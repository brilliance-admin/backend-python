import re
import time

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
    filter_only: bool = False

    def get_list_field_slugs(self) -> list[str]:
        return list(self.table_schema.list_display or self.table_schema.get_fields().keys())

    def optimize_list_queryset(self, queryset):
        if not self.filter_only:
            return queryset

        model = queryset.model
        model_field_names = {field.name for field in model._meta.fields}
        model_many_to_many_names = {field.name for field in model._meta.many_to_many}
        only_fields = {model._meta.pk.name}

        for field_slug in self.get_list_field_slugs():
            field = self.table_schema.get_field(field_slug)
            if field is None:
                continue

            if isinstance(field, RelatedField):
                if field_slug not in model_field_names:
                    continue

                only_fields.add(field_slug)
                continue

            if field_slug in model_field_names or field_slug in model_many_to_many_names:
                only_fields.add(field_slug)

        return queryset.only(*sorted(only_fields))

    @staticmethod
    def get_debug_info_from_context(ctx):
        return schema.DebugInfo(
            db_query_count=len(ctx),
            queries=[
                schema.DebugQuery(
                    sql=query['sql'],
                    time_ms=float(query['time']) * 1000 if query.get('time') else None,
                )
                for query in ctx.captured_queries
            ],
        )

    @staticmethod
    def _load_page_with_query_count(queryset, offset, limit):
        connection = connections[queryset.db]
        with CaptureQueriesContext(connection) as ctx:
            total_count = queryset.count()
            records = list(queryset[offset:offset + limit])
        return total_count, records, DjangoAdminListMixin.get_debug_info_from_context(ctx)

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

    @staticmethod
    def search_to_regex(value: str) -> str:
        if len(value) >= 2 and value.startswith('"') and value.endswith('"'):
            return '^' + re.escape(value[1:-1]) + '$'

        return DjangoAdminListMixin.like_to_regex(value)

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
        from django.db.models import CharField, Q
        from django.db.models.functions import Cast

        if not self.search_fields or not list_data.search:
            return queryset

        regex = self.search_to_regex(list_data.search)
        query = Q()
        for index, field_slug in enumerate(self.search_fields):
            queryset, lookup, value = self.get_search_lookup(
                queryset,
                field_slug,
                regex,
                CharField,
                Cast,
                alias=f'_search_text_{index}',
            )
            query |= Q(**{lookup: value})
        return queryset.filter(query)

    def get_search_lookup(self, queryset, field_slug, regex, char_field_cls, cast_cls, alias):
        model_field, json_tail = self.resolve_lookup_path(field_slug)

        internal_type = model_field.get_internal_type()
        if internal_type in {'CharField', 'TextField', 'SlugField', 'EmailField', 'URLField'}:
            return queryset, f'{field_slug}__iregex', regex

        if internal_type == 'JSONField' and json_tail:
            return queryset, f'{field_slug}__iregex', regex

        queryset = queryset.alias(**{
            alias: cast_cls(field_slug, output_field=char_field_cls()),
        })
        return queryset, f'{alias}__iregex', regex

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
            total_count, records, debug_info = await sync_to_async(
                self._load_page_with_query_count,
                thread_sensitive=True,
            )(queryset, offset, limit)
        else:
            total_count = await queryset.acount()
            records = [record async for record in queryset[offset:offset + limit]]

        serialize_started_at = time.perf_counter()
        data = []
        for record in records:
            line = await self.table_schema.serialize(
                record,
                extra={
                    "record": record,
                    "user": user,
                    "debug": debug,
                    "raise_async_unsafe": self.raise_async_unsafe,
                },
                field_slugs=list_field_slugs,
            )
            data.append(line)

        if debug_info is not None:
            debug_info.serialize_ms = round((time.perf_counter() - serialize_started_at) * 1000, 2)

        return schema.TableListResult(data=data, total_count=total_count, debug_info=debug_info)
