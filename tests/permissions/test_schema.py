import pytest

from brilliance_admin.auth import UserABC
from brilliance_admin.permissions.interfaces import PermissionsManager, UserPermissions
from brilliance_admin.permissions.settings import PermissionsData
from brilliance_admin.schema.table.table_action import TableAction
from example.main import admin_schema


class SchemaUserPermissions(UserPermissions):
    def get_permissions_data(self):
        return PermissionsData([])

    def __init__(self, user, denied_category, denied_action):
        super().__init__(user)
        self.denied_category = denied_category
        self.denied_action = denied_action

    def has_action_permission(self, category, action_type, action_name=None):
        if category is not self.denied_category or action_type != self.denied_action:
            return True
        if action_type == TableAction.ADMIN_ACTION:
            return action_name != 'delete'
        return False


class SchemaPermissionsManager(PermissionsManager):
    def __init__(self, denied_category, denied_action):
        self.denied_category = denied_category
        self.denied_action = denied_action

    def get_user_permissions(self, user, for_schema_generation):
        return SchemaUserPermissions(user, self.denied_category, self.denied_action)


def generate_schema_with_denied_action(mocker, denied_action, subcategory):
    user = UserABC(username='test_admin')
    merchant = admin_schema.get_group('payments').get_category('merchant')
    category = merchant.get_subcategory('terminal') if subcategory else merchant
    manager = SchemaPermissionsManager(category, denied_action)
    get_permissions = mocker.spy(manager, 'get_user_permissions')
    generate_category = mocker.spy(category, 'generate_category_schema')
    mocker.patch.object(admin_schema, 'permissions_manager', manager)

    result = admin_schema.generate_admin_schema(user, 'en')

    get_permissions.assert_called_once_with(user, for_schema_generation=True)
    categories = result.categories['payments']['categories']
    sibling = categories['terminal']['table_info']
    assert sibling['can_retrieve'] is True
    assert sibling['can_create'] is True
    assert sibling['can_update'] is True
    assert 'delete' in sibling['actions']
    if subcategory:
        categories = categories['merchant']['table_info']['subcategories']
    return categories, category.slug, generate_category


@pytest.mark.parametrize('subcategory', [False, True])
def test_schema_list_permission(subcategory, mocker):
    categories, slug, generate_category = generate_schema_with_denied_action(mocker, TableAction.LIST, subcategory)

    assert slug not in categories
    generate_category.assert_not_called()


@pytest.mark.parametrize('subcategory', [False, True])
def test_schema_retrieve_permission(subcategory, mocker):
    categories, slug, generate_category = generate_schema_with_denied_action(mocker, TableAction.RETRIEVE, subcategory)

    table = categories[slug]['table_info']
    assert table['can_retrieve'] is False
    assert table['can_create'] is True
    assert table['can_update'] is True
    assert 'delete' in table['actions']
    generate_category.assert_called_once()


@pytest.mark.parametrize('subcategory', [False, True])
def test_schema_create_permission(subcategory, mocker):
    categories, slug, generate_category = generate_schema_with_denied_action(mocker, TableAction.CREATE, subcategory)

    table = categories[slug]['table_info']
    assert table['can_create'] is False
    assert table['can_retrieve'] is True
    assert table['can_update'] is True
    assert 'delete' in table['actions']
    generate_category.assert_called_once()


@pytest.mark.parametrize('subcategory', [False, True])
def test_schema_update_permission(subcategory, mocker):
    categories, slug, generate_category = generate_schema_with_denied_action(mocker, TableAction.UPDATE, subcategory)

    table = categories[slug]['table_info']
    assert table['can_update'] is False
    assert table['can_retrieve'] is True
    assert table['can_create'] is True
    assert 'delete' in table['actions']
    generate_category.assert_called_once()


@pytest.mark.parametrize('subcategory', [False, True])
def test_schema_admin_action_permission(subcategory, mocker):
    categories, slug, generate_category = generate_schema_with_denied_action(mocker, TableAction.ADMIN_ACTION, subcategory)

    table = categories[slug]['table_info']
    assert 'delete' not in table['actions']
    assert table['can_retrieve'] is True
    assert table['can_create'] is True
    assert table['can_update'] is True
    generate_category.assert_called_once()
