from fastapi.testclient import TestClient

from brilliance_admin.permissions.interfaces import PermissionsManager, UserPermissions
from brilliance_admin.permissions.settings import PermissionsData
from brilliance_admin.schema.table.table_action import TableAction
from example.main import admin_schema, app

client = TestClient(app)


class ApiUserPermissions(UserPermissions):
    def get_permissions_data(self):
        return PermissionsData([])

    def __init__(self, user, denied_category, denied_action, denied_action_name):
        super().__init__(user)
        self.denied_category = denied_category
        self.denied_action = denied_action
        self.denied_action_name = denied_action_name

    def has_action_permission(self, category, action_type, action_name=None):
        return not (
            category is self.denied_category
            and action_type == self.denied_action
            and action_name == self.denied_action_name
        )


class ApiPermissionsManager(PermissionsManager):
    def __init__(self, denied_category, denied_action, denied_action_name=None):
        self.denied_category = denied_category
        self.denied_action = denied_action
        self.denied_action_name = denied_action_name

    async def get_user_permissions(self, user, for_schema_generation):
        return ApiUserPermissions(user, self.denied_category, self.denied_action, self.denied_action_name)


def deny_permission(mocker, category, action_type, action_name=None):
    manager = ApiPermissionsManager(category, action_type, action_name)
    get_permissions = mocker.spy(manager, 'get_user_permissions')
    mocker.patch.object(admin_schema, 'permissions_manager', manager)
    return get_permissions


def assert_denied(response, handler, get_permissions):
    assert response.status_code == 403, response.text
    assert response.json() == {'detail': 'Permission denied'}
    handler.assert_not_called()
    get_permissions.assert_called_once()
    assert get_permissions.call_args.args[0].username == 'test_admin'
    assert get_permissions.call_args.kwargs == {'for_schema_generation': False}


def test_list_denied(mocker):
    category = admin_schema.get_group('payments').get_category('merchant')
    get_permissions = deny_permission(mocker, category, TableAction.LIST)
    handler = mocker.spy(category, 'get_list')

    response = client.post(app.url_path_for('table_list', group='payments', category='merchant'), json={})

    assert_denied(response, handler, get_permissions)


def test_retrieve_denied(mocker):
    category = admin_schema.get_group('payments').get_category('merchant')
    get_permissions = deny_permission(mocker, category, TableAction.RETRIEVE)
    handler = mocker.spy(category, 'retrieve')

    response = client.post(
        app.url_path_for('table_retrieve', group='payments', category='merchant', pk='1'), json={},
    )

    assert_denied(response, handler, get_permissions)


def test_create_denied(mocker):
    category = admin_schema.get_group('payments').get_category('merchant')
    get_permissions = deny_permission(mocker, category, TableAction.CREATE)
    handler = mocker.spy(category, 'create')

    response = client.post(
        app.url_path_for('table_create', group='payments', category='merchant'), json={'title': 'Forbidden'},
    )

    assert_denied(response, handler, get_permissions)


def test_update_denied(mocker):
    category = admin_schema.get_group('payments').get_category('merchant')
    get_permissions = deny_permission(mocker, category, TableAction.UPDATE)
    handler = mocker.spy(category, 'update')

    response = client.patch(
        app.url_path_for('table_update', group='payments', category='merchant', pk='1'), json={'title': 'Forbidden'},
    )

    assert_denied(response, handler, get_permissions)


def test_action_selected_denied(mocker):
    category = admin_schema.get_group('payments').get_category('merchant')
    get_permissions = deny_permission(mocker, category, TableAction.ADMIN_ACTION, 'delete')
    handler = mocker.spy(category, '_perform_action')

    response = client.post(
        app.url_path_for('table_action', group='payments', category='merchant', action='delete'), json={'pks': [1]},
    )

    assert_denied(response, handler, get_permissions)


