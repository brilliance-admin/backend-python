import asyncio
import datetime
import random

from brilliance_admin.schema.dashboard.category_dashboard import ChartData
from brilliance_admin.schema.table.table_models import FilterSubtableData, FilterSubtableUnitSize
from example.config import settings

FAKE_DATA_SEED = 42


def get_value(point: datetime.datetime, unit_size: FilterSubtableUnitSize, randomizer: random.Random) -> int:
    if unit_size == FilterSubtableUnitSize.DAY:
        return 1800 + point.toordinal() % 700 + randomizer.randint(-80, 80)

    hour = point.hour + point.minute / 60
    daylight = max(0, 1 - abs(hour - 15) / 10)
    variation = point.hour % 5 * 7 + randomizer.randint(-12, 12)
    return int(20 + 260 * daylight + variation)


async def get_filter_subtable(subtable_data: FilterSubtableData) -> ChartData:
    await asyncio.sleep(settings.fake_delay_seconds)

    date_range = subtable_data.filters[subtable_data.field_slug]
    from_date = datetime.datetime.fromisoformat(date_range['from'])
    to_date = datetime.datetime.fromisoformat(date_range['to'])

    step = {
        FilterSubtableUnitSize.TEN_MINUTES: datetime.timedelta(minutes=10),
        FilterSubtableUnitSize.HOUR: datetime.timedelta(hours=1),
        FilterSubtableUnitSize.DAY: datetime.timedelta(days=1),
    }[subtable_data.unit_size]

    points = []
    point = from_date
    while point <= to_date:
        points.append(point)
        point += step

    randomizer = random.Random(FAKE_DATA_SEED)
    totals = [get_value(point, subtable_data.unit_size, randomizer) for point in points]
    errors = [max(1, total // 20 + point.hour % 3) for point, total in zip(points, totals)]
    other = [max(1, total // 10 + point.day % 4) for point, total in zip(points, totals)]
    success = [total - error - other_value for total, error, other_value in zip(totals, errors, other)]

    return ChartData(
        type='bar',
        data={
            'labels': [point.isoformat(sep=' ', timespec='minutes') for point in points],
            'datasets': [
                {'label': 'Success', 'data': success, 'backgroundColor': 'success'},
                {'label': 'Errors', 'data': errors, 'backgroundColor': 'error'},
                {'label': 'Other', 'data': other, 'backgroundColor': 'secondary'},
            ],
        },
        options={
            'scales': {
                'x': {'stacked': True},
                'y': {'stacked': True, 'beginAtZero': True},
            },
        },
    )
