import inspect
from typing import Any, List

from pydantic.dataclasses import dataclass

from brilliance_admin.auth import UserABC
from brilliance_admin.exceptions import AdminAPIException, APIError, AsyncUnsafeTitleLoad, FieldError
from brilliance_admin.integrations.sqlalchemy.utils import get_pk
from brilliance_admin.schema.admin_schema import AdminSchema
from brilliance_admin.schema.category import FieldSchemaData
from brilliance_admin.schema.table.fields.base import RelatedField
from brilliance_admin.schema.table.schema_type import SchemaType
from brilliance_admin.schema.table.table_models import AutocompleteData, Record
from brilliance_admin.translations import LanguageContext
from brilliance_admin.translations import TranslateText as _
from brilliance_admin.utils import get_logger

logger = get_logger()

FIELD_NOT_FOUND_ON_MODEL = 'Field "{field_slug}" is not found on model "{model}"'
FIELD_NOT_RELATIONSHIP_OR_FK = 'Field "{field_slug}" is not a relationship and not a FK column'
CANNOT_RESOLVE_TARGET_MODEL = 'Cannot resolve target model for FK "{field_slug}"'
AUTOCOMPLETE_REQUIRES_MODEL = (
    'SQLAlchemyRelatedField.autocomplete {class_name} requires extra["model"]'
)
AUTOCOMPLETE_REQUIRES_SESSION = (
    'SQLAlchemyRelatedField.autocomplete {class_name}'
    ' requires extra["db_async_session"] (AsyncSession)'
)
INVALID_EXISTED_CHOICES = (
    'Invalid existed_choices value "{value}"'
    ' for pk {pk} python_pk_type:{python_pk_type}'
)
MISSING_RECORD_IN_CONTEXT = 'Missing record in serialize context in value: {value}'
MANY_RELATED_MISSING = 'Many Related field "{rel_name}" is missing on record "{record}"'
RELATED_MISSING_ON_RECORD = (
    'Inline related field "{rel_name}" cannot be serialized from record "{record_type}". '
    'Expected inline row model to contain this relation.'
)
EXPECTED_LIST_FOR_FILTER = 'Expected list[int] for filter {rel_name}'
ASYNC_LAZY_RELATED_LOAD_ERROR = (
    'Async unsafe lazy related load: field="{field}" model="{model}". '
    'Add selectinload({model}.{field}) or joinedload({model}.{field}) to get_queryset().'
)
TITLE_ASYNC_UNSAFE_HINT = (
    'Add required selectinload()/joinedload() to get_queryset(), '
    'or avoid lazy relation access in __str__().'
)


def get_str_source(record) -> str:
    try:
        source = inspect.getsource(type(record).__str__)
    except (OSError, TypeError):
        return ''

    return f'\n__str__ source:\n{source}'


def get_record_title(
    record,
    raise_async_unsafe=True,
    *,
    parent_record=None,
    field_slug: str | None = None,
    rel_name: str | None = None,
    debug: bool = False,
) -> str:
    try:
        return str(record)
    except Exception as e:
        # pylint: disable=import-outside-toplevel
        from sqlalchemy.exc import MissingGreenlet

        if not isinstance(e, MissingGreenlet):
            raise

        error = AsyncUnsafeTitleLoad(
            record,
            get_str_source(record),
            backend='sqlalchemy',
            hint=TITLE_ASYNC_UNSAFE_HINT,
        )
        if raise_async_unsafe:
            raise error from e
        if debug:
            logger.warning(
                'Async unsafe title load: field="%s" rel_name="%s" '
                'parent_model="%s" parent_pk=%s '
                'model="%s" pk=%s. %s%s',
                field_slug,
                rel_name,
                type(parent_record).__name__ if parent_record is not None else None,
                get_pk(parent_record) if parent_record is not None else None,
                type(error.record).__name__,
                get_pk(error.record),
                error.hint,
                error.source,
            )
        return f'{type(record).__name__}#{get_pk(record)}'


