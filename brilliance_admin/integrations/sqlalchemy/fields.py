from typing import Any, List

from pydantic.dataclasses import dataclass

from brilliance_admin.auth import UserABC
from brilliance_admin.exceptions import AdminAPIException, APIError, FieldError
from brilliance_admin.schema.category import FieldSchemaData
from brilliance_admin.schema.table.fields.base import TableField
from brilliance_admin.schema.table.table_models import AutocompleteData, Record
from brilliance_admin.translations import LanguageContext
from brilliance_admin.translations import TranslateText as _
from brilliance_admin.utils import DeserializeAction


def get_pk(obj):
    pk_cols = obj.__mapper__.primary_key
    if len(pk_cols) != 1:
        raise NotImplementedError('Composite primary key is not supported')
    return getattr(obj, pk_cols[0].key)


@dataclass
class SQLAlchemyRelatedField(TableField):
    _type: str = 'related'

    # Тип связи.
    # Откуда берётся:
    # - из SQLAlchemy relationship.uselist
    #   rel.uselist == True  -> список связанных объектов
    #   rel.uselist == False -> одиночная связь
    #
    # Зачем нужен:
    # - чтобы понимать, ожидать list или один объект
    # - влияет на логику update_related и serialize
    many: bool = False

    # Имя relationship-атрибута на модели.
    # Откуда берётся:
    # - из mapper.relationships: rel.key
    # - либо через поиск relationship по FK колонке (col.local_columns)
    #
    # Зачем нужен:
    # - для доступа к связи через ORM
    #   getattr(record, rel_name)
    # - для записи и чтения связанных объектов
    rel_name: str | None

    # Класс связанной SQLAlchemy-модели.
    # Откуда берётся:
    # - из relationship: rel.mapper.class_
    #
    # Зачем нужен:
    # - для загрузки связанных записей из БД
    #   session.get(target_model, pk)
    #   select(target_model).where(target_model.id.in_(...))
    target_model: Any | None = None

    # Работает только если many=True
    dual_list: bool = False

    def generate_schema(self, user: UserABC, field_slug, language_context: LanguageContext) -> FieldSchemaData:
        schema = super().generate_schema(user, field_slug, language_context)
        schema.many = self.many
        schema.rel_name = self.rel_name
        schema.dual_list = self.dual_list
        return schema

    def _get_target_model(self, model, field_slug):
        # pylint: disable=import-outside-toplevel
        from sqlalchemy import inspect

        mapper = inspect(model).mapper
        attr = mapper.attrs.get(field_slug)
        if attr is None:
            msg = f'Field "{field_slug}" is not found on model "{model}"'
            raise AttributeError(msg)

        # RelationshipProperty
        if hasattr(attr, 'mapper'):
            return attr.mapper.class_

        # ColumnProperty (FK column). Try to resolve from foreign key target table.
        col = getattr(model, field_slug).property.columns[0]
        if not col.foreign_keys:
            msg = f'Field "{field_slug}" is not a relationship and not a FK column'
            raise AttributeError(msg)

        fk = next(iter(col.foreign_keys))
        target_table = fk.column.table

        # Find a mapped class that uses this table in the same registry
        for m in mapper.registry.mappers:
            if getattr(m, 'local_table', None) is target_table:
                return m.class_

        msg = f'Cannot resolve target model for FK "{field_slug}"'
        raise AttributeError(msg)

    async def autocomplete(self, model, data: AutocompleteData, user, *, extra: dict | None = None) -> List[Record]:
        # pylint: disable=import-outside-toplevel
        from sqlalchemy import select

        if extra is None or extra.get('db_async_session') is None:
            msg = f'SQLAlchemyRelatedField.autocomplete {type(self).__name__} requires extra["db_async_session"] (AsyncSession)'
            raise AttributeError(msg)

        db_async_session = extra['db_async_session']

        results = []

        target_model = self._get_target_model(model, data.field_slug)
        limit = min(150, data.limit)
        stmt = select(target_model).limit(limit)

        pk = get_pk(target_model)
        python_pk_type = pk.property.columns[0].type.python_type

        if data.search_string:
            try:
                value = python_pk_type(data.search_string)
            except (ValueError, TypeError):
                # Search string cannot be cast to primary key type, skip id filter
                value = None

            stmt = stmt.where(pk == value)

        # Add already selected choices
        if data.existed_choices:
            existed_choices = [i['key'] for i in data.existed_choices if 'key' in i]

            values = []
            for value in existed_choices:
                try:
                    values.append(python_pk_type(value))
                except (ValueError, TypeError) as e:
                    msg = f'Invalid existed_choices value "{value}" for pk {pk} python_pk_type:{python_pk_type.__name__}'
                    raise AdminAPIException(APIError(message=msg), status_code=500) from e

            stmt = stmt.where(pk.in_(values))

        async with db_async_session() as session:
            records = (await session.execute(stmt)).scalars().all()

        for record in records:
            results.append(Record(key=getattr(record, pk.key), title=str(record)))

        return results

    async def serialize(self, value, extra: dict, *args, **kwargs) -> Any:
        """
        Сериализация related-поля.

        Входные данные:
        - value всегда scalar (None или int)
        - ORM-объект доступен через extra["record"]
        """
        if not value:
            return

        record = extra.get('record')
        if record is None:
            raise FieldError(f'Missing record in serialize context in value: {value}')

        related = getattr(record, self.rel_name, None)

        if self.many:
            if related is None:
                raise FieldError(f'Many Related field "{self.rel_name}" is missing on record "{record}"')
            return [{'key': get_pk(obj), 'title': str(obj)} for obj in related]

        if related is None:
            return None

        return {'key': get_pk(related), 'title': str(related)}

    async def deserialize(self, value, action: DeserializeAction, extra: dict, *args, **kwargs) -> Any:
        value = await super().deserialize(value, action, extra, *args, **kwargs)
        if not value:
            return None

        if isinstance(value, list):
            result = []
            for i in value:
                i = i.get('key')
                if not isinstance(i, (int, str)):
                    raise FieldError(f'Value "{i}" is not supported for related field')
                result.append(i)
            return result

        result = None
        if isinstance(value, dict) and 'key' in value:
            result = value['key']

        if isinstance(value, (int, str)):
            result = value

        if not isinstance(result, (int, str)):
            raise FieldError(f'Value "{result}" is not supported for related field')

        return result

    async def update_related(self, record, field_slug, value, session):
        """
        Обновление SQLAlchemy relationship.

        Предположения:
        - self.rel_name всегда имя relationship
        - self.target_model задан
        - self.many отражает тип связи
        """

        # pylint: disable=import-outside-toplevel

        if value is None:
            return

        # При CREATE объект должен быть в session до работы с relationship
        if record not in session:
            session.add(record)

        rel_attr = self.rel_name

        if self.many:
            assert isinstance(value, list)

            if not value:
                setattr(record, rel_attr, [])
                return

            result = []
            for i in value:
                obj = await session.get(self.target_model, i)
                if obj is None:
                    msg = _('related_not_found') % {
                        'model': self.target_model.__name__,
                        'pk': i,
                        'field_slug': field_slug,
                    }
                    raise AdminAPIException(
                        APIError(message=msg, code='related_not_found'),
                        status_code=400,
                    )
                result.append(obj)

            # getattr(record, rel_attr).clear()
            getattr(record, rel_attr).extend(list(result))
            return

        obj = await session.get(self.target_model, value)
        setattr(record, rel_attr, obj)

    async def apply_filter(self, stmt, value, model, column):
        # pylint: disable=import-outside-toplevel
        from sqlalchemy import inspect

        if value is None:
            return stmt

        rel = getattr(model, self.rel_name)
        pk_col = inspect(self.target_model).primary_key[0]

        # many=False: FK (many-to-one)
        if not self.many:
            if not isinstance(value, int):
                raise FieldError(f'Expected int for filter {self.rel_name}')
            return stmt.where(rel.has(pk_col == value))

        # many=True: one-to-many / many-to-many
        if not isinstance(value, list):
            raise FieldError(f'Expected list[int] for filter {self.rel_name}')
        return stmt.where(rel.any(pk_col.in_(value)))
