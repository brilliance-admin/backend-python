import pytest
from fastapi.testclient import TestClient

from brilliance_admin.schema.table.admin_action import ActionData
from example.main import app
from example.sections.models import CurrencyFactory, Merchant, MerchantFactory, TerminalFactory

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


@pytest.mark.asyncio
async def test_change_password(mocker):
    url = app.url_path_for(
        'table_action',
        group='users',
        category='user',
        action='change_password',
    )
    request_data = ActionData(
        pks=[70],
        form_data={"new_password": "123123"},
    )
    response = client.post(url, json=request_data.model_dump(mode='json'))
    assert response.status_code == 200, response.content.decode()
    assert response.json() == {"message": "Password successfully updated", "persistent_message": None}


@pytest.mark.asyncio
async def test_delete_payment(mocker):
    url = app.url_path_for(
        'table_action',
        group='payments',
        category='payments',
        action='delete',
    )
    request_data = ActionData(
        pks=[100500],
    )
    response = client.post(url, json=request_data.model_dump(mode='json'))
    assert response.status_code == 200, response.content.decode()
    assert response.json() == {"message": None, "persistent_message": None}


@pytest.mark.asyncio
async def test_delete(postgres_sessionmaker):
    merchant = await MerchantFactory()
    url = app.url_path_for(
        'table_action',
        group='payments',
        category='merchant',
        action='delete',
    )
    request_data = ActionData(
        pks=[merchant.id],
    )
    response = client.post(url, json=request_data.model_dump(mode='json'))
    assert response.status_code == 200, response.content.decode()
    assert response.json() == {"message": "The entries were successfully deleted.", "persistent_message": None}

    async with postgres_sessionmaker() as session:
        result = await session.get(Merchant, merchant.id)
        assert result is None


@pytest.mark.asyncio
async def test_delete_integrity_error(postgres_sessionmaker):
    merchant = await MerchantFactory()
    currency = await CurrencyFactory()
    await TerminalFactory(merchant=merchant, currency=currency)

    url = app.url_path_for(
        'table_action',
        group='payments',
        category='merchant',
        action='delete',
    )
    request_data = ActionData(
        pks=[merchant.id],
    )
    response = client.post(url, json=request_data.model_dump(mode='json'))
    assert response.status_code == 400, response.content.decode()
    assert response.json() == {
        "message": "Cannot delete: related records exist: terminal.merchant_id",
        "code": None,
        "field_errors": None,
    }

    async with postgres_sessionmaker() as session:
        result = await session.get(Merchant, merchant.id)
        assert result is not None