def test_action_send_to_all_denied(mocker):
    category = admin_schema.get_group('payments').get_category('merchant')
    get_permissions = deny_permission(mocker, category, TableAction.ADMIN_ACTION, 'delete')
    handler = mocker.spy(category, '_perform_action')

    response = client.post(
        app.url_path_for('table_action', group='payments', category='merchant', action='delete'),
        json={'send_to_all': True, 'filters': {'is_active': True}, 'search': 'test'},
    )

    assert_denied(response, handler, get_permissions)


def test_create_defaults_denied(mocker):
    category = admin_schema.get_group('payments').get_category('merchant')
    get_permissions = deny_permission(mocker, category, TableAction.CREATE)
    handler = mocker.spy(category, '_before_create')

    response = client.post(app.url_path_for('before_create', group='payments', category='merchant'), json={})

    assert_denied(response, handler, get_permissions)


def test_action_defaults_denied(mocker):
    category = admin_schema.get_group('payments').get_category('payments')
    get_permissions = deny_permission(mocker, category, TableAction.ADMIN_ACTION, 'create_payment')
    handler = mocker.spy(category, '_before_create')

    response = client.post(
        app.url_path_for('before_create', group='payments', category='payments'),
        params={'action_name': 'create_payment'}, json={'pks': [1]},
    )

    assert_denied(response, handler, get_permissions)


def test_action_defaults_send_to_all_denied(mocker):
    category = admin_schema.get_group('payments').get_category('payments')
    get_permissions = deny_permission(mocker, category, TableAction.ADMIN_ACTION, 'create_payment')
    handler = mocker.spy(category, '_before_create')

    response = client.post(
        app.url_path_for('before_create', group='payments', category='payments'),
        params={'action_name': 'create_payment'},
        json={'send_to_all': True, 'filters': {'status': 'success'}, 'search': 'test'},
    )

    assert_denied(response, handler, get_permissions)


def test_filter_subtable_denied(mocker):
    category = admin_schema.get_group('payments').get_category('payments')
    get_permissions = deny_permission(mocker, category, TableAction.LIST)
    handler = mocker.spy(category, '_get_subtable_data')

    response = client.post(
        app.url_path_for('filter_subtable', group='payments', category='payments', field_slug='created_at'),
        json={'unit_size': '1day'},
    )

    assert_denied(response, handler, get_permissions)


def test_autocomplete_denied(mocker):
    category = admin_schema.get_group('payments').get_category('terminal')
    get_permissions = deny_permission(mocker, category, TableAction.LIST)
    handler = mocker.spy(category, 'autocomplete')

    response = client.post(
        app.url_path_for('autocomplete', group='payments', category='terminal'),
        params={'field_slug': 'currency_id'}, json={},
    )

    assert_denied(response, handler, get_permissions)


def test_filter_autocomplete_denied(mocker):
    category = admin_schema.get_group('payments').get_category('terminal')
    get_permissions = deny_permission(mocker, category, TableAction.LIST)
    handler = mocker.spy(category, 'autocomplete')

    response = client.post(
        app.url_path_for('autocomplete', group='payments', category='terminal'),
        params={'field_slug': 'currency_id'}, json={'is_filter': True},
    )

    assert_denied(response, handler, get_permissions)


def test_action_autocomplete_denied(mocker):
    category = admin_schema.get_group('payments').get_category('payments')
    get_permissions = deny_permission(mocker, category, TableAction.ADMIN_ACTION, 'change_amount')
    handler = mocker.spy(category, 'autocomplete')

    response = client.post(
        app.url_path_for('autocomplete', group='payments', category='payments'),
        params={'field_slug': 'amount'}, json={'action_name': 'change_amount'},
    )

    assert_denied(response, handler, get_permissions)


def test_subcategory_list_denied(mocker):
    category = admin_schema.get_group('payments').get_category('merchant').get_subcategory('terminal')
    get_permissions = deny_permission(mocker, category, TableAction.LIST)
    handler = mocker.spy(category, 'get_list')

    response = client.post(
        app.url_path_for('table_list', group='payments', category='merchant'),
        params={'subcategory': 'terminal', 'parent_pk': 1}, json={},
    )

    assert_denied(response, handler, get_permissions)


