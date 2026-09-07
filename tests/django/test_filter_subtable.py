from datetime import UTC, datetime

import pytest

from brilliance_admin import schema
from brilliance_admin.integrations.django import DjangoAdmin, DjangoFieldsSchema
from brilliance_admin.integrations.django.table.filter_subtable import DjangoPostgreSQLFilterSubtable
from example.sections.django_models import DjangoAnotherExample, DjangoAnotherExampleFactory


class DjangoFilterSubtableAdmin(DjangoAdmin):
    def get_queryset(self, *, action):
        return super().get_queryset(action=action).select_related('example')


@pytest.mark.asyncio
async def test_django_postgresql_filter_subtable_handles_joined_duplicate_datetime_columns():
    category = DjangoFilterSubtableAdmin(
        model=DjangoAnotherExample,
        search_fields=['title'],
        table_schema=DjangoFieldsSchema(model=DjangoAnotherExample, fields=['id']),
        table_filters=DjangoFieldsSchema(
            model=DjangoAnotherExample,
            fields=['created_at', 'is_active'],
            created_at=schema.DateTimeField(range=True),
        ),
    )
    first = await DjangoAnotherExampleFactory(title='match first', is_active=True)
    second = await DjangoAnotherExampleFactory(title='match second', is_active=False)
    third = await DjangoAnotherExampleFactory(title='other', is_active=True)

    await DjangoAnotherExample.objects.filter(pk=first.pk).aupdate(
        created_at=datetime(2026, 9, 5, 0, 30, tzinfo=UTC)
    )
    await DjangoAnotherExample.objects.filter(pk=second.pk).aupdate(
        created_at=datetime(2026, 9, 5, 1, 30, tzinfo=UTC)
    )
    await DjangoAnotherExample.objects.filter(pk=third.pk).aupdate(
        created_at=datetime(2026, 9, 5, 2, 30, tzinfo=UTC)
    )

    chart = await DjangoPostgreSQLFilterSubtable().get_filter_subtable(
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
