import datetime
from typing import Any

from brilliance_admin import schema
from brilliance_admin.exceptions import AdminAPIException, APIError
from brilliance_admin.integrations.sqlalchemy.fields import SQLAlchemyRelatedField
from brilliance_admin.schema.table.fields.base import DateTimeField
from brilliance_admin.translations import TranslateText as _
from brilliance_admin.utils import DeserializeAction, humanize_field_name

FIELD_FILTERS_NOT_FOUND = '{class_name} filter "{field_slug}" not found inside table_filters fields: {available_filters}'


class SQLAlchemyFieldsSchema(schema.FieldsSchema):
    model: Any

    def __init__(self, *args, model=None, **kwargs):
        if model:
            self.model = model

        super().__init__(*args, **kwargs)

    def generate_fields(self, kwargs) -> dict:
        generated_fields = super().generate_fields(kwargs)

        # pylint: disable=import-outside-toplevel
        from sqlalchemy import inspect
        from sqlalchemy.dialects.postgresql import ARRAY
        from sqlalchemy.ext.mutable import Mutable
        from sqlalchemy.sql import sqltypes
        from sqlalchemy.sql.schema import Column

        mapper = inspect(self.model).mapper

        for attr in mapper.column_attrs:
            col: Column = attr.columns[0]
            field_slug = attr.key

            if field_slug in generated_fields:
                continue

            field_data = {}
            info = col.info or {}
            field_data["label"] = info.get('label', humanize_field_name(field_slug))
            field_data["help_text"] = info.get('help_text')

            field_data["read_only"] = col.primary_key

            # Whether the field is required on input (best-effort heuristic)
            field_data["required"] = (
                not col.nullable
                and col.default is None
                and col.server_default is None
                and not col.primary_key
            )

            col_type = col.type
            try:
                py_t = col_type.python_type
            except Exception:
                py_t = None

            impl = getattr(attr, 'impl', None)
            is_impl_mutable = isinstance(impl, Mutable)

            # Foreign key column
            if col.foreign_keys:
                continue

            elif "choices" in info:
                field_data["choices"] = info['choices']
                field_class = schema.ChoiceField

            elif isinstance(col_type, (sqltypes.BigInteger, sqltypes.Integer)) or py_t is int:
                field_class = schema.IntegerField

            elif isinstance(col_type, sqltypes.Numeric):
                field_class = schema.IntegerField
                field_data["inputmode"] = "decimal"
                field_data["precision"] = col_type.precision
                field_data["scale"] = col_type.scale

            elif isinstance(col_type, sqltypes.String) or py_t is str:
                field_class = schema.StringField
                # Max length is usually stored as String(length=...)
                if getattr(col_type, "length", None):
                    field_data["max_length"] = col_type.length

            elif isinstance(col_type, sqltypes.DateTime) or py_t is datetime:
                field_class = schema.DateTimeField

            elif isinstance(col_type, sqltypes.Boolean) or py_t is bool:
                field_class = schema.BooleanField

            elif isinstance(col_type, sqltypes.JSON):
                field_class = schema.JSONField

            elif isinstance(col_type, ARRAY):
                field_class = schema.ArrayField
                field_data["array_type"] = type(col_type.item_type).__name__.lower()
                field_data["read_only"] = is_impl_mutable or isinstance(col_type, Mutable)

            elif isinstance(col_type, sqltypes.NullType):
                continue

            elif not self.fields:
                msg = f'SQLAlchemy autogenerate ORM field {self.model.__name__}.{field_slug} is not supported for type: {col_type}'
                raise AttributeError(msg)

            schema_field = field_class(**field_data)

            if col.primary_key:
                generated_fields = {field_slug: schema_field, **generated_fields}
            else:
                generated_fields[field_slug] = schema_field

        for field_slug, field in self.generate_related_fields():
            generated_fields[field_slug] = field

        return generated_fields

    def generate_related_fields(self):
        # pylint: disable=import-outside-toplevel
        from sqlalchemy import inspect

        mapper = inspect(self.model).mapper

        # relationship-поля
        for rel in mapper.relationships:
            # relationship, у которых есть локальные FK-колонки, не добавляем в схему,
            # так как связь редактируется через scalar-поле (FK),
            # а relationship используется только для ORM-навигации
            if any(col.foreign_keys for col in rel.local_columns):
                continue

            field_slug = rel.key

            field_data = {}

            info = rel.info or {}
            field_data["label"] = info.get('label', humanize_field_name(field_slug))
            field_data["help_text"] = info.get('help_text')

            field_data["read_only"] = rel.viewonly
            field_data["required"] = (
                not rel.uselist
                and all(not col.nullable for col in rel.local_columns)
            )

            field_data["rel_name"] = rel.key
            field_data["many"] = rel.uselist
            field_data["dual_list"] = rel.uselist
            field_data["target_model"] = rel.mapper.class_

            yield field_slug, SQLAlchemyRelatedField(**field_data)

        # FK-поля
        for attr in mapper.column_attrs:
            col = attr.columns[0]

            if not col.foreign_keys:
                continue

            rel_obj = None
            for rel in mapper.relationships:
                if col in rel.local_columns:
                    rel_obj = rel
                    break

            if not rel_obj:
                continue

            field_slug = attr.key

            field_data = {}

            info = col.info or {}
            field_data["label"] = info.get('label', humanize_field_name(rel_obj.key))
            field_data["help_text"] = info.get('help_text')

            field_data["read_only"] = False
            field_data["required"] = (
                not col.nullable
                and col.default is None
                and col.server_default is None
                and not col.primary_key
            )

            field_data["rel_name"] = rel_obj.key
            field_data["many"] = rel_obj.uselist
            field_data["target_model"] = rel_obj.mapper.class_

            yield field_slug, SQLAlchemyRelatedField(**field_data)

    async def apply_filters(self, stmt, filters: dict):
        # pylint: disable=import-outside-toplevel
        from sqlalchemy import String, cast

        for field_slug in filters.keys():
            field = self.get_field(field_slug)

            if not field:
                available_filters = list(self.get_fields().keys())
                msg = FIELD_FILTERS_NOT_FOUND.format(
                    class_name=type(self).__name__,
                    field_slug=field_slug,
                    available_filters=available_filters,
                )
                raise AttributeError(msg)

        deserialized_filters = await self.deserialize(
            filters,
            DeserializeAction.FILTERS,
            extra={'model': self.model},
        )

        for field_slug, value in deserialized_filters.items():
            field = self.get_field(field_slug)
            column = getattr(self.model, field_slug, None)

            apply_filter = getattr(field, 'apply_filter', None)
            if apply_filter and callable(apply_filter):
                stmt = await apply_filter(stmt, value, self.model, column)

            elif issubclass(type(field), DateTimeField) and field.range:
                stmt = stmt.where(column >= value['from'])
                stmt = stmt.where(column <= value['to'])

            elif isinstance(value, list):
                stmt = stmt.where(column.in_(value))

            elif isinstance(value, str):
                stmt = stmt.where(
                    cast(column, String).like(value)
                )

            else:
                stmt = stmt.where(column == value)

        return stmt

    async def serialize(self, record, extra: dict, *args, **kwargs) -> dict:

        # Convert model values to dict
        record_data = {}

        for slug, field in self.get_fields().items():
            # pylint: disable=protected-access
            if field._type == 'related':
                record_data[slug] = record
            else:
                record_data[slug] = getattr(record, slug, None)

        return await super().serialize(record_data, extra, *args, **kwargs)

    def validate_incoming_data(self, data):
        '''
        Validate that all fields keys has their schema

        for create, update
        '''
        for field_slug in data.keys():
            field = self.get_field(field_slug)
            if not field:
                available = list(self.get_fields().keys())
                msg = _('field_not_found_in_schema') % {'field_slug': field_slug, 'available': available}
                raise AdminAPIException(
                    APIError(message=msg, code='field_not_found_in_schema '),
                    status_code=400,
                )

    async def create(self, user, data, session):
        self.validate_incoming_data(data)

        record = self.model()

        deserialized_data = await self.deserialize(
            data,
            DeserializeAction.CREATE,
            extra={'model': self.model},
        )

        # сначала простые поля
        for field_slug, value in deserialized_data.items():
            field = self.get_field(field_slug)

            if isinstance(field, SQLAlchemyRelatedField):
                continue

            setattr(record, field_slug, value)

        session.add(record)

        # затем related под no_autoflush
        for field_slug, value in deserialized_data.items():
            field = self.get_field(field_slug)

            if isinstance(field, SQLAlchemyRelatedField):
                with session.no_autoflush:
                    await field.update_related(record, field_slug, value, session)

        await session.commit()
        await session.refresh(record)
        return record

    async def update(self, record, user, data, session):
        self.validate_incoming_data(data)

        deserialized_data = await self.deserialize(
            data,
            DeserializeAction.UPDATE,
            extra={'model': self.model},
        )

        for field_slug, value in deserialized_data.items():
            field = self.get_field(field_slug)

            if isinstance(field, SQLAlchemyRelatedField):
                await field.update_related(record, field_slug, value, session)
                continue

            setattr(record, field_slug, value)

        await session.commit()
        return record