@dataclass
class SQLAlchemyRelatedField(RelatedField):

    # Имя relationship-атрибута на модели.
    # Откуда берётся:
    # - из mapper.relationships: rel.key
    # - либо через поиск relationship по FK колонке (col.local_columns)
    #
    # Зачем нужен:
    # - для доступа к связи через ORM
    #   getattr(record, rel_name)
    # - для записи и чтения связанных объектов
    rel_name: str | None = None

    # Класс связанной SQLAlchemy-модели.
    # Откуда берётся:
    # - из relationship: rel.mapper.class_
    #
    # Зачем нужен:
    # - для загрузки связанных записей из БД
    #   session.get(target_model, pk)
    #   select(target_model).where(target_model.id.in_(...))
    target_model: Any | None = None

    def get_related_category(self, admin_schema: AdminSchema) -> tuple[str, str] | None:
        from brilliance_admin.integrations.sqlalchemy.table.base import SQLAlchemyAdminBase

        if self.target_model is None:
            raise AttributeError(f'{type(self).__name__}.target_model is required')

        for group in admin_schema.categories:
            for category in getattr(group, 'subcategories', []):
                if isinstance(category, SQLAlchemyAdminBase) and category.model is self.target_model:
                    return group.slug, category.slug

        return None

    def _cast_pk(self, value, pk_type):
        if isinstance(value, pk_type):
            return value

        try:
            return pk_type(value)
        except (TypeError, ValueError) as e:
            raise FieldError(f'Invalid key for filter {self.rel_name}: {value}') from e

    def generate_field_schema(
            self,
            user: UserABC,
            field_slug,
            fields_schema,
            admin_schema,
            language_context: LanguageContext,
            schema_type: SchemaType = SchemaType.TABLE,
            **kwargs,
    ) -> FieldSchemaData:
        schema = super().generate_field_schema(
            user,
            field_slug,
            fields_schema,
            admin_schema,
            language_context,
            schema_type,
            **kwargs,
        )
        schema.rel_name = self.rel_name

        if schema.related_group is None and schema.related_category is None:
            related_category = self.get_related_category(admin_schema)
            if related_category is not None:
                schema.related_group, schema.related_category = related_category

        return schema

    def _get_target_model(self, model, field_slug):
        # pylint: disable=import-outside-toplevel
        from sqlalchemy import inspect

        mapper = inspect(model).mapper
        attr = mapper.attrs.get(field_slug)
        if attr is None:
            msg = FIELD_NOT_FOUND_ON_MODEL.format(field_slug=field_slug, model=model)
            raise AttributeError(msg)

        # RelationshipProperty
        if hasattr(attr, 'mapper'):
            return attr.mapper.class_

        # ColumnProperty (FK column). Try to resolve from foreign key target table.
        col = getattr(model, field_slug).property.columns[0]
        if not col.foreign_keys:
            msg = FIELD_NOT_RELATIONSHIP_OR_FK.format(field_slug=field_slug)
            raise AttributeError(msg)

        fk = next(iter(col.foreign_keys))
        target_table = fk.column.table

        # Find a mapped class that uses this table in the same registry
        for m in mapper.registry.mappers:
            if getattr(m, 'local_table', None) is target_table:
                return m.class_

        msg = CANNOT_RESOLVE_TARGET_MODEL.format(field_slug=field_slug)
        raise AttributeError(msg)

    async def _get_autocomplete_statement(
        self,
        data: AutocompleteData,
        user,
        *,
        extra: dict | None = None,
    ):
        if extra is None or extra.get('model') is None:
            msg = AUTOCOMPLETE_REQUIRES_MODEL.format(class_name=type(self).__name__)
            raise AttributeError(msg)

        model = extra['model']

        # pylint: disable=import-outside-toplevel
        from sqlalchemy import select

        target_model = self._get_target_model(model, data.field_slug)
        stmt = select(target_model)

        pk = get_pk(target_model)
        python_pk_type = pk.property.columns[0].type.python_type

        if self.filter_fn:
            import inspect as ins
            if ins.iscoroutinefunction(self.filter_fn):
                stmt = await self.filter_fn(stmt, data, user)
            else:
                stmt = self.filter_fn(stmt, data, user)

        return stmt, pk

    def _get_existing_choices_statement(self, stmt, data: AutocompleteData, pk, python_pk_type):
        if not data.existed_choices:
            return None

        existed_choices = [item['key'] for item in data.existed_choices if 'key' in item]
        values = []
        for value in existed_choices:
            try:
                values.append(python_pk_type(value))
            except (ValueError, TypeError) as e:
                msg = INVALID_EXISTED_CHOICES.format(
                    value=value, pk=pk, python_pk_type=python_pk_type.__name__,
                )
                raise AdminAPIException(APIError(message=msg), status_code=500) from e

        return stmt.where(pk.in_(values))

    def _get_autocomplete_result_statement(self, stmt, data: AutocompleteData, pk):
        python_pk_type = pk.property.columns[0].type.python_type
        existing_stmt = self._get_existing_choices_statement(stmt, data, pk, python_pk_type)
        search_stmt = self._apply_autocomplete_search(stmt, data, pk)

        if existing_stmt is None or not data.search_string:
            return search_stmt

        # UNION must contain only PKs: selecting models from a compound query
        # makes SQLAlchemy return row values instead of ORM instances.
        from sqlalchemy import select

        matching_pks = existing_stmt.with_only_columns(pk).union(
            search_stmt.with_only_columns(pk),
        ).subquery()
        return stmt.where(pk.in_(select(matching_pks.c[pk.key])))

    def _apply_autocomplete_search(self, stmt, data: AutocompleteData, pk):
        if not data.search_string:
            return stmt

        # pylint: disable=import-outside-toplevel
        from sqlalchemy import String, cast, or_

        target_model = pk.class_
        search_fields = getattr(target_model, '__search_fields__', None)
        if search_fields:
            conditions = []
            for field_name in search_fields:
                col = getattr(target_model, field_name, None)
                if col is not None:
                    conditions.append(
                        cast(col, String).ilike(f'%{data.search_string}%')
                    )
            if conditions:
                return stmt.where(or_(*conditions))
            return stmt

        python_pk_type = pk.property.columns[0].type.python_type
        try:
            value = python_pk_type(data.search_string)
        except (ValueError, TypeError):
            value = None
        return stmt.where(pk == value)

    async def autocomplete(
        self,
        data: AutocompleteData,
        user,
        extra: dict | None = None,
        parent_category=None,
        parent_pk=None,
        debug: bool = False,
    ) -> List[Record]:
        if extra is None or extra.get('db_async_session') is None:
            msg = AUTOCOMPLETE_REQUIRES_SESSION.format(class_name=type(self).__name__)
            raise AttributeError(msg)

        db_async_session = extra['db_async_session']
        stmt, pk = await self._get_autocomplete_statement(data, user, extra=extra)
        stmt = self._get_autocomplete_result_statement(stmt, data, pk)
        stmt = stmt.limit(min(150, data.limit))
        results = []

        async with db_async_session() as session:
            records = (await session.execute(stmt)).scalars().all()
            for record in records:
                try:
                    title = get_record_title(
                        record,
                        extra.get('raise_async_unsafe'),
                        field_slug=data.field_slug,
                        rel_name=self.rel_name,
                        debug=debug,
                    )
                except AsyncUnsafeTitleLoad as e:
                    message = (
                        f'Async unsafe title load: field="{data.field_slug}" rel_name="{self.rel_name}" '
                        f'parent_model="{None}" parent_pk=None '
                        f'model="{type(e.record).__name__}" pk={get_pk(e.record)}. '
                        f'{e.hint}'
                        f'{e.source}'
                    )
                    logger.exception(
                        'SQLAlchemy async unsafe autocomplete title load: field=%s rel_name=%s model=%s pk=%s',
                        data.field_slug,
                        self.rel_name,
                        type(e.record).__name__,
                        get_pk(e.record),
                    )
                    raise AdminAPIException(
                        APIError(message=message, code='async_unsafe_title_load'),
                        status_code=500,
                    ) from e
                _record = Record(
                    key=getattr(record, pk.key),
                    title=title,
                )
                results.append(_record)

        return results

    async def autocomplete_total_count(
        self,
        data: AutocompleteData,
        user,
        extra: dict | None = None,
        parent_category=None,
        parent_pk=None,
    ) -> int:
        if extra is None or extra.get('db_async_session') is None:
            msg = AUTOCOMPLETE_REQUIRES_SESSION.format(class_name=type(self).__name__)
            raise AttributeError(msg)

        # pylint: disable=import-outside-toplevel
        from sqlalchemy import func, select

        db_async_session = extra['db_async_session']
        stmt, pk = await self._get_autocomplete_statement(data, user, extra=extra)
        stmt = self._get_autocomplete_result_statement(stmt, data, pk)
        count_stmt = select(func.count()).select_from(stmt.subquery())
        async with db_async_session() as session:
            return await session.scalar(count_stmt)

    async def _load_related_fallback(self, value, extra: dict):
        db_async_session = extra.get('db_async_session')
        if db_async_session is None or self.target_model is None:
            return None

        async with db_async_session() as session:
            return await session.get(self.target_model, value)

    async def serialize(self, value, extra: dict, field_slug: str | None = None, *args, **kwargs) -> Any:
        """
        Сериализация related-поля.

        Входные данные:
        - value всегда scalar (None или int)
        - ORM-объект доступен через extra["record"]
        """
        if not value:
            return None

        record = extra.get('record')
        if record is None:
            raise FieldError(MISSING_RECORD_IN_CONTEXT.format(value=value))

        if not hasattr(record, self.rel_name):
            raise FieldError(RELATED_MISSING_ON_RECORD.format(
                rel_name=self.rel_name,
                record_type=type(record).__name__,
            ))

        try:
            related = getattr(record, self.rel_name, None)
        except Exception as e:
            # pylint: disable=import-outside-toplevel
            from sqlalchemy.exc import MissingGreenlet

            if not isinstance(e, MissingGreenlet):
                raise

            msg = ASYNC_LAZY_RELATED_LOAD_ERROR.format(
                field=self.rel_name,
                model=type(record).__name__,
            )
            if extra.get('raise_async_unsafe'):
                logger.exception(
                    'SQLAlchemy async unsafe lazy related load: field=%s model=%s',
                    self.rel_name,
                    type(record).__name__,
                )
                raise AdminAPIException(
                    APIError(message=msg, code='async_lazy_related_load'),
                    status_code=500,
                ) from e
            if extra.get('debug'):
                logger.warning(msg)
            if self.many:
                return []
            related = await self._load_related_fallback(value, extra)

        if self.many:
            if related is None:
                raise FieldError(MANY_RELATED_MISSING.format(rel_name=self.rel_name, record=record))
            result = []
            for obj in related:
                try:
                    title = get_record_title(
                        obj,
                        extra.get('raise_async_unsafe'),
                        parent_record=record,
                        field_slug=field_slug,
                        rel_name=self.rel_name,
                        debug=extra.get('debug', False),
                    )
                except AsyncUnsafeTitleLoad as e:
                    self._raise_title_load_error(e, record, field_slug)
                result.append({'key': get_pk(obj), 'title': title})
            return result

        if related is None:
            return None

        try:
            title = get_record_title(
                related,
                extra.get('raise_async_unsafe'),
                parent_record=record,
                field_slug=field_slug,
                rel_name=self.rel_name,
                debug=extra.get('debug', False),
            )
        except AsyncUnsafeTitleLoad as e:
            self._raise_title_load_error(e, record, field_slug)

        return {'key': get_pk(related), 'title': title}

    def _raise_title_load_error(
        self,
        error: AsyncUnsafeTitleLoad,
        parent_record,
        field_slug: str | None = None,
    ):
        message = (
            f'Async unsafe title load: field="{field_slug}" rel_name="{self.rel_name}" '
            f'parent_model="{type(parent_record).__name__ if parent_record is not None else None}" '
            f'parent_pk={get_pk(parent_record)} '
            f'model="{type(error.record).__name__}" pk={get_pk(error.record)}. '
            f'{error.hint}'
            f'{error.source}'
        )
        logger.exception(
            'SQLAlchemy async unsafe title load: field=%s rel_name=%s parent_model=%s parent_pk=%s model=%s pk=%s',
            field_slug,
            self.rel_name,
            type(parent_record).__name__,
            get_pk(parent_record),
            type(error.record).__name__,
            get_pk(error.record),
        )
        raise AdminAPIException(
            APIError(message=message, code='async_unsafe_title_load'),
            status_code=500,
        ) from error

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
        if obj is None:
            msg = _('related_not_found') % {
                'model': self.target_model.__name__,
                'pk': value,
                'field_slug': field_slug,
            }
            raise AdminAPIException(
                APIError(message=msg, code='related_not_found'),
                status_code=400,
            )
        setattr(record, rel_attr, obj)

    async def apply_filter(self, stmt, value, model, column):
        # pylint: disable=import-outside-toplevel
        from sqlalchemy import inspect

        if value is None:
            return stmt

        rel = getattr(model, self.rel_name)
        pk_col = inspect(self.target_model).primary_key[0]
        pk_type = pk_col.type.python_type

        # many=False: FK (many-to-one)
        if not self.many:
            value = self._cast_pk(value, pk_type)
            return stmt.where(rel.has(pk_col == value))

        # many=True: one-to-many / many-to-many
        if not isinstance(value, list):
            raise FieldError(EXPECTED_LIST_FOR_FILTER.format(rel_name=self.rel_name))
        value = [self._cast_pk(item, pk_type) for item in value]
        if not rel.property.uselist:
            return stmt.where(rel.has(pk_col.in_(value)))
        return stmt.where(rel.any(pk_col.in_(value)))
