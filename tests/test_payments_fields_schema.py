from unittest import mock

import pytest

from brilliance_admin.auth import UserABC
from example.sections.payments import PaymentsAdmin

category_schema_data = {
    'graph_info': None,
    'icon': 'mdi-credit-card-outline',
    'description': 'Статичные данные',
    'link': None,
    'categories': {},
    'table_info': {
        'actions': {
            'action_with_exception': {
                'allow_empty_selection': True,
                'base_color': None,
                'confirmation_text': None,
                'description': None,
                'form_schema': None,
                'icon': None,
                'title': 'Действие с ошибкой',
                'variant': None,
            },
            'create_payment': {
                'allow_empty_selection': True,
                'base_color': None,
                'confirmation_text': None,
                'description': 'Создать платеж и отправить его на обработку в платежную '
                'систему.',
                'form_schema': {
                    'fields': {
                        'amount': {
                            'header': {},
                            'label': 'Сумма',
                            'read_only': False,
                            'required': False,
                            'type': 'integer',
                        },
                        'is_throw_error': {
                            'header': {},
                            'label': 'Выбросить ошибку?',
                            'read_only': False,
                            'required': False,
                            'type': 'boolean',
                        },
                    },
                    'list_display': [
                        'amount',
                        'is_throw_error',
                    ],
                },
                'icon': None,
                'title': 'Создать платеж',
                'variant': None,
            },
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
        'can_create': False,
        'can_retrieve': True,
        'can_update': False,
        'ordering_fields': [
            'id',
        ],
        'default_ordering': None,
        'pk_name': 'id',
        'search_enabled': True,
        'search_help': mock.ANY,
        'table_filters': {
            'fields': {
                'created_at': {
                    'header': {},
                    'label': 'Время создания',
                    'range': True,
                    'read_only': False,
                    'required': False,
                    'type': 'datetime',
                    'include_date': True,
                    'include_time': True,
                },
                'id': {
                    'header': {},
                    'label': 'ID',
                    'read_only': False,
                    'required': False,
                    'type': 'integer',
                },
            },
            'list_display': [
                'id',
                'created_at',
            ],
        },
        'table_schema': {
            'fields': {
                'amount': {
                    'header': {},
                    'label': 'Сумма',
                    'read_only': True,
                    'required': False,
                    'type': 'integer',
                },
                'created_at': {
                    'header': {},
                    'label': 'Время создания',
                    'read_only': True,
                    'required': False,
                    'type': 'datetime',
                    'include_date': True,
                    'include_time': True,
                },
                'description': {
                    'header': {},
                    'label': 'Описание',
                    'read_only': False,
                    'required': False,
                    'type': 'string',
                },
                'endpoint': {
                    'header': {},
                    'label': 'Эндпоинт',
                    'read_only': False,
                    'required': False,
                    'type': 'string',
                },
                'get_provider_registry': {
                    'header': {},
                    'label': 'Реестр проверен',
                    'read_only': True,
                    'required': False,
                    'type': 'boolean',
                },
                'get_provider_registry_info': {
                    'header': {},
                    'label': 'Информация по реестру провайдера',
                    'read_only': True,
                    'required': False,
                    'type': 'boolean',
                },
                'id': {
                    'header': {},
                    'label': 'ID',
                    'read_only': True,
                    'required': False,
                    'type': 'integer',
                },
                'other_field': {
                    'header': {},
                    'label': 'Other Field',
                    'read_only': True,
                    'required': False,
                    'type': 'string',
                },
                'whitelist_ips': {
                    'header': {},
                    'label': 'Белый список IP',
                    'read_only': False,
                    'required': False,
                    'type': 'array',
                },
            },
            'list_display': [
                'id',
                'amount',
                'endpoint',
                'description',
                'created_at',
                'get_provider_registry',
                'get_provider_registry_info',
            ],
        },
    },
    'title': 'Платежи',
    'type': 'table',
 }


@pytest.mark.asyncio
async def test_generate_category_schema(language_context):
    category = PaymentsAdmin()
    new_schema = category.generate_schema(UserABC(username="test"), language_context)
    assert new_schema.model_dump() == category_schema_data, new_schema.model_dump()
