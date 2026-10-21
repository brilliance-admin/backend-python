from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from brilliance_admin.api.views.table import router
from brilliance_admin.auth import UserABC
from brilliance_admin.permissions.interfaces import PermissionsManager, UserPermissions
from brilliance_admin.schema.category import CategoryGroup
from brilliance_admin.schema.table.admin_action import admin_action
from brilliance_admin.schema.table.category_table import CategoryTable
from brilliance_admin.schema.table.fields.base import IntegerField
from brilliance_admin.schema.table.fields_schema import FieldsSchema
from brilliance_admin.translations import LanguageContext, LanguageManager


class DenyAllUserPermissions(UserPermissions):
    def has_action_permission(self, category, action_type, action_name=None):
        return False


class DenyAllPermissionsManager(PermissionsManager):
    def get_user_permissions(self, user, for_schema_generation):
        return DenyAllUserPermissions(user)


async def max_default(*, user, category, parent_category, parent_pk, action_name, action_data):
    raise AssertionError('Denied request must not compute defaults')


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
def before_create_context():
    user = UserABC(username='admin')
    category = GatewayCategory()
    parent = GatewayCategory(slug='parents', subcategories=[category])
    group = CategoryGroup(slug='test', subcategories=[parent])
    language_context = LanguageContext('en', LanguageManager({'en': 'English'}))
    app = FastAPI()
    app.include_router(router)
    app.state.schema = SimpleNamespace(
        auth=SimpleNamespace(authenticate=AsyncMock(return_value=user)),
        permissions_manager=DenyAllPermissionsManager(),
        get_group=lambda slug: group if slug == 'test' else None,
        get_language_context=lambda slug: language_context,
        debug=False,
    )
    with TestClient(app) as client:
        yield SimpleNamespace(
            client=client,
        )


def test_before_create_denies_all(before_create_context, mocker):
    client = before_create_context.client
    category = client.app.state.schema.get_group('test').get_category('parents').get_subcategory('gateways')
    handler = mocker.spy(category, '_before_create')

    response = client.post(
        '/table/test/parents/before-create/',
        params={'subcategory': 'gateways', 'parent_pk': '42', 'action_name': 'make_active_provider'},
        json={'send_to_all': True},
    )

    assert response.status_code == 403, response.text
    handler.assert_not_called()