def test_subcategory_retrieve_denied(mocker):
    category = admin_schema.get_group('payments').get_category('merchant').get_subcategory('terminal')
    get_permissions = deny_permission(mocker, category, TableAction.RETRIEVE)
    handler = mocker.spy(category, 'retrieve')

    response = client.post(
        app.url_path_for('table_retrieve', group='payments', category='merchant', pk='1'),
        params={'subcategory': 'terminal', 'parent_pk': 1}, json={},
    )

    assert_denied(response, handler, get_permissions)


def test_subcategory_create_denied(mocker):
    category = admin_schema.get_group('payments').get_category('merchant').get_subcategory('terminal')
    get_permissions = deny_permission(mocker, category, TableAction.CREATE)
    handler = mocker.spy(category, 'create')

    response = client.post(
        app.url_path_for('table_create', group='payments', category='merchant'),
        params={'subcategory': 'terminal', 'parent_pk': 1}, json={'title': 'Forbidden'},
    )

    assert_denied(response, handler, get_permissions)


def test_subcategory_update_denied(mocker):
    category = admin_schema.get_group('payments').get_category('merchant').get_subcategory('terminal')
    get_permissions = deny_permission(mocker, category, TableAction.UPDATE)
    handler = mocker.spy(category, 'update')

    response = client.patch(
        app.url_path_for('table_update', group='payments', category='merchant', pk='1'),
        params={'subcategory': 'terminal', 'parent_pk': 1}, json={'title': 'Forbidden'},
    )

    assert_denied(response, handler, get_permissions)


def test_subcategory_action_denied(mocker):
    category = admin_schema.get_group('payments').get_category('merchant').get_subcategory('terminal')
    get_permissions = deny_permission(mocker, category, TableAction.ADMIN_ACTION, 'delete')
    handler = mocker.spy(category, '_perform_action')

    response = client.post(
        app.url_path_for('table_action', group='payments', category='merchant', action='delete'),
        params={'subcategory': 'terminal', 'parent_pk': 1}, json={'pks': [1]},
    )

    assert_denied(response, handler, get_permissions)


def test_subcategory_defaults_denied(mocker):
    category = admin_schema.get_group('payments').get_category('merchant').get_subcategory('terminal')
    get_permissions = deny_permission(mocker, category, TableAction.CREATE)
    handler = mocker.spy(category, '_before_create')

    response = client.post(
        app.url_path_for('before_create', group='payments', category='merchant'),
        params={'subcategory': 'terminal', 'parent_pk': 1}, json={},
    )

    assert_denied(response, handler, get_permissions)


def test_subcategory_autocomplete_denied(mocker):
    category = admin_schema.get_group('payments').get_category('merchant').get_subcategory('terminal')
    get_permissions = deny_permission(mocker, category, TableAction.LIST)
    handler = mocker.spy(category, 'autocomplete')

    response = client.post(
        app.url_path_for('autocomplete', group='payments', category='merchant'),
        params={'subcategory': 'terminal', 'parent_pk': 1, 'field_slug': 'currency_id'}, json={},
    )

    assert_denied(response, handler, get_permissions)


def test_dashboard_denied(mocker):
    category = admin_schema.get_group('main').get_category('dashboard')
    get_permissions = deny_permission(mocker, category, TableAction.LIST)
    handler = mocker.spy(category, 'get_data')

    response = client.post(app.url_path_for('dashboard_data', group='main', category='dashboard'), json={})

    assert_denied(response, handler, get_permissions)


def test_subcategory_dashboard_denied(mocker):
    group = admin_schema.get_group('payments')
    parent = group.get_category('terminal')
    category = parent.get_subcategory('terminal-dashboard')
    get_permissions = deny_permission(mocker, category, TableAction.LIST)
    handler = mocker.spy(category, 'get_data')

    response = client.post(
        app.url_path_for('dashboard_data', group='payments', category='terminal'),
        params={'subcategory': 'terminal-dashboard', 'parent_pk': 1},
        json={},
    )

    assert_denied(response, handler, get_permissions)
