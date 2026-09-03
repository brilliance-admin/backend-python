import pytest
from fastapi.testclient import TestClient

from brilliance_admin import schema
from brilliance_admin.auth import AdminAuthentication, UserABC
from brilliance_admin.exceptions import FieldError
from brilliance_admin.schema.table.admin_action import ActionData, ActionResult, admin_action
from brilliance_admin.schema.table.category_table import CategoryTable
from brilliance_admin.utils import DeserializeAction, validate_email


class TestAuth(AdminAuthentication):
    async def authenticate(self, headers):
        return UserABC(username='test')


class EmailActionCategory(CategoryTable):
    async def get_list(self, *args, **kwargs):
        raise NotImplementedError

    @admin_action(
        allow_empty_selection=True,
        form_schema=schema.FieldsSchema(
            email=schema.StringField(validator=validate_email),
        ),
    )
    async def validate_email_action(self, action_data, **kwargs):
        return ActionResult()


@pytest.mark.asyncio
async def test_optional_integer_rejects_none_when_minimum_configured():
    field = schema.IntegerField(required=False, min_value=1)

    with pytest.raises(FieldError):
        await field.deserialize_field(None, DeserializeAction.CREATE, extra={})


@pytest.mark.asyncio
async def test_required_integer_rejects_none():
    field = schema.IntegerField(required=True)

    with pytest.raises(FieldError, match='Field is required'):
        await field.deserialize_field(None, DeserializeAction.CREATE, extra={})


@pytest.mark.asyncio
async def test_integer_rejects_value_below_minimum():
    field = schema.IntegerField(required=False, min_value=1)

    with pytest.raises(FieldError):
        await field.deserialize_field(0, DeserializeAction.CREATE, extra={})


@pytest.mark.asyncio
async def test_optional_decimal_rejects_none_when_minimum_configured():
    field = schema.DecimalField(required=False, min_value=1)

    with pytest.raises(FieldError):
        await field.deserialize_field(None, DeserializeAction.CREATE, extra={})


@pytest.mark.asyncio
async def test_required_decimal_rejects_none():
    field = schema.DecimalField(required=True)

    with pytest.raises(FieldError, match='Field is required'):
        await field.deserialize_field(None, DeserializeAction.CREATE, extra={})


@pytest.mark.asyncio
async def test_decimal_rejects_value_below_minimum():
    field = schema.DecimalField(required=False, min_value=1)

    with pytest.raises(FieldError):
        await field.deserialize_field('0.5', DeserializeAction.CREATE, extra={})


@pytest.mark.asyncio
async def test_multiple_choice_outputs_selected_choices():
    field = schema.MultipleChoiceField(
        choices=[
            {'value': 'draft', 'title': 'Draft'},
            {'value': 'published', 'title': 'Published'},
        ],
    )

    assert await field.serialize(['draft', 'published'], extra={}) == [
        {'value': 'draft', 'title': 'Draft'},
        {'value': 'published', 'title': 'Published'},
    ]


@pytest.mark.asyncio
async def test_multiple_choice_updates_and_defaults_to_all_selected():
    field = schema.MultipleChoiceField(
        choices=[
            {'value': 'draft', 'title': 'Draft'},
            {'value': 'published', 'title': 'Published'},
        ],
        default_all_selected=True,
    )

    assert await field.deserialize_field(['published'], DeserializeAction.UPDATE, extra={}) == ['published']
    assert await field.deserialize_field(None, DeserializeAction.CREATE, extra={}) == ['draft', 'published']


def test_email_field_validator_is_translated():
    category = EmailActionCategory(
        slug='email',
        table_schema=schema.FieldsSchema(value=schema.StringField()),
    )
    admin_schema = schema.AdminSchema(
        auth=TestAuth(),
        categories=[
            schema.CategoryGroup(slug='test', subcategories=[category]),
        ],
    )
    app = admin_schema.generate_app()
    client = TestClient(app)

    response = client.post(
        app.url_path_for(
            'table_action',
            group='test',
            category='email',
            action='validate_email_action',
        ),
        headers={'Accept-Language': 'ru'},
        json=ActionData(form_data={'email': 'not-an-email'}).model_dump(mode='json'),
    )

    assert response.status_code == 400
    assert response.json()['field_errors']['email']['message'] == 'Введите корректный email'
