import inspect

from asgiref.sync import sync_to_async
from django.core.exceptions import SynchronousOnlyOperation
from pydantic import BaseModel

from brilliance_admin.exceptions import AdminAPIException, APIError, FieldError
from brilliance_admin.schema.table.fields.base import RelatedField
from brilliance_admin.schema.table.table_models import AutocompleteData, Record
from brilliance_admin.utils import get_logger

logger = get_logger()

MISSING_RECORD_IN_CONTEXT = 'Missing record in serialize context in value: {value}'
RELATED_MISSING_ON_RECORD = (
    'Inline related field "{rel_name}" cannot be serialized from record "{record_type}". '
    'Expected inline row model to contain this relation.'
)
MANY_RELATED_MISSING = 'Many Related field "{rel_name}" is missing on record "{record}"'
AUTOCOMPLETE_REQUIRES_MODEL = (
    'DjangoRelatedField.autocomplete {class_name} requires extra["model"]'
)
RELATED_LOAD_ERROR = (
    "Failed to load related field \"{field}\" for model \"{model}\" pk={pk}: {error}"
)
ASYNC_LAZY_RELATED_LOAD_ERROR = (
    "Async unsafe lazy related load: field=\"{field}\" model=\"{model}\" pk={pk}. "
    "Add select_related('{field}') to get_queryset(), or avoid sync lazy relation access "
    "in async serialization; use async ORM in admin_title() when extra data is needed."
)
ADMIN_TITLE_MUST_BE_ASYNC = (
    '{model}.admin_title must be async def, got {value_type}'
)
TITLE_ASYNC_UNSAFE_ERROR = (
    'Async unsafe title load: model="{model}" pk={pk}. '
    'Add required select_related() to get_queryset(), or define async admin_title().'
    '{source}'
)


def get_str_source(record) -> str:
    try:
        source = inspect.getsource(type(record).__str__)
    except (OSError, TypeError):
        return ''

    return f'\n__str__ source:\n{source}'


async def get_record_title(record) -> str:
    admin_title = getattr(record, 'admin_title', None)
    if admin_title is None:
        try:
            return record.__str__()
        except SynchronousOnlyOperation as e:
            msg = TITLE_ASYNC_UNSAFE_ERROR.format(
                model=type(record).__name__,
                pk=getattr(record, 'pk', None),
                source=get_str_source(record),
            )
            logger.exception(
                'Async unsafe title load: model=%s pk=%s',
                type(record).__name__,
                getattr(record, 'pk', None),
            )
            raise AdminAPIException(
                APIError(message=msg, code='async_unsafe_title_load'),
                status_code=500,
            ) from e

    if not inspect.iscoroutinefunction(admin_title):
        msg = ADMIN_TITLE_MUST_BE_ASYNC.format(
            model=type(record).__name__,
            value_type=type(admin_title).__name__,
        )
        raise AttributeError(msg)

    return await admin_title()


class DjangoRelatedField(RelatedField):
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

    async def autocomplete(self, data: AutocompleteData, user, extra: dict | None = None) -> list[Record]:
        queryset, pk_name = await self._get_autocomplete_queryset(data, user, extra)
        queryset = self._apply_autocomplete_search(queryset, data, pk_name)
        records = [record async for record in queryset[: min(150, data.limit)]]
        return [
            Record(
                key=getattr(record, pk_name),
                title=await get_record_title(record)
            )
            for record in records
        ]

    async def autocomplete_total_count(self, data: AutocompleteData, user, extra: dict | None = None) -> int:
        queryset, _ = await self._get_autocomplete_queryset(data, user, extra)
        return await queryset.acount()

    async def serialize(self, value, extra: dict, *args, **kwargs):
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
            related = await sync_to_async(lambda: list(getattr(record, self.rel_name).all()), thread_sensitive=True)()
            if related is None:
                raise FieldError(MANY_RELATED_MISSING.format(rel_name=self.rel_name, record=record))
            return [
                {'key': obj.pk, 'title': await get_record_title(obj)}
                for obj in related
            ]

        try:
            related = getattr(record, self.rel_name, None)
        except SynchronousOnlyOperation as e:
            msg = ASYNC_LAZY_RELATED_LOAD_ERROR.format(
                field=self.rel_name,
                model=type(record).__name__,
                pk=getattr(record, 'pk', None),
            )
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

        return {'key': related.pk, 'title': await get_record_title(related)}
