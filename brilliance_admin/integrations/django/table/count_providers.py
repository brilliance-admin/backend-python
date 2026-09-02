from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import connections

from brilliance_admin.schema.table.count_providers import CountProvider, CountResult
from brilliance_admin.schema.table.table_models import ListData


class DjangoCountProvider(CountProvider):
    async def get_count(self, queryset, list_data: ListData) -> CountResult:
        count = await queryset.acount()
        return CountResult(
            total_count=str(count),
            pages_count=CountResult.get_pages_count(count, list_data.limit),
        )


class PostgresCounter(CountProvider):
    async def get_count(self, queryset, list_data: ListData) -> CountResult:
        if list_data.filters or list_data.search:
            return await self.get_capped_count(queryset, list_data)

        estimated_count = await sync_to_async(self.get_estimated_count, thread_sensitive=True)(queryset)
        if estimated_count >= 0:
            return CountResult(total_count=f'~{estimated_count}', pages_count=None)

        return await self.get_capped_count(queryset, list_data)

    @staticmethod
    async def get_capped_count(queryset, list_data: ListData) -> CountResult:
        limit = getattr(settings, 'BRILLIANCE_ADMIN_CAPPED_COUNT_LIMIT', 1000)
        if not isinstance(limit, int) or limit < 1:
            raise ImproperlyConfigured('BRILLIANCE_ADMIN_CAPPED_COUNT_LIMIT must be a positive integer')

        count = await queryset.order_by()[:limit + 1].acount()
        if count > limit:
            return CountResult(total_count=f'{limit}+', pages_count=None)

        return CountResult(
            total_count=str(count),
            pages_count=CountResult.get_pages_count(count, list_data.limit),
        )

    @staticmethod
    def get_estimated_count(queryset) -> int:
        with connections[queryset.db].cursor() as cursor:
            cursor.execute(
                'SELECT reltuples FROM pg_class WHERE oid = %s::regclass',
                [queryset.model._meta.db_table],
            )
            row = cursor.fetchone()

        if row is None:
            raise RuntimeError(f'PostgreSQL relation not found: {queryset.model._meta.db_table}')

        return round(row[0])
