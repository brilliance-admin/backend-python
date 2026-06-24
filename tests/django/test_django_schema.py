import pytest

from brilliance_admin.auth import UserABC
from brilliance_admin.integrations.django import DjangoFieldsSchema
from example.sections.django_models import DjangoExample

FORM_SCHEMA_DATA = {
    'fields': {
        'id': {
            'type': 'integer',
            'label': 'ID',
            'header': {},
            'read_only': True,
            'required': False,
        },
        'title': {
            'type': 'string',
            'label': 'Title',
            'header': {},
            'read_only': False,
            'required': True,
            'max_length': 255,
            'password': False,
        },
        'allowed_ips': {
            'type': 'array',
            'label': 'Allowed Ips',
            'header': {},
            'read_only': False,
            'required': False,
            'array_type': 'string',
        },
        'description': {
            'type': 'string',
            'label': 'Description',
            'header': {},
            'read_only': False,
            'required': False,
            'max_length': 255,
            'password': False,
        },
        'is_active': {
            'type': 'boolean',
            'label': 'Is Active',
            'header': {},
            'read_only': False,
            'required': False,
        },
        'count': {
            'type': 'integer',
            'label': 'Count',
            'header': {},
            'read_only': False,
            'required': False,
        },
        'uuid': {
            'type': 'string',
            'label': 'Uuid',
            'header': {},
            'read_only': False,
            'required': False,
            'max_length': 32,
            'password': False,
        },
        'price': {
            'type': 'decimal',
            'label': 'Price',
            'header': {},
            'read_only': False,
            'required': False,
            'inputmode': 'decimal',
            'precision': 12,
            'scale': 2,
        },
        'rating': {
            'type': 'decimal',
            'label': 'Rating',
            'header': {},
            'read_only': False,
            'required': False,
            'inputmode': 'decimal',
        },
        'payload': {
            'type': 'json',
            'label': 'Payload',
            'header': {},
            'read_only': False,
            'required': False,
        },
        'event_date': {
            'type': 'datetime',
            'label': 'Event Date',
            'header': {},
            'read_only': False,
            'required': False,
            'include_date': True,
            'include_time': False,
        },
        'event_time': {
            'type': 'datetime',
            'label': 'Event Time',
            'header': {},
            'read_only': False,
            'required': False,
            'include_date': False,
            'include_time': True,
        },
        'file': {
            'type': 'file',
            'label': 'File',
            'header': {},
            'read_only': False,
            'required': False,
        },
        'image': {
            'type': 'image',
            'label': 'Image',
            'header': {},
            'read_only': False,
            'required': False,
            'preview_max_height': 100,
            'preview_max_width': 100,
        },
        'created_at': {
            'type': 'datetime',
            'label': 'Created At',
            'header': {},
            'read_only': True,
            'required': False,
            'include_date': True,
            'include_time': True,
        },
    },
    'list_display': [
        'id',
        'title',
        'allowed_ips',
        'description',
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
}


@pytest.mark.asyncio
async def test_generate_form_schema_django(language_context):
    fields_schema = DjangoFieldsSchema(model=DjangoExample)

    result = fields_schema.generate_form_schema(
        UserABC(username='test'),
        language_context,
    )

    assert result.model_dump() == FORM_SCHEMA_DATA
