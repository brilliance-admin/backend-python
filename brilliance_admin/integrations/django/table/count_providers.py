from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import connections

from brilliance_admin.schema.table.count_providers import CountProvider, CountResult


class DjangoCountProvider(CountProvider):
    def __init__(self, max_count: int | None = None):
        if max_count is not None and (not isinstance(max_count, int) or max_count < 1):
            raise ValueError('max_count must be a positive integer or None')

        self.max_count = max_count

    async def get_count(self, queryset, *, category, has_filters: bool, limit: int) -> CountResult:
        if self.max_count is None:
            count = await queryset.acount()
        else:
            count = await queryset.order_by()[:self.max_count + 1].acount()
            if count > self.max_count:
                return CountResult(total_count=f'{self.max_count}+', pages_count=None)

        return CountResult(
            total_count=str(count),
            pages_count=CountResult.get_pages_count(count, limit),
        )


class PostgresCounter(CountProvider):
    async def get_count(self, queryset, *, category, has_filters: bool, limit: int) -> CountResult:
        if has_filters:
            return await self.get_capped_count(queryset, limit=limit)

        estimated_count = await sync_to_async(self.get_estimated_count, thread_sensitive=True)(queryset)
        if estimated_count >= 0:
            return CountResult(total_count=f'~{estimated_count}', pages_count=None)

        return await self.get_capped_count(queryset, limit=limit)

    @staticmethod
    async def get_capped_count(queryset, *, limit: int) -> CountResult:
        capped_count_limit = getattr(settings, 'BRILLIANCE_ADMIN_CAPPED_COUNT_LIMIT', 1000)
        if not isinstance(capped_count_limit, int) or capped_count_limit < 1:
            raise ImproperlyConfigured('BRILLIANCE_ADMIN_CAPPED_COUNT_LIMIT must be a positive integer')

        count = await queryset.order_by()[:capped_count_limit + 1].acount()
        if count > capped_count_limit:
            return CountResult(total_count=f'{capped_count_limit}+', pages_count=None)

        return CountResult(
            total_count=str(count),
            pages_count=CountResult.get_pages_count(count, limit),
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
