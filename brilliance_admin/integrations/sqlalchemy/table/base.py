from typing import Any

from brilliance_admin.integrations.sqlalchemy.fields_schema import SQLAlchemyFieldsSchema
from brilliance_admin.integrations.sqlalchemy.table.count_providers import SQLAlchemyCountProvider
from brilliance_admin.schema.table.category_table import CategoryTable
from brilliance_admin.schema.table.count_providers import CountProvider
from brilliance_admin.schema.table.schema_type import SchemaType
from brilliance_admin.schema.table.table_models import AutocompleteData
from brilliance_admin.translations import TranslateText as _

EXCEPTION_REL_NAME = '''
Model "{model_name}" doesn\'t contain rel_name:"{rel_name}" for field "{slug}"
Model fields = {model_attrs}
'''


class SQLAlchemyAdminBase(CategoryTable):
    model: Any
    slug = None
    raise_async_unsafe = False
    ordering_fields = []

    search_fields = []

    table_schema: SQLAlchemyFieldsSchema

    db_async_session: Any = None
    count_provider: CountProvider | None = None

    def __init__(
            self,
            *args,
            model=None,
            table_schema=None,
            db_async_session=None,
            ordering_fields=None,
            default_ordering=None,
            search_fields=None,
            raise_async_unsafe=None,
            count_provider=None,
            **kwargs,
    ):
        if model:
            self.model = model

        if raise_async_unsafe is not None:
            self.raise_async_unsafe = raise_async_unsafe

        if count_provider is not None:
            self.count_provider = count_provider

        if search_fields:
            self.search_fields = search_fields

        if self.search_fields:
            self.search_enabled = True
            self.search_help = _('sqlalchemy_search_help') % {'fields': ', '.join(self.search_fields)}

        if default_ordering:
            self.default_ordering = default_ordering

        if ordering_fields:
            self.ordering_fields = ordering_fields

        self.validate_fields()

        if table_schema:
            self.table_schema = table_schema

        if not self.table_schema:
            self.table_schema = SQLAlchemyFieldsSchema(model=self.model)

        if not issubclass(type(self.table_schema), SQLAlchemyFieldsSchema):
            msg = f'{type(self).__name__}.table_schema {self.table_schema} must be subclass of SQLAlchemyFieldsSchema'
            raise AttributeError(msg)

        if not self.model:
            msg = f'{type(self).__name__}.model is required for SQLAlchemy'
            raise AttributeError(msg)

        if not self.slug:
            self.slug = self.model.__name__.lower()

        if db_async_session:
            self.db_async_session = db_async_session

        if not self.db_async_session:
            msg = f'{type(self).__name__}.db_async_session is required for SQLAlchemy'
            raise AttributeError(msg)

        if self.count_provider is None:
            self.count_provider = SQLAlchemyCountProvider(self.db_async_session)

        # pylint: disable=import-outside-toplevel
        from sqlalchemy import inspect
        from sqlalchemy.sql.schema import Column

        for attr in inspect(self.model).mapper.column_attrs:
            col: Column = attr.columns[0]
            if col.primary_key and not self.pk_name:
                self.pk_name = attr.key
                break

        if not self.default_ordering and self.pk_name:
            self.default_ordering = f'-{self.pk_name}'

        super().__init__(*args, **kwargs)

    def get_extra_autocomplete(self, data: AutocompleteData) -> dict:
        extra = super().get_extra_autocomplete(data)
        extra['db_async_session'] = self.db_async_session
        extra['model'] = self.model
        extra['raise_async_unsafe'] = self.raise_async_unsafe

        # Inline model
        if data.inline_field_slug:
            inline_field = self.table_schema.get_field(data.inline_field_slug)
            form_schema = inline_field.table_schema
            extra['model'] = form_schema.model

        return extra

    def _get_form_schema(self, user, language_context, parent_category=None, admin_schema=None):
        exclude_fields = []

        if isinstance(parent_category, SQLAlchemyAdminBase):
            assert parent_category.model is not None
            fk_field_name = self.get_parent_fk_field_name(parent_category)
            assert fk_field_name in self.table_schema.get_fields(), (
                'Subcategory schema must contain parent FK before exclusion'
            )
            exclude_fields.append(fk_field_name)

        return self.table_schema.generate_form_schema(
            user,
            language_context,
            schema_type=SchemaType.TABLE,
            exclude_fields=exclude_fields,
            admin_schema=admin_schema,
        )

    def validate_fields(self):
        # pylint: disable=import-outside-toplevel
        from sqlalchemy.orm import InstrumentedAttribute

        if self.search_fields:
            for field in self.search_fields:
                column = getattr(self.model, field, None)
                if not isinstance(column, InstrumentedAttribute):
                    raise AttributeError(
                        f'{type(self).__name__}: search field "{field}" not found in model {self.model.__name__}'
                    )

        if self.ordering_fields:
            for field in self.ordering_fields:
                column = getattr(self.model, field, None)
                if not isinstance(column, InstrumentedAttribute):
                    raise AttributeError(
                        f'{type(self).__name__}: ordering field "{field}" not found in model {self.model.__name__}'
                    )

    def get_queryset(self):
        # pylint: disable=import-outside-toplevel
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        stmt = select(self.model).options(selectinload('*'))

        # Eager-load related fields
        for slug, field in self.table_schema.get_fields().items():

            # pylint: disable=protected-access
            if field._type == "related":

                if not hasattr(self.model, field.rel_name):
                    # pylint: disable=import-outside-toplevel
                    from sqlalchemy import inspect
                    model_attrs = [attr.key for attr in inspect(self.model).mapper.attrs]

                    msg = EXCEPTION_REL_NAME.format(
                        slug=slug,
                        model_name=self.model.__name__,
                        rel_name=field.rel_name,
                        model_attrs=model_attrs,
                    )
                    raise AttributeError(msg)

                stmt = stmt.options(selectinload(getattr(self.model, field.rel_name)))

        return stmt

    def get_parent_fk_field_name(self, parent_category):
        if parent_category is None:
            return None

        parent_model = getattr(parent_category, 'model', None)
        if parent_model is None:
            return None

        # pylint: disable=import-outside-toplevel
        from sqlalchemy import inspect

        mapper = inspect(self.model).mapper
        parent_table = parent_model.__table__
        matched_fields = []

        for attr in mapper.column_attrs:
            col = attr.columns[0]
            for fk in col.foreign_keys:
                if fk.column.table is parent_table:
                    matched_fields.append(attr.key)

        if not matched_fields:
            raise RuntimeError(
                f'{type(self).__name__}: no FK from {self.model.__name__} '
                f'to parent model {parent_model.__name__}'
            )

        if len(matched_fields) > 1:
            raise RuntimeError(
                f'{type(self).__name__}: multiple FKs from {self.model.__name__} '
                f'to parent model {parent_model.__name__}: {matched_fields}'
            )

        return matched_fields[0]

    def apply_parent_filter(self, stmt, parent_category=None, parent_pk=None):
        if parent_category is None or parent_pk is None:
            return stmt

        fk_field_name = self.get_parent_fk_field_name(parent_category)
        # pylint: disable=import-outside-toplevel
        from sqlalchemy import inspect

        fk_column = inspect(self.model).mapper.columns[fk_field_name]
        python_type = fk_column.type.python_type

        return stmt.where(getattr(self.model, fk_field_name) == python_type(parent_pk))
