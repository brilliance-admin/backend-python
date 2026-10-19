from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from brilliance_admin.api.views.table import router
from brilliance_admin.auth import UserABC
from brilliance_admin.schema.category import CategoryGroup
from brilliance_admin.schema.table.admin_action import admin_action
from brilliance_admin.schema.table.category_table import CategoryTable
from brilliance_admin.schema.table.fields.base import IntegerField
from brilliance_admin.schema.table.fields_schema import FieldsSchema
from brilliance_admin.translations import LanguageContext, LanguageManager
from example.sections.models import Currency, CurrencyFactory


async def max_default(*, user, category, parent_category, parent_pk, action_name, action_data):
    if action_data.send_to_all or not action_data.pks:
        return 1000

    async with category.db_async_session() as session:
        currency = await session.get(Currency, action_data.pks[0])
        if currency is None:
            raise ValueError(f'Currency {action_data.pks[0]} not found')
        return currency.depth


class DefaultForm(FieldsSchema):
    static = IntegerField(default=10)
    max_amount = IntegerField(default_fn=max_default)
    cleared = IntegerField(default=50, default_fn=lambda **context: None)


class GatewayCategory(CategoryTable):
    slug = 'gateways'
    table_schema = DefaultForm()

    async def get_list(self, *args, **kwargs):
        raise NotImplementedError()

    @admin_action(form_schema=DefaultForm())
    async def make_active_provider(self, action_data, user):
        raise AssertionError('Before create must not execute the action')


@pytest.fixture
def before_create_context(postgres_sessionmaker):
    user = UserABC(username='admin')
    category = GatewayCategory()
    category.db_async_session = postgres_sessionmaker
    parent = GatewayCategory(slug='parents', subcategories=[category])
    group = CategoryGroup(slug='test', subcategories=[parent])
    language_context = LanguageContext('en', LanguageManager({'en': 'English'}))
    app = FastAPI()
    app.include_router(router)
    app.state.schema = SimpleNamespace(
        auth=SimpleNamespace(authenticate=AsyncMock(return_value=user)),
        get_group=lambda slug: group if slug == 'test' else None,
        get_language_context=lambda slug: language_context,
        debug=False,
    )
    with TestClient(app) as client:
        yield SimpleNamespace(
            client=client,
        )


@pytest.mark.parametrize('for_action', [False, True])
def test_before_create_defaults(for_action, before_create_context):
    context = before_create_context
    action_name = 'make_active_provider' if for_action else None
    params = {'subcategory': 'gateways', 'parent_pk': '42'}
    if for_action:
        params['action_name'] = action_name
    payload = {
        'pks': [],
        'send_to_all': for_action,
        'filters': {'currency': 2},
        'search': 'gateway',
    }

    response = context.client.post('/table/test/parents/before-create/', params=params, json=payload)

    assert response.status_code == 200, response.text
    assert response.json() == {
        'form_data': {'static': 10, 'max_amount': 1000, 'cleared': None},
    }


@pytest.mark.asyncio
async def test_before_create_default_from_first_selected_record(before_create_context):
    first = await CurrencyFactory(depth=3)
    second = await CurrencyFactory(depth=2)

    response = before_create_context.client.post(
        '/table/test/parents/before-create/',
        params={
            'subcategory': 'gateways',
            'parent_pk': '42',
            'action_name': 'make_active_provider',
        },
        json={
            'pks': [first.id, second.id],
            'send_to_all': False,
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()['form_data']['max_amount'] == first.depth
