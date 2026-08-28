from unittest import mock
from enum import Enum

import pytest

from brilliance_admin import schema
from brilliance_admin.auth import UserABC
from brilliance_admin.schema.table.fields.function_field import function_field
from example.main import admin_schema
from example.sections.payments import PaymentsAdmin

category_schema_data = {
    'dashboard_info': None,
    'icon': 'mdi-credit-card-outline',
    'description': 'Статичные данные',
    'link': None,
    'categories': {},
    'table_info': mock.ANY,
    'title': 'Платежи',
    'type': 'table',
 }


@pytest.mark.asyncio
async def test_generate_category_schema(language_context):
    category = PaymentsAdmin()
    new_schema = category.generate_category_schema(UserABC(username="test"), language_context, admin_schema)
    assert new_schema.model_dump() == category_schema_data, new_schema.model_dump()


def test_function_field_choice_enum_schema(language_context):
    class ModerateStatus(Enum):
        WAIT = 'wait'
        APPROVED = 'approved'
        NOT_APPROVED = 'not_approved'

        @property
        def label(self):
            return self.value

        @property
        def tag_color(self):
            return 'green'

    class Fields(schema.FieldsSchema):
        @function_field(type=schema.ChoiceField, choices=ModerateStatus)
        async def moderate_status(self, **kwargs):
            return 'wait'

        @function_field(type=schema.ChoiceField(choices=ModerateStatus, size='small'))
        async def moderate_status_instance(self, **kwargs):
            return 'approved'

    fields = Fields()
    schema_data = fields.generate_form_schema(
        user=UserABC(username="test"),
        language_context=language_context,
    )

    fields_data = schema_data.model_dump(mode='json', context={'language_context': language_context})['fields']

    assert fields_data['moderate_status'] == {
        'choices': [
            {'tag_color': 'green', 'title': 'wait', 'value': 'wait'},
            {'tag_color': 'green', 'title': 'approved', 'value': 'approved'},
            {'tag_color': 'green', 'title': 'not_approved', 'value': 'not_approved'},
        ],
        'header': {},
        'label': 'Moderate Status',
        'read_only': True,
        'required': False,
        'size': 'default',
        'type': 'choice',
        'variant': 'elevated',
    }
    assert fields_data['moderate_status_instance'] == {
        **fields_data['moderate_status'],
        'label': 'Moderate Status Instance',
        'size': 'small',
    }


def test_integer_field_enum_choices_schema(language_context):
    class EndpointStatusChoice(Enum):
        WAIT = 1
        APPROVED = 2
        NOT_APPROVED = 3

        @property
        def label(self):
            return str(self.value)

        @property
        def tag_color(self):
            return 'green'

    class Fields(schema.FieldsSchema):
        status = schema.IntegerField(choices=EndpointStatusChoice)

    fields = Fields()
    schema_data = fields.generate_form_schema(
        user=UserABC(username="test"),
        language_context=language_context,
    )

    assert schema_data.model_dump(mode='json', context={'language_context': language_context})['fields']['status'] == {
        'choices': [
            {'tag_color': 'green', 'title': '1', 'value': 1},
            {'tag_color': 'green', 'title': '2', 'value': 2},
            {'tag_color': 'green', 'title': '3', 'value': 3},
        ],
        'header': {},
        'label': 'Status',
        'read_only': False,
        'required': False,
        'size': 'default',
        'type': 'integer',
        'variant': 'elevated',
    }
