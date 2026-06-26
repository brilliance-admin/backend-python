import pytest
from fastapi.testclient import TestClient

from brilliance_admin.auth import UserABC
from brilliance_admin.integrations.django import DjangoFieldsSchema
from brilliance_admin.integrations.django.table import DjangoAdmin
from example.main import admin_app
from example.sections.django_models import DjangoExample

FORM_SCHEMA_DATA = {
    'categories': {},
    'dashboard_info': None,
    'description': None,
    'icon': None,
    'link': None,
    'table_info': {
        'actions': {
            'delete': {
                'allow_empty_selection': False,
                'base_color': 'red-lighten-2',
                'confirmation_text': 'Вы уверены, что хотите удалить данные записи?\n'
                'Данное действие нельзя отменить.',
                'description': None,
                'form_schema': None,
                'icon': 'mdi-delete-outline',
                'title': 'Удалить',
                'variant': 'outlined',
            },
        },
        'can_create': True,
        'can_retrieve': True,
        'can_update': True,
        'default_ordering': '-id',
        'ordering_fields': [],
        'pk_name': 'id',
        'search_enabled': False,
        'search_help': None,
        'subcategories': {},
        'table_filters': None,
        'table_schema': {
            'fields': {
                'allowed_ips': {
                    'array_type': 'string',
                    'header': {},
                    'label': 'Allowed Ips',
                    'read_only': False,
                    'required': False,
                    'type': 'array',
                },
                'count': {
                    'header': {},
                    'label': 'Count',
                    'read_only': False,
                    'required': False,
                    'type': 'integer',
                },
                'created_at': {
                    'header': {},
                    'include_date': True,
                    'include_time': True,
                    'label': 'Created At',
                    'read_only': True,
                    'required': False,
                    'type': 'datetime',
                },
                'description': {
                    'header': {},
                    'label': 'Description',
                    'max_length': 255,
                    'password': False,
                    'read_only': False,
                    'required': False,
                    'type': 'string',
                },
                'event_date': {
                    'header': {},
                    'include_date': True,
                    'include_time': False,
                    'label': 'Event Date',
                    'read_only': False,
                    'required': False,
                    'type': 'datetime',
                },
                'event_time': {
                    'header': {},
                    'include_date': False,
                    'include_time': True,
                    'label': 'Event Time',
                    'read_only': False,
                    'required': False,
                    'type': 'datetime',
                },
                'file': {
                    'header': {},
                    'label': 'File',
                    'read_only': False,
                    'required': False,
                    'type': 'file',
                },
                'id': {
                    'header': {},
                    'label': 'ID',
                    'read_only': True,
                    'required': False,
                    'type': 'integer',
                },
                'image': {
                    'header': {},
                    'label': 'Image',
                    'preview_max_height': 100,
                    'preview_max_width': 100,
                    'read_only': False,
                    'required': False,
                    'type': 'image',
                },
                'is_active': {
                    'header': {},
                    'label': 'Is Active',
                    'read_only': False,
                    'required': False,
                    'type': 'boolean',
                },
                'payload': {
                    'header': {},
                    'label': 'Payload',
                    'read_only': False,
                    'required': False,
                    'type': 'json',
                },
                'price': {
                    'header': {},
                    'inputmode': 'decimal',
                    'label': 'Price',
                    'precision': 12,
                    'read_only': False,
                    'required': False,
                    'scale': 2,
                    'type': 'decimal',
                },
                'rating': {
                    'header': {},
                    'inputmode': 'decimal',
                    'label': 'Rating',
                    'read_only': False,
                    'required': False,
                    'type': 'decimal',
                },
                'status': {
                    'choices': [
                        {
                            'tag_color': None,
                            'title': 'Pending translated',
                            'value': 'pending',
                        },
                        {
                            'tag_color': None,
                            'title': 'Done translated',
                            'value': 'done',
                        },
                    ],
                    'header': {},
                    'label': 'Status',
                    'read_only': False,
                    'required': False,
                    'size': 'default',
                    'type': 'choice',
                    'variant': 'elevated',
                },
                'title': {
                    'header': {},
                    'label': 'Title translated',
                    'max_length': 255,
                    'password': False,
                    'read_only': False,
                    'required': True,
                    'type': 'string',
                },
                'uuid': {
                    'header': {},
                    'label': 'Uuid',
                    'max_length': 32,
                    'password': False,
                    'read_only': False,
                    'required': False,
                    'type': 'string',
                },
            },
            'list_display': [
                'id',
                'title',
                'allowed_ips',
                'description',
                'status',
                'is_active',
                'count',
                'uuid',
                'price',
                'rating',
                'payload',
                'event_date',
                'event_time',
                'file',
                'image',
                'created_at',
            ],
        },
    },
    'title': 'Django examples translated',
    'type': 'table',
}

client = TestClient(admin_app)


@pytest.mark.asyncio
async def test_generate_category_schema_django(language_context):
    category = DjangoAdmin(
        model=DjangoExample,
        table_schema=DjangoFieldsSchema(model=DjangoExample)
    )
    new_schema = category.generate_category_schema(UserABC(username="test"), language_context)
    assert new_schema.model_dump() == FORM_SCHEMA_DATA, new_schema.model_dump()
