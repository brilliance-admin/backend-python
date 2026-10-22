import pytest
from fastapi.testclient import TestClient

from brilliance_admin.schema.admin_schema import AdminSchema
from brilliance_admin.schema.category import CategoryGroup
from brilliance_admin.schema.table.admin_action import admin_action
from brilliance_admin.schema.table.category_table import CategoryTable
from brilliance_admin.schema.table.fields.base import IntegerField, RelatedField
from brilliance_admin.schema.table.fields_schema import FieldsSchema
from brilliance_admin.schema.table.table_models import AutocompleteData, AutocompleteResult, Record
from example.main import admin_schema, app
from example.sections.models import UserFactory

client = TestClient(app)


class ActionRelatedField(RelatedField):
    async def autocomplete(self, data, user, extra, **kwargs):
        return AutocompleteResult(
            records=[Record(key=1, title=data.search_string)],
            current_count=1,
            total_count='1',
        )


class ActionAutocompleteForm(FieldsSchema):
    target = ActionRelatedField()


class ActionAutocompleteCategory(CategoryTable):
    slug = 'action-autocomplete'
    table_schema = FieldsSchema(id=IntegerField())

    async def get_list(self, *args, **kwargs):
        raise AssertionError('Autocomplete must not retrieve the table list')

    @admin_action(form_schema=ActionAutocompleteForm())
    async def assign(self, *args, **kwargs):
        raise AssertionError('Autocomplete must not execute the action')


action_category = ActionAutocompleteCategory()
action_group = CategoryGroup(slug='autocomplete-actions', subcategories=[action_category])
action_schema = AdminSchema(
    auth=admin_schema.auth,
    categories=[action_group],
)
action_app = action_schema.generate_app()
action_client = TestClient(action_app)


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
    response = client.post(
        url,
        params={'field_slug': request_data.field_slug},
        json=request_data.model_dump(mode='json', exclude={'field_slug'}),
    )
    assert response.status_code == 200, response.content.decode()
    response_data = {
        'records': [
            {
                'key': user_1.id,
                'title': 'User #1 "active"',
            },
        ],
        'current_count': 1,
        'total_count': '1',
    }
    assert response.json() == response_data


def test_autocomplete_action_related_field():
    url = action_app.url_path_for(
        'autocomplete',
        group=action_group.slug,
        category=action_category.slug,
    )
    response = action_client.post(
        url,
        params={'field_slug': 'target'},
        json={'action_name': 'assign', 'search_string': 'example'},
    )

    assert response.status_code == 200, response.text
    assert response.json() == {
        'records': [{'key': 1, 'title': 'example'}],
        'current_count': 1,
        'total_count': '1',
    }
