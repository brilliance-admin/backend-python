import pytest
from fastapi.testclient import TestClient

from brilliance_admin.schema.table.admin_action import ActionData
from example.main import app

client = TestClient(app)


@pytest.mark.asyncio
async def test_exception_handle(mocker):
    url = app.url_path_for(
        'table_action',
        group='payments',
        category='payments',
        action='action_with_exception',
    )
    request_data = ActionData()
    response = client.post(url, json=request_data.model_dump(mode='json'))
    assert response.status_code == 500, response.content.decode()
    response_data = {
        'code': 'user_action_error',
        'field_errors': None,
        'message': 'Exception example.',
    }
    assert response.json() == response_data
