import inspect
from typing import Any, Callable

from asgiref.sync import sync_to_async
from django.core.exceptions import SynchronousOnlyOperation, ValidationError as DjangoValidationError
from pydantic.dataclasses import dataclass
from pydantic import BaseModel

from brilliance_admin.exceptions import AdminAPIException, APIError, AsyncUnsafeTitleLoad, FieldError
from brilliance_admin.schema.table.fields.base import RelatedField
from brilliance_admin.schema.table.table_models import AutocompleteData, Record
from brilliance_admin.utils import DeserializeAction, get_logger

logger = get_logger()

MISSING_RECORD_IN_CONTEXT = 'Missing record in serialize context in value: {value}'
RELATED_MISSING_ON_RECORD = (
    'Inline related field "{rel_name}" cannot be serialized from record "{record_type}". '
    'Expected inline row model to contain this relation.'
)
MANY_RELATED_MISSING = 'Many Related field "{rel_name}" is missing on record "{record}"'
RELATED_GET_QUERYSET_RESULT_ERROR = (
    '{class_name}.get_queryset() must return Django QuerySet, got {result_type}'
)
AUTOCOMPLETE_REQUIRES_MODEL = (
    'DjangoRelatedField.autocomplete {class_name} requires extra["model"]'
)
RELATED_LOAD_ERROR = (
    "Failed to load related field \"{field}\" for model \"{model}\" pk={pk}: {error}"
)
ADMIN_TITLE_MUST_BE_ASYNC = (
    '{model}.admin_title must be async def, got {value_type}'
)

ASYNC_LAZY_RELATED_LOAD_ERROR = (
    "SynchronousOnlyOperation: Async unsafe lazy related load: field=\"{field}\" model=\"{model}\" pk={pk}. "
    "Add select_related('{field}') to get_queryset(), or avoid sync lazy relation access "
    "in async serialization; use async ORM in admin_title() when extra data is needed."
)
TITLE_ASYNC_UNSAFE_HINT = (
    'SynchronousOnlyOperation: Add required select_related() to get_queryset(), or define async admin_title().'
)


def get_str_source(record) -> str:
    try:
        source = inspect.getsource(type(record).__str__)
    except (OSError, TypeError):
        return ''

    return f'\n__str__ source:\n{source}'


async def get_record_title(
    record,
    raise_async_unsafe,
    *,
    parent_record=None,
    field_slug: str | None = None,
    rel_name: str | None = None,
    debug: bool = False,
) -> str:
    admin_title = getattr(record, 'admin_title', None)
    if admin_title is None:
        try:
            return record.__str__()
        except SynchronousOnlyOperation as e:
            error = AsyncUnsafeTitleLoad(
                record,
                get_str_source(record),
                backend='django',
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
                    getattr(parent_record, 'pk', None),
                    type(error.record).__name__,
                    getattr(error.record, 'pk', None),
                    error.hint,
                    error.source,
                )
            return await sync_to_async(str, thread_sensitive=True)(record)

    if not inspect.iscoroutinefunction(admin_title):
        msg = ADMIN_TITLE_MUST_BE_ASYNC.format(
            model=type(record).__name__,
            value_type=type(admin_title).__name__,
        )
        raise AttributeError(msg)

    return await admin_title()


