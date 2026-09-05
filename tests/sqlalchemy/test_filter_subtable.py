from datetime import UTC, datetime

import pytest

from brilliance_admin import schema, sqlalchemy
from brilliance_admin.integrations.sqlalchemy.table.filter_subtable import PostgreSQLFilterSubtable
from example.sections.models import CurrencyFactory, MerchantFactory, Terminal, TerminalFactory


@pytest.mark.asyncio
async def test_postgresql_filter_subtable_applies_datetime_filter_and_search(postgres_sessionmaker):
    category = sqlalchemy.SQLAlchemyAdmin(
        model=Terminal,
        db_async_session=postgres_sessionmaker,
        search_fields=['title'],
        table_schema=sqlalchemy.SQLAlchemyFieldsSchema(model=Terminal, fields=['id']),
        table_filters=sqlalchemy.SQLAlchemyFieldsSchema(
            model=Terminal,
            fields=['created_at', 'is_active'],
            created_at=schema.DateTimeField(range=True),
        ),
    )
    merchant = await MerchantFactory()
    currency = await CurrencyFactory()
    await TerminalFactory(
        merchant=merchant,
        currency=currency,
        title='match first',
        is_active=True,
        created_at=datetime(2026, 9, 5, 0, 30, tzinfo=UTC),
    )
    await TerminalFactory(
        merchant=merchant,
        currency=currency,
        title='match second',
        is_active=False,
        created_at=datetime(2026, 9, 5, 1, 30, tzinfo=UTC),
    )
    await TerminalFactory(
        merchant=merchant,
        currency=currency,
        title='other',
        created_at=datetime(2026, 9, 5, 2, 30, tzinfo=UTC),
    )

    chart = await PostgreSQLFilterSubtable().get_filter_subtable(
        schema.FilterSubtableData(
            field_slug='created_at',
            unit_size=schema.FilterSubtableUnitSize.HOUR,
            filters={
                'created_at': {
                    'from': '2026-09-05T00:00:00+00:00',
                    'to': '2026-09-05T03:00:00+00:00',
                },
                'is_active': True,
            },
            search='match%',
        ),
        view=category,
    )

    assert chart.data['labels'] == [
        '2026-09-05 00:00',
        '2026-09-05 01:00',
        '2026-09-05 02:00',
    ]
    assert chart.data['datasets'] == [{'label': 'Count', 'data': [1, 0, 0]}]
