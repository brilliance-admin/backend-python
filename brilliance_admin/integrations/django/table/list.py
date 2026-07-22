import re

from asgiref.sync import sync_to_async
from django.db import connections
from django.test.utils import CaptureQueriesContext

from brilliance_admin import schema
from brilliance_admin.exceptions import FieldError
from brilliance_admin.integrations.django.fields_schema import DjangoFieldsSchema
from brilliance_admin.schema.table.fields.base import DateTimeField, RelatedField

ORDERING_NOT_ALLOWED = (
    'Ordering "{ordering}" is not allowed;'
    ' available options: {ordering_fields}'
    ' default_ordering: {default_ordering}'
)


class DjangoAdminListMixin:
    table_filters: DjangoFieldsSchema | None

    def get_list_field_slugs(self) -> list[str]:
        return list(self.table_schema.list_display or self.table_schema.get_fields().keys())

    def optimize_list_queryset(self, queryset):
        model = queryset.model
        model_field_names = {field.name for field in model._meta.fields}
        model_many_to_many_names = {field.name for field in model._meta.many_to_many}
        only_fields = {model._meta.pk.name}
        select_related_fields = set()
        prefetch_related_fields = set()

        for field_slug in self.get_list_field_slugs():
            field = self.table_schema.get_field(field_slug)
            if field is None:
                continue

            if isinstance(field, RelatedField):
                if field.many:
                    prefetch_related_fields.add(field.rel_name)
                    continue

                if field_slug not in model_field_names:
                    continue

                select_related_fields.add(field.rel_name)
                only_fields.add(field_slug)

                target_model = model._meta.get_field(field_slug).related_model
                if target_model is not None:
                    for target_field in target_model._meta.fields:
                        only_fields.add(f'{field_slug}__{target_field.name}')
                continue

            if field_slug in model_field_names or field_slug in model_many_to_many_names:
                only_fields.add(field_slug)

        if select_related_fields:
            queryset = queryset.select_related(*sorted(select_related_fields))

        if prefetch_related_fields:
            queryset = queryset.prefetch_related(*sorted(prefetch_related_fields))

        return queryset.only(*sorted(only_fields))

    @staticmethod
    def _load_page_with_query_count(queryset, offset, limit):
        connection = connections[queryset.db]
        with CaptureQueriesContext(connection) as ctx:
            total_count = queryset.count()
            records = list(queryset[offset:offset + limit])
        return total_count, records, len(ctx)

    @staticmethod
    def like_to_regex(value: str) -> str:
        parts = []
        for char in value:
            if char == '%':
                parts.append('.*')
            elif char == '_':
                parts.append('.')
            else:
                parts.append(re.escape(char))
        return '^' + ''.join(parts) + '$'

    def apply_ordering(self, queryset, list_data):
        ordering = list_data.ordering or self.default_ordering
        if not ordering:
            return queryset

        normalized = ordering[1:] if ordering.startswith('-') else ordering
        if list_data.ordering and self.ordering_fields and normalized not in self.ordering_fields:
            msg = ORDERING_NOT_ALLOWED.format(
                ordering=normalized,
                ordering_fields=self.ordering_fields,
                default_ordering=self.default_ordering,
            )
            raise FieldError(message=msg, field_slug='ordering')

        return queryset.order_by(ordering)

    def apply_search(self, queryset, list_data):
        from django.db.models import Q

        if not self.search_fields or not list_data.search:
            return queryset

        regex = self.like_to_regex(list_data.search)
        query = Q()
        for field_slug in self.search_fields:
            lookup, value = self.get_search_lookup(field_slug, list_data.search, regex)
            query |= Q(**{lookup: value})
        return queryset.filter(query)

    def get_search_lookup(self, field_slug, raw_value, regex):
        model_field, json_tail = self.resolve_lookup_path(field_slug)

        internal_type = model_field.get_internal_type()
        if internal_type in {'CharField', 'TextField', 'SlugField', 'EmailField', 'URLField'}:
            return f'{field_slug}__iregex', regex

        if internal_type == 'JSONField' and json_tail:
            return field_slug, raw_value

        return field_slug, raw_value

    async def apply_filters(self, queryset, list_data):
        if not self.table_filters or not list_data.filters:
            return queryset

        for field_slug, raw_value in list_data.filters.items():
            field = self.table_filters.get_field(field_slug)
            if field is None:
                raise AttributeError(
                    f'{type(self.table_filters).__name__} filter "{field_slug}" not found'
                )

            if isinstance(field, RelatedField):
                if isinstance(raw_value, dict):
                    queryset = queryset.filter(**{field_slug: raw_value.get('key')})
                elif isinstance(raw_value, list):
                    values = [item.get('key') for item in raw_value if isinstance(item, dict) and 'key' in item]
                    queryset = queryset.filter(**{f'{field_slug}__in': values})
                else:
                    queryset = queryset.filter(**{field_slug: raw_value})
                continue

            if isinstance(field, DateTimeField) and field.range and isinstance(raw_value, dict):
                if raw_value.get('from') is not None:
                    queryset = queryset.filter(**{f'{field_slug}__gte': raw_value['from']})
                if raw_value.get('to') is not None:
                    queryset = queryset.filter(**{f'{field_slug}__lte': raw_value['to']})
                continue

            if isinstance(raw_value, str):
                if '%' in raw_value or '_' in raw_value:
                    queryset = queryset.filter(**{f'{field_slug}__iregex': self.like_to_regex(raw_value)})
                else:
                    queryset = queryset.filter(**{field_slug: raw_value})
                continue

            if isinstance(raw_value, list):
                queryset = queryset.filter(**{f'{field_slug}__in': raw_value})
                continue

            queryset = queryset.filter(**{field_slug: raw_value})

        return queryset

    async def get_list(
        self,
        list_data,
        user,
        language_context,
        debug: bool,
        parent_category=None,
        parent_pk=None,
    ):
        queryset = self.get_queryset()
        queryset = self.apply_parent_filter(queryset, parent_category, parent_pk)
        queryset = await self.apply_filters(queryset, list_data)
        queryset = self.apply_search(queryset, list_data)
        queryset = self.apply_ordering(queryset, list_data)
        queryset = self.optimize_list_queryset(queryset)

        page = max(1, list_data.page or 1)
        limit = min(150, max(1, list_data.limit or 25))
        offset = (page - 1) * limit
        list_field_slugs = self.get_list_field_slugs()

        debug_info = None
        if debug:
            total_count, records, db_query_count = await sync_to_async(
                self._load_page_with_query_count,
                thread_sensitive=True,
            )(queryset, offset, limit)
            debug_info = {"db_query_count": db_query_count}
        else:
            total_count = await queryset.acount()
            records = [record async for record in queryset[offset:offset + limit]]

        data = []
        for record in records:
            line = await self.table_schema.serialize(
                record,
                extra={"record": record, "user": user, "debug": debug},
                field_slugs=list_field_slugs,
            )
            data.append(line)

        return schema.TableListResult(data=data, total_count=total_count, debug_info=debug_info)
