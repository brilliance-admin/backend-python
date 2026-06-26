from decimal import Decimal
from unittest import mock

import pytest

from brilliance_admin.translations import TranslateText as _
from brilliance_admin.auth import UserABC
from brilliance_admin.integrations.django import DjangoAdmin, DjangoFieldsSchema
from brilliance_admin.schema.table.admin_action import ActionData
from brilliance_admin import schema
from example.sections.django_models import DjangoExample


class DjangoExampleCategory(DjangoAdmin):
    model = DjangoExample
    table_schema = DjangoFieldsSchema(model=DjangoExample)


@pytest.mark.asyncio
async def test_create(language_context):
    category = DjangoExampleCategory()
    user = UserABC(username='test')

    result = await category.create(
        data={
            'title': 'test title',
            'description': 'test description',
            'is_active': False,
            'count': 5,
            'price': '12.34',
            'rating': '4.5',
            'payload': {'key': 'value'},
        },
        user=user,
        language_context=language_context,
        debug=True,
    )

    assert result.pk == 1

    record = await DjangoExample.objects.aget(pk=result.pk)

    assert record.title == 'test title'
    assert record.allowed_ips == []
    assert record.description == 'test description'
    assert record.is_active is False
    assert record.count == 5
    assert record.price == Decimal('12.34')
    assert record.rating == 4.5
    assert record.payload == {'key': 'value'}


@pytest.mark.asyncio
async def test_update(language_context):
    category = DjangoExampleCategory()
    user = UserABC(username='test')
    record = await DjangoExample.objects.acreate(
        title='before',
        description='before description',
        is_active=True,
        count=1,
        price=Decimal('1.00'),
        rating=1.0,
        payload={'before': True},
    )

    result = await category.update(
        pk=record.pk,
        data={
            'title': 'after',
            'description': 'after description',
            'is_active': False,
            'count': 7,
            'price': '77.70',
            'rating': '8.5',
            'payload': {'after': True},
        },
        user=user,
        language_context=language_context,
        debug=True,
    )

    assert result.pk == record.pk

    updated = await DjangoExample.objects.aget(pk=record.pk)

    assert updated.title == 'after'
    assert updated.allowed_ips == []
    assert updated.description == 'after description'
    assert updated.is_active is False
    assert updated.count == 7
    assert updated.price == Decimal('77.70')
    assert updated.rating == 8.5
    assert updated.payload == {'after': True}


@pytest.mark.asyncio
async def test_retrieve(language_context):
    category = DjangoExampleCategory()
    user = UserABC(username='test')
    record = await DjangoExample.objects.acreate(
        title='retrieve title',
        description='retrieve description',
        is_active=True,
        count=9,
        price=Decimal('9.99'),
        rating=2.5,
        payload={'retrieve': True},
    )

    result = await category.retrieve(
        pk=record.pk,
        user=user,
        language_context=language_context,
        debug=True,
    )

    assert result.data['id'] == record.pk
    assert result.data['title'] == 'retrieve title'
    assert result.data['allowed_ips'] == []
    assert result.data['description'] == 'retrieve description'
    assert result.data['is_active'] is True
    assert result.data['count'] == 9


@pytest.mark.asyncio
async def test_list(language_context):
    category = DjangoExampleCategory()
    user = UserABC(username='test')
    first = await DjangoExample.objects.acreate(title='first', description='a')
    second = await DjangoExample.objects.acreate(title='second', description='b')

    result = await category.get_list(
        list_data=schema.ListData(),
        user=user,
        language_context=language_context,
        debug=True,
    )

    assert result == schema.TableListResult(
        data=[
            {
                'id': second.pk,
                'title': 'second',
                'allowed_ips': [],
                'description': 'b',
                'status': {'value': 'pending', 'title': 'Pending translated'},
                'is_active': True,
                'count': 0,
                'uuid': second.uuid,
                'price': Decimal('0.00'),
                'rating': 0.0,
                'payload': {},
                'event_date': None,
                'event_time': None,
                'file': mock.ANY,
                'image': {'url': mock.ANY},
                'created_at': mock.ANY,
            },
            {
                'id': first.pk,
                'title': 'first',
                'allowed_ips': [],
                'description': 'a',
                'status': {'value': 'pending', 'title': 'Pending translated'},
                'is_active': True,
                'count': 0,
                'uuid': first.uuid,
                'price': Decimal('0.00'),
                'rating': 0.0,
                'payload': {},
                'event_date': None,
                'event_time': None,
                'file': mock.ANY,
                'image': {'url': mock.ANY},
                'created_at': mock.ANY,
            },
        ],
        total_count=2,
    )


@pytest.mark.asyncio
async def test_delete(language_context):
    category = DjangoExampleCategory()
    record = await DjangoExample.objects.acreate(title='delete me')

    result = await category.delete(
        action_data=ActionData(
            pks=[record.pk],
            send_to_all=False,
            form_data={},
            filters={},
            search=None,
        ),
    )

    assert result.message == _('deleted_successfully')
    assert await DjangoExample.objects.filter(pk=record.pk).aexists() is False
