import datetime

from sqlalchemy import and_, func, literal, literal_column, select

from brilliance_admin.exceptions import FieldError
from brilliance_admin.schema.chart import ChartData
from brilliance_admin.schema.table.filter_subtable import FilterSubtable
from brilliance_admin.schema.table.table_models import FilterSubtableData, FilterSubtableUnitSize, ListData


class PostgreSQLFilterSubtable(FilterSubtable):
    def __init__(self, limit: int = 300):
        self.limit = limit

    async def get_queryset(self, subtable_data: FilterSubtableData, *, view):
        list_data = ListData(filters=subtable_data.filters, search=subtable_data.search)
        queryset = view.get_queryset()
        queryset = await view.apply_filters(queryset, list_data)
        return view.apply_search(queryset, list_data).order_by(None)

    async def get_data(
            self,
            queryset,
            *,
            date_from: datetime.datetime,
            date_to: datetime.datetime,
            step,
            field_slug: str,
            view,
    ):
        source = queryset.subquery()
        date_column = source.c.get(field_slug)
        pk_column = source.c.get(view.pk_name)
        if date_column is None or pk_column is None:
            raise FieldError(
                f'Filter "{field_slug}" and primary key "{view.pk_name}" must be model columns'
            )

        series = func.generate_series(
            date_from,
            literal(date_to) - step,
            step,
        ).table_valued('bucket').render_derived().alias('series')
        stmt = (
            select(
                series.c.bucket,
                func.count(pk_column).label('count'),
            )
            .select_from(
                series.outerjoin(
                    source,
                    and_(
                        date_column >= series.c.bucket,
                        date_column < series.c.bucket + step,
                    ),
                )
            )
            .group_by(series.c.bucket)
            .order_by(series.c.bucket)
        )

        async with view.db_async_session() as session:
            return (await session.execute(stmt)).all()

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

        python_step = {
            FilterSubtableUnitSize.TEN_MINUTES: datetime.timedelta(minutes=10),
            FilterSubtableUnitSize.HOUR: datetime.timedelta(hours=1),
            FilterSubtableUnitSize.DAY: datetime.timedelta(days=1),
        }[subtable_data.unit_size]
        sql_step = {
            FilterSubtableUnitSize.TEN_MINUTES: literal_column("interval '10 minutes'"),
            FilterSubtableUnitSize.HOUR: literal_column("interval '1 hour'"),
            FilterSubtableUnitSize.DAY: literal_column("interval '1 day'"),
        }[subtable_data.unit_size]

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
            step=sql_step,
            field_slug=subtable_data.field_slug,
            view=view,
        )

        return ChartData(
            type='bar',
            data={
                'labels': [row.bucket.replace(tzinfo=None).isoformat(sep=' ', timespec='minutes') for row in rows],
                'datasets': [{'label': 'Count', 'data': [row.count for row in rows]}],
            },
            options={'scales': {'y': {'beginAtZero': True}}},
        )
