import datetime

from brilliance_admin.exceptions import FieldError
from brilliance_admin.schema.chart import ChartData
from brilliance_admin.schema.table.filter_subtable import FilterSubtable
from brilliance_admin.schema.table.table_models import FilterSubtableData, FilterSubtableUnitSize, ListData


class DjangoPostgreSQLFilterSubtable(FilterSubtable):
    def __init__(self, limit: int = 300):
        self.limit = limit

    async def get_queryset(self, subtable_data: FilterSubtableData, *, view):
        list_data = ListData(filters=subtable_data.filters, search=subtable_data.search)
        queryset = view.get_queryset(action='list')
        queryset = await view.apply_filters(queryset, list_data)
        return view.apply_search(queryset, list_data).order_by()

    @staticmethod
    def _get_data(
            queryset,
            *,
            date_from: datetime.datetime,
            date_to: datetime.datetime,
            interval: str,
            field_slug: str,
    ):
        from django.core.exceptions import FieldDoesNotExist
        from django.db import connections

        try:
            date_field = queryset.model._meta.get_field(field_slug)
        except FieldDoesNotExist as e:
            raise FieldError(f'Filter "{field_slug}" must be a model field') from e

        if not getattr(date_field, 'column', None):
            raise FieldError(f'Filter "{field_slug}" must be a model column')

        connection = connections[queryset.db]
        quote_name = connection.ops.quote_name
        pk_field = queryset.model._meta.pk
        queryset = queryset.values(date_field.name, pk_field.name)
        date_column = quote_name(date_field.name)
        pk_column = quote_name(pk_field.name)
        queryset_sql, queryset_params = queryset.query.sql_with_params()

        sql = f'''
            SELECT
                series.bucket,
                COUNT(source.{pk_column}) AS count
            FROM generate_series(
                %s::timestamptz,
                %s::timestamptz - %s::interval,
                %s::interval
            ) AS series(bucket)
            LEFT JOIN ({queryset_sql}) AS source
                ON source.{date_column} >= series.bucket
                AND source.{date_column} < series.bucket + %s::interval
            GROUP BY series.bucket
            ORDER BY series.bucket
        '''
        params = [date_from, date_to, interval, interval, *queryset_params, interval]

        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()

    async def get_data(
            self,
            queryset,
            *,
            date_from: datetime.datetime,
            date_to: datetime.datetime,
            interval: str,
            field_slug: str,
    ):
        from asgiref.sync import sync_to_async

        return await sync_to_async(self._get_data, thread_sensitive=True)(
            queryset,
            date_from=date_from,
            date_to=date_to,
            interval=interval,
            field_slug=field_slug,
        )

    async def get_filter_subtable(
            self,
            subtable_data: FilterSubtableData,
            *,
            view,
    ) -> ChartData:
        try:
            date_range = subtable_data.filters[subtable_data.field_slug]
            date_from = datetime.datetime.fromisoformat(date_range['from'])
            date_to = datetime.datetime.fromisoformat(date_range['to'])
        except (KeyError, TypeError, ValueError) as e:
            raise FieldError(f'Filter "{subtable_data.field_slug}" must contain a datetime range') from e

        if date_from >= date_to:
            raise FieldError(f'Filter "{subtable_data.field_slug}" range must have from before to')

        steps = {
            FilterSubtableUnitSize.TEN_MINUTES: (datetime.timedelta(minutes=10), '10 minutes'),
            FilterSubtableUnitSize.HOUR: (datetime.timedelta(hours=1), '1 hour'),
            FilterSubtableUnitSize.DAY: (datetime.timedelta(days=1), '1 day'),
        }
        python_step, sql_interval = steps[subtable_data.unit_size]

        points_count = (date_to - date_from) // python_step
        if (date_to - date_from) % python_step:
            points_count += 1
        if points_count > self.limit:
            raise FieldError(f'Too many chart sections: {points_count}. Maximum is {self.limit}.')

        queryset = await self.get_queryset(subtable_data, view=view)
        rows = await self.get_data(
            queryset,
            date_from=date_from,
            date_to=date_to,
            interval=sql_interval,
            field_slug=subtable_data.field_slug,
        )

        return ChartData(
            type='bar',
            data={
                'labels': [bucket.replace(tzinfo=None).isoformat(sep=' ', timespec='minutes') for bucket, _ in rows],
                'datasets': [{'label': 'Count', 'data': [count for _, count in rows]}],
            },
            options={'scales': {'y': {'beginAtZero': True}}},
        )
