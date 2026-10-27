from fastapi.testclient import TestClient

from brilliance_admin import schema
from brilliance_admin.auth import AdminAuthentication
from brilliance_admin.exceptions import AdminAPIException, APIError
from brilliance_admin.schema.table.admin_action import admin_action


class DeniedAuth(AdminAuthentication):
    async def authenticate(self, headers):
        raise AdminAPIException(
            APIError(code='unauthorized'),
            status_code=401,
        )


class ProtectedCategory(schema.CategoryTable):
    slug = 'protected'
    table_schema = schema.FieldsSchema(id=schema.IntegerField())

    async def get_list(self, *args, **kwargs):
        raise AssertionError('Category handler called after authentication was denied')

    retrieve = get_list
    create = get_list
    update = get_list
    _before_create = get_list
    autocomplete = get_list
    _get_subtable_data = get_list

    @admin_action()
    async def blocked(self, *args, **kwargs):
        raise AssertionError('Action called after authentication was denied')


class ProtectedDashboard(schema.CategoryDashboard):
    slug = 'dashboard'

    async def get_data(self, *args, **kwargs):
        raise AssertionError('Dashboard called after authentication was denied')


AUTH_SCHEMA = schema.AdminSchema(
    auth=DeniedAuth(),
    categories=[
        schema.CategoryGroup(
            slug='group',
            subcategories=[ProtectedCategory(), ProtectedDashboard()],
        ),
    ],
)

APP = AUTH_SCHEMA.generate_app()
CLIENT = TestClient(APP)


def test_list_no_auth():
    response = CLIENT.post(
        APP.url_path_for(
            'table_list',
            group='group',
            category='protected',
        ),
        json={},
    )

    assert response.status_code == 401


def test_schema_no_auth():
    response = CLIENT.get(APP.url_path_for('schema_handler'))

    assert response.status_code == 401


def test_retrieve_no_auth():
    response = CLIENT.post(
        APP.url_path_for('table_retrieve', group='group', category='protected', pk='1'),
        json={},
    )

    assert response.status_code == 401


def test_create_no_auth():
    response = CLIENT.post(
        APP.url_path_for('table_create', group='group', category='protected'),
        json={},
    )

    assert response.status_code == 401


def test_update_no_auth():
    response = CLIENT.patch(
        APP.url_path_for('table_update', group='group', category='protected', pk='1'),
        json={},
    )

    assert response.status_code == 401


def test_action_no_auth():
    response = CLIENT.post(
        APP.url_path_for('table_action', group='group', category='protected', action='blocked'),
        json={'pks': [1]},
    )

    assert response.status_code == 401


def test_defaults_no_auth():
    response = CLIENT.post(
        APP.url_path_for('before_create', group='group', category='protected'),
        json={},
    )

    assert response.status_code == 401


def test_autocomplete_no_auth():
    response = CLIENT.post(
        APP.url_path_for('autocomplete', group='group', category='protected'),
        params={'field_slug': 'id'},
        json={},
    )

    assert response.status_code == 401


def test_dashboard_no_auth():
    response = CLIENT.post(
        APP.url_path_for('dashboard_data', group='group', category='dashboard'),
        json={},
    )

    assert response.status_code == 401


def test_subtable_no_auth():
    response = CLIENT.post(
        APP.url_path_for('filter_subtable', group='group', category='protected', field_slug='id'),
        json={'unit_size': '1day'},
    )

    assert response.status_code == 401
