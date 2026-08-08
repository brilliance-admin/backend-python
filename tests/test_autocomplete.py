import pytest
from fastapi.testclient import TestClient

from brilliance_admin.schema.table.table_models import AutocompleteData
from example.main import app
from example.sections.models import UserFactory

client = TestClient(app)


@pytest.mark.asyncio
async def test_autocomplete_filter_fn(mocker):
    user_1 = await UserFactory(username='active', is_active=True)
    user_2 = await UserFactory(username='not_active', is_active=False)

    url = app.url_path_for(
        'autocomplete',
        group='users',
        category='usersession',
    )
    request_data = AutocompleteData(
        search_string="",
        field_slug="user_id",
        is_filter=True,
        form_data={},
        existed_choices=[],
        limit=30,
    )
    response = client.post(url, json=request_data.model_dump(mode='json'))
    assert response.status_code == 200, response.content.decode()
    response_data = {
        'results': [
            {
                'key': user_1.id,
                'title': 'User #1 "active"',
            },
        ],
        'total_count': 1,
    }
    assert response.json() == response_data
