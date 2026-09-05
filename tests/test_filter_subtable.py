import pytest
from fastapi.testclient import TestClient

from brilliance_admin.schema.table.table_models import FilterSubtableData, FilterSubtableUnitSize
from example.main import app

client = TestClient(app)


@pytest.mark.asyncio
async def test_payment_created_at_filter_subtable_uses_selected_range():
    subtable_data = FilterSubtableData(
        unit_size=FilterSubtableUnitSize.HOUR,
        filters={
            'created_at': {
                'from': '2026-09-05T00:00:00',
                'to': '2026-09-05T15:00:00',
            },
        },
    )
    url = app.url_path_for(
        'filter_subtable',
        group='payments',
        category='payments',
        field_slug='created_at',
    )

    response = client.post(url, json=subtable_data.model_dump(mode='json'))

    assert response.status_code == 200, response.content.decode()
    chart = response.json()['chart']
    assert chart['data']['labels'][0] == '2026-09-05 00:00'
    assert chart['data']['labels'][-1] == '2026-09-05 15:00'
    assert len(chart['data']['labels']) == 16
    assert chart['data']['datasets'][0]['data'][15] > chart['data']['datasets'][0]['data'][0]
