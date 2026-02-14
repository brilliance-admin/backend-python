import pytest
from fastapi.testclient import TestClient

from brilliance_admin.schema.table.table_models import AutocompleteData
from example.main import app
from example.sections.models import CurrencyFactory, MerchantFactory, TerminalFactory

client = TestClient(app)


@pytest.mark.asyncio
async def test_exception_handle(mocker):
    merchant = await MerchantFactory()
    currency = await CurrencyFactory()
    await TerminalFactory(title="first", merchant=merchant, currency=currency)
    await TerminalFactory(title="second", merchant=merchant, currency=currency)

    url = app.url_path_for(
        'autocomplete',
        group='payments',
        category='merchant',
    )
    request_data = AutocompleteData(
        search_string="",
        field_slug="terminals",
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
                'key': 1,
                'title': 'first',
            },
            {
                'key': 2,
                'title': 'second',
            },
        ],
    }
    assert response.json() == response_data
