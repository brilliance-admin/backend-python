from fastapi.testclient import TestClient

from example.main import admin_app


client = TestClient(admin_app)


def test_dashboard_subcategory_uses_query_param_like_table():
    response = client.post(
        '/dashboard/payments/terminal/?subcategory=terminal-dashboard&parent_pk=15',
        json={
            'search': None,
            'filters': {},
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data['component_type'] == 'container'
    assert [component['component_type'] for component in data['components']] == [
        'container',
        'container',
        'container',
        'container',
    ]
    assert data['components'][0]['components'][0]['component_type'] == 'chart'
    assert data['components'][0]['components'][0]['options']['plugins']['title']['text'] == 'Payments: count and amount'
