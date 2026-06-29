from typing import Any

from asgiref.sync import sync_to_async
from django.db import models
from django.db.models import Q
from pydantic import BaseModel

from brilliance_admin.exceptions import AdminAPIException, APIError
from brilliance_admin.exceptions import FieldError
from brilliance_admin.schema.table.fields.base import RelatedField
from brilliance_admin.schema.table.table_models import AutocompleteData, Record

MISSING_RECORD_IN_CONTEXT = 'Missing record in serialize context in value: {value}'
RELATED_MISSING_ON_RECORD = (
    'Inline related field "{rel_name}" cannot be serialized from record "{record_type}". '
    'Expected inline row model to contain this relation.'
)
MANY_RELATED_MISSING = 'Many Related field "{rel_name}" is missing on record "{record}"'
AUTOCOMPLETE_REQUIRES_MODEL = (
    'DjangoRelatedField.autocomplete {class_name} requires extra["model"]'
)


class DjangoRelatedField(RelatedField):
    def _get_target_model(self, model, field_slug):
        model_field = model._meta.get_field(field_slug)
        return getattr(model_field, 'related_model', None)

    @staticmethod
    def _get_search_fields(model) -> list[str]:
        search_fields = getattr(model, '__search_fields__', None)
        if search_fields:
            return search_fields

        result = []
        for model_field in model._meta.fields:
            if isinstance(model_field, (models.CharField, models.TextField)):
                result.append(model_field.name)
        return result

    async def autocomplete(self, data: AutocompleteData, user, extra: dict | None = None) -> list[Record]:
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

        if data.search_string:
            search_fields = self._get_search_fields(target_model)
            if search_fields:
                query = Q()
                for field_name in search_fields:
                    query |= Q(**{f'{field_name}__icontains': data.search_string})
                queryset = queryset.filter(query)
            else:
                try:
                    queryset = queryset.filter(**{pk_name: pk_python(data.search_string)})
                except (TypeError, ValueError):
                    queryset = queryset.none()

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
            import inspect

            if inspect.iscoroutinefunction(self.filter_fn):
                queryset = await self.filter_fn(queryset, data, user)
            else:
                queryset = self.filter_fn(queryset, data, user)

        records = await sync_to_async(lambda: list(queryset[: min(150, data.limit)]), thread_sensitive=True)()
        return [Record(key=getattr(record, pk_name), title=str(record)) for record in records]

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
            return [{'key': obj.pk, 'title': str(obj)} for obj in related]

        related = await sync_to_async(getattr, thread_sensitive=True)(record, self.rel_name, None)

        if related is None:
            return None

        return {'key': related.pk, 'title': str(related)}