@dataclass
class DjangoRelatedField(RelatedField):
    get_queryset: Callable[[Any, dict], Any] | None = None
    select_related: list[str] | None = None
    prefetch_related: list[str] | None = None

    def _cast_pk(self, value, model):
        target_model = model._meta.get_field(self.rel_name).related_model
        try:
            return target_model._meta.pk.to_python(value)
        except (TypeError, ValueError, DjangoValidationError) as e:
            raise FieldError(str(e)) from e

    async def deserialize_field(self, value, action: DeserializeAction, extra: dict, *args, **kwargs):
        value = await super().deserialize_field(value, action, extra, *args, **kwargs)
        if value is None or action != DeserializeAction.FILTERS:
            return value

        if isinstance(value, list):
            return [self._cast_pk(pk, extra['model']) for pk in value]
        return self._cast_pk(value, extra['model'])

    def _validate_queryset(self, queryset):
        # pylint: disable=import-outside-toplevel
        from django.db.models import QuerySet

        if not isinstance(queryset, QuerySet):
            msg = RELATED_GET_QUERYSET_RESULT_ERROR.format(
                class_name=type(self).__name__,
                result_type=type(queryset).__name__,
            )
            raise TypeError(msg)

    async def _get_many_queryset(self, manager, extra):
        if self.get_queryset is None:
            queryset = manager.all()
            if self.select_related:
                queryset = queryset.select_related(*self.select_related)
            if self.prefetch_related:
                queryset = queryset.prefetch_related(*self.prefetch_related)
        elif inspect.iscoroutinefunction(self.get_queryset):
            queryset = await self.get_queryset(manager, extra)
        else:
            queryset = self.get_queryset(manager, extra)

        self._validate_queryset(queryset)
        return queryset

    def _get_target_model(self, model, field_slug):
        model_field = model._meta.get_field(field_slug)
        return getattr(model_field, 'related_model', None)

    @staticmethod
    def _get_search_fields(model) -> list[str]:
        from django.db import models

        search_fields = getattr(model, '__search_fields__', None)
        if search_fields:
            return search_fields

        result = []
        for model_field in model._meta.fields:
            if isinstance(model_field, (models.CharField, models.TextField)):
                result.append(model_field.name)
        return result

    async def _get_autocomplete_queryset(
        self,
        data: AutocompleteData,
        user,
        extra: dict | None = None,
    ):
        if extra is None or extra.get('model') is None:
            msg = AUTOCOMPLETE_REQUIRES_MODEL.format(class_name=type(self).__name__)
            raise AttributeError(msg)

        model = extra['model']
        target_model = self._get_target_model(model, data.field_slug)
        if target_model is None:
            return []

        queryset = target_model.objects.all()
        if self.get_queryset is None:
            if self.select_related:
                queryset = queryset.select_related(*self.select_related)
            if self.prefetch_related:
                queryset = queryset.prefetch_related(*self.prefetch_related)
        elif inspect.iscoroutinefunction(self.get_queryset):
            queryset = await self.get_queryset(queryset, data, user)
        else:
            queryset = self.get_queryset(queryset, data, user)
        self._validate_queryset(queryset)
        pk_field = target_model._meta.pk
        pk_name = pk_field.name
        pk_python = pk_field.to_python

        if data.existed_choices:
            pks = []
            for item in data.existed_choices:
                if isinstance(item, BaseModel):
                    item = item.model_dump()
                if isinstance(item, dict) and 'key' in item:
                    try:
                        pks.append(pk_python(item['key']))
                    except (TypeError, ValueError) as e:
                        raise AdminAPIException(
                            APIError(message=f'Invalid existed_choices value "{item["key"]}"'),
                            status_code=500,
                        ) from e
            if pks:
                queryset = queryset.filter(**{f'{pk_name}__in': pks})

        if self.filter_fn:
            if inspect.iscoroutinefunction(self.filter_fn):
                queryset = await self.filter_fn(queryset, data, user)
            else:
                queryset = self.filter_fn(queryset, data, user)

        return queryset, pk_name

    def _apply_autocomplete_search(self, queryset, data: AutocompleteData, pk_name: str):
        if not data.search_string:
            return queryset

        from django.db.models import Q

        target_model = queryset.model
        search_fields = self._get_search_fields(target_model)
        if search_fields:
            query = Q()
            for field_name in search_fields:
                query |= Q(**{f'{field_name}__icontains': data.search_string})
            return queryset.filter(query)

        pk_field = target_model._meta.pk
        try:
            return queryset.filter(**{pk_name: pk_field.to_python(data.search_string)})
        except (TypeError, ValueError):
            return queryset.none()

    async def autocomplete(
        self,
        data: AutocompleteData,
        user,
        extra: dict | None = None,
        parent_category=None,
        parent_pk=None,
        debug: bool = False,
    ) -> list[Record]:
        queryset, pk_name = await self._get_autocomplete_queryset(data, user, extra)
        queryset = self._apply_autocomplete_search(queryset, data, pk_name)
        records = [record async for record in queryset[: min(150, data.limit)]]
        result = []
        for record in records:
            try:
                title = await get_record_title(
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
                    f'model="{type(e.record).__name__}" pk={getattr(e.record, "pk", None)}. '
                    f'{e.hint}'
                    f'{e.source}'
                )
                logger.exception(
                    'Async unsafe autocomplete title load: field=%s rel_name=%s model=%s pk=%s',
                    data.field_slug,
                    self.rel_name,
                    type(e.record).__name__,
                    getattr(e.record, 'pk', None),
                )
                raise AdminAPIException(
                    APIError(message=message, code='async_unsafe_title_load'),
                    status_code=500,
                ) from e
            result.append(Record(key=getattr(record, pk_name), title=title))
        return result

    async def autocomplete_total_count(
        self,
        data: AutocompleteData,
        user,
        extra: dict | None = None,
        parent_category=None,
        parent_pk=None,
    ) -> int:
        queryset, _ = await self._get_autocomplete_queryset(data, user, extra)
        return await queryset.acount()

    def _raise_title_load_error(self, error: AsyncUnsafeTitleLoad, parent_record):
        error.rel_name = self.rel_name
        error.parent_record = parent_record
        logger.exception(
            'Async unsafe title load: rel_name=%s parent_model=%s parent_pk=%s model=%s pk=%s',
            self.rel_name,
            type(parent_record).__name__,
            getattr(parent_record, 'pk', None),
            type(error.record).__name__,
            getattr(error.record, 'pk', None),
        )
        raise error

    async def serialize(self, value, extra: dict, field_slug: str | None = None, *args, **kwargs):
        if not value:
            return None

        record = extra.get('record')
        if record is None:
            raise FieldError(MISSING_RECORD_IN_CONTEXT.format(value=value))

        if not hasattr(type(record), self.rel_name):
            raise FieldError(RELATED_MISSING_ON_RECORD.format(
                rel_name=self.rel_name,
                record_type=type(record).__name__,
            ))

        if self.many:
            manager = getattr(record, self.rel_name, None)
            if manager is None:
                raise FieldError(MANY_RELATED_MISSING.format(rel_name=self.rel_name, record=record))
            queryset = await self._get_many_queryset(manager, extra)
            related = [obj async for obj in queryset]
            result = []
            for obj in related:
                try:
                    title = await get_record_title(
                        obj,
                        extra.get('raise_async_unsafe'),
                        parent_record=record,
                        field_slug=field_slug,
                        rel_name=self.rel_name,
                        debug=extra.get('debug', False),
                    )
                except AsyncUnsafeTitleLoad as e:
                    self._raise_title_load_error(e, record)
                result.append({'key': obj.pk, 'title': title})
            return result

        try:
            related = getattr(record, self.rel_name, None)
        except SynchronousOnlyOperation as e:
            msg = ASYNC_LAZY_RELATED_LOAD_ERROR.format(
                field=self.rel_name,
                model=type(record).__name__,
                pk=getattr(record, 'pk', None),
            )
            if extra.get('raise_async_unsafe'):
                logger.exception(
                    'Async unsafe lazy related load: field=%s model=%s pk=%s',
                    self.rel_name,
                    type(record).__name__,
                    getattr(record, 'pk', None),
                )
                raise AdminAPIException(
                    APIError(message=msg, code='async_lazy_related_load'),
                    status_code=500,
                ) from e
            if extra.get('debug'):
                logger.warning(msg)
            related = await sync_to_async(
                getattr,
                thread_sensitive=True,
            )(record, self.rel_name, None)
        except Exception as e:
            logger.exception(
                'Related load failed: field=%s model=%s pk=%s error=%s',
                self.rel_name,
                type(record).__name__,
                getattr(record, 'pk', None),
                str(e),
            )
            msg = RELATED_LOAD_ERROR.format(
                field=self.rel_name,
                model=type(record).__name__,
                pk=getattr(record, 'pk', None),
                error=e,
            )
            raise AdminAPIException(
                APIError(message=msg, code='field_error'),
                status_code=500,
            ) from e

        if related is None:
            return None

        try:
            title = await get_record_title(
                related,
                extra.get('raise_async_unsafe'),
                parent_record=record,
                field_slug=field_slug,
                rel_name=self.rel_name,
                debug=extra.get('debug', False),
            )
        except AsyncUnsafeTitleLoad as e:
            self._raise_title_load_error(e, record)

        return {'key': related.pk, 'title': title}
