from unittest import mock

import pytest

from brilliance_admin import schema, sqlalchemy
from brilliance_admin.auth import UserABC
from example.sections.models import Terminal

category_schema_data = {
    'graph_info': None,
    'icon': None,
    'description': None,
    'link': None,
    'categories': {},
    'table_info': {
        'actions': {
            'delete': {
                'allow_empty_selection': False,
                'base_color': 'red-lighten-2',
                'confirmation_text': 'Вы уверены, что хотите удалить данные записи?\n'
                'Данное действие нельзя отменить.',
                'description': None,
                'form_schema': None,
                'icon': None,
                'title': 'Удалить',
                'variant': 'outlined',
            },
        },
        'can_create': True,
        'can_retrieve': True,
        'can_update': True,
        'ordering_fields': [],
        'default_ordering': '-id',
        'pk_name': 'id',
        'search_enabled': True,
        'search_help': mock.ANY,
        'table_filters': None,
        'table_schema': {
            'fields': {
                'created_at': {
                    'header': {},
                    'label': 'Created At',
                    'read_only': False,
                    'required': False,
                    'type': 'datetime',
                    'range': True,
                    'include_date': True,
                    'include_time': True,
                },
                'currency_id': {
                    'dual_list': False,
                    'header': {},
                    'label': 'Currency',
                    'many': False,
                    'read_only': False,
                    'rel_name': 'currency',
                    'required': True,
                    'type': 'related',
                },
                'description': {
                    'header': {},
                    'label': 'Описание',
                    'max_length': 255,
                    'read_only': False,
                    'required': True,
                    'type': 'string',
                },
                'id': {
                    'header': {},
                    'label': 'ID',
                    'read_only': True,
                    'required': False,
                    'type': 'integer',
                },
                'is_h2h': {
                    'header': {},
                    'label': 'Is H2H',
                    'read_only': False,
                    'required': False,
                    'type': 'boolean',
                },
                'merchant_id': {
                    'dual_list': False,
                    'header': {},
                    'label': 'Merchant',
                    'many': False,
                    'read_only': False,
                    'rel_name': 'merchant',
                    'required': True,
                    'type': 'related',
                },
                'registered_delay': {
                    'header': {},
                    'label': 'Registered Delay',
                    'read_only': False,
                    'required': False,
                    'type': 'integer',
                },
                'secret_key': {
                    'header': {},
                    'label': 'Secret Key',
                    'max_length': 255,
                    'read_only': False,
                    'required': False,
                    'type': 'string',
                },
                'title': {
                    'header': {},
                    'label': 'Title',
                    'max_length': 255,
                    'read_only': False,
                    'required': True,
                    'type': 'string',
                },
                'status': {
                    'choices': [
                        {
                            'tag_color': 'grey-lighten-1',
                            'title': 'В процессе',
                            'value': 'process',
                        },
                        {
                            'tag_color': 'green-darken-1',
                            'title': 'Успех',
                            'value': 'success',
                        },
                        {
                            'tag_color': 'red-lighten-2',
                            'title': 'Ошибка',
                            'value': 'error',
                        },
                    ],
                    'header': {},
                    'label': 'Status',
                    'read_only': False,
                    'required': True,
                    'size': 'default',
                    'type': 'choice',
                    'variant': 'elevated',
                },
                'fee_id': {
                    'dual_list': False,
                    'header': {},
                    'label': 'Fee',
                    'many': False,
                    'read_only': False,
                    'rel_name': 'fee',
                    'required': False,
                    'type': 'related',
                },
                'manager_id': {
                    'header': {},
                    'label': 'Manager ID',
                    'read_only': False,
                    'required': True,
                    'type': 'integer',
                },
            },
            'list_display': [
                'id',
                'manager_id',
                'title',
                'fee_id',
                'status',
                'description',
                'secret_key',
                'currency_id',
                'merchant_id',
                'is_h2h',
                'registered_delay',
                'created_at',
            ],
        },
    },
    'title': 'Terminal',
    'type': 'table',
}

FIELDS = [
    'id',
    'manager_id',
    'title',
    'fee_id',
    'status',
    'description',
    'secret_key',
    'currency_id',
    'merchant_id',
    'is_h2h',
    'registered_delay',
    'created_at',
]


@pytest.mark.asyncio
async def test_generate_category_schema(sqlite_sessionmaker, language_context):
    category = sqlalchemy.SQLAlchemyAdmin(
        search_fields=['id'],
        model=Terminal,
        db_async_session=sqlite_sessionmaker,
        table_schema=sqlalchemy.SQLAlchemyFieldsSchema(
            model=Terminal,
            fields=FIELDS,
            created_at=schema.DateTimeField(range=True),
        ),
    )
    new_schema = category.generate_schema(UserABC(username="test"), language_context)
    assert new_schema.model_dump() == category_schema_data, new_schema.model_dump()
