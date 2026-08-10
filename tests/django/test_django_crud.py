from decimal import Decimal
from datetime import time
from unittest import mock

import pytest
from django.db import connection, models

from brilliance_admin import schema
from brilliance_admin.auth import UserABC
from brilliance_admin.integrations.django import DjangoAdmin, DjangoFieldsSchema
from brilliance_admin.schema.table.admin_action import ActionData
from brilliance_admin.translations import TranslateText as _
from example.sections.django_models import DjangoExample, DjangoExampleFactory, DjangoUserFactory


class DjangoExampleCategory(DjangoAdmin):
    model = DjangoExample

    def get_queryset(self):
        return super().get_queryset().select_related('owner')


class DjangoExampleCompactCategory(DjangoAdmin):
    model = DjangoExample
    table_schema = DjangoFieldsSchema(
        model=DjangoExample,
        list_display=['id', 'owner', 'title'],
    )

    def get_queryset(self):
        return super().get_queryset().select_related('owner')


class CallableDefaultTarget(models.Model):
    name = models.CharField(max_length=255)

    class Meta:
        app_label = 'sections'
        db_table = 'test_callable_default_target'


def default_callable_target():
    targets = CallableDefaultTarget.objects.filter(name='default').only('id')
    if targets.exists():
        return targets.first().id
    return CallableDefaultTarget.objects.create(name='default').id


class CallableDefaultOwner(models.Model):
    title = models.CharField(max_length=255)
    target = models.ForeignKey(
        CallableDefaultTarget,
        models.PROTECT,
        related_name='owners',
        default=default_callable_target,
    )

    class Meta:
        app_label = 'sections'
        db_table = 'test_callable_default_owner'


class CallableDefaultOwnerAdmin(DjangoAdmin):
    model = CallableDefaultOwner


@pytest.fixture
def callable_default_schema():
    with connection.schema_editor() as schema_editor:
        schema_editor.create_model(CallableDefaultTarget)
        schema_editor.create_model(CallableDefaultOwner)

    yield

    with connection.schema_editor() as schema_editor:
        schema_editor.delete_model(CallableDefaultOwner)
        schema_editor.delete_model(CallableDefaultTarget)


@pytest.mark.asyncio
async def test_create(language_context):
    category = DjangoExampleCategory()
    user = UserABC(username='test')
    user_django = await DjangoUserFactory()

    result = await category.create(
        data={
            'owner': user_django.pk,
            'title': 'test title',
            'description': 'test description',
            'is_active': False,
            'count': 5,
            'price': '12.34',
            'rating': '4.5',
            'payload': {'key': 'value'},
            'timezone': 'Europe/Moscow',
        },
        user=user,
        language_context=language_context,
        debug=True,
    )

    assert result.pk == 1

    record = await DjangoExample.objects.aget(pk=result.pk)

    assert record.owner_id == user_django.pk
    assert record.title == 'test title'
    assert record.allowed_ips == []
    assert record.description == 'test description'
    assert record.is_active is False
    assert record.count == 5
    assert record.price == Decimal('12.34')
    assert record.rating == 4.5
    assert record.payload == {'key': 'value'}
    assert str(record.timezone) == 'Europe/Moscow'


@pytest.mark.asyncio
async def test_create_with_callable_fk_default(callable_default_schema, language_context):
    category = CallableDefaultOwnerAdmin()
    user = UserABC(username='test')

    result = await category.create(
        data={
            'title': 'created with default',
        },
        user=user,
        language_context=language_context,
        debug=True,
    )

    record = await CallableDefaultOwner.objects.aget(pk=result.pk)
    assert record.title == 'created with default'
    assert record.target_id is not None


@pytest.mark.asyncio
async def test_update(language_context):
    category = DjangoExampleCategory()
    user = UserABC(username='test')
    record = await DjangoExampleFactory(
        title='before',
        description='before description',
        is_active=True,
        count=1,
        price=Decimal('1.00'),
        rating=1.0,
        payload={'before': True},
    )
    new_owner = await DjangoUserFactory()
    result = await category.update(
        pk=record.pk,
        data={
            'owner': new_owner.pk,
            'title': 'after',
            'description': 'after description',
            'is_active': False,
            'count': 7,
            'price': '77.70',
            'rating': '8.5',
            'payload': {'after': True},
            'event_time': '12:00',
            'timezone': 'Asia/Tokyo',
        },
        user=user,
        language_context=language_context,
        debug=True,
    )

    assert result.pk == record.pk

    updated = await DjangoExample.objects.aget(pk=record.pk)

    assert updated.title == 'after'
    assert updated.owner_id == new_owner.pk
    assert updated.allowed_ips == []
    assert updated.description == 'after description'
    assert updated.is_active is False
    assert updated.count == 7
    assert updated.price == Decimal('77.70')
    assert updated.rating == 8.5
    assert updated.payload == {'after': True}
    assert updated.event_time == time(12, 0)
    assert str(updated.timezone) == 'Asia/Tokyo'


@pytest.mark.asyncio
async def test_retrieve(language_context):
    category = DjangoExampleCategory()
    user = UserABC(username='test')
    record = await DjangoExampleFactory(
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
    assert result.data['owner'] == {'key': record.owner_id, 'title': str(record.owner)}
    assert result.data['title'] == 'retrieve title'
    assert result.data['description'] == 'retrieve description'


@pytest.mark.asyncio
async def test_list(language_context):
    category = DjangoExampleCategory()
    user = UserABC(username='test')

    first = await DjangoExampleFactory(title='first')
    second = await DjangoExampleFactory(title='second')

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
                'owner': {'key': second.owner.pk, 'title': mock.ANY},
                'title': second.title,
                'allowed_ips': [],
                'description': second.description,
                'status': {'value': 'pending', 'title': 'Pending translated'},
                'is_active': True,
                'count': 0,
                'uuid': second.uuid,
                'price': Decimal('0.00'),
                'rating': 0.0,
                'payload': {},
                'event_date': None,
                'event_time': None,
                'timezone': {'value': 'UTC', 'title': 'UTC'},
                'ttl': None,
                'file': mock.ANY,
                'image': {'url': mock.ANY},
                'created_at': mock.ANY,
            },
            {
                'id': first.pk,
                'owner': {'key': first.owner.pk, 'title': mock.ANY},
                'title': first.title,
                'allowed_ips': [],
                'description': first.description,
                'status': {'value': 'pending', 'title': 'Pending translated'},
                'is_active': True,
                'count': 0,
                'uuid': first.uuid,
                'price': Decimal('0.00'),
                'rating': 0.0,
                'payload': {},
                'event_date': None,
                'event_time': None,
                'timezone': {'value': 'UTC', 'title': 'UTC'},
                'ttl': None,
                'file': mock.ANY,
                'image': {'url': mock.ANY},
                'created_at': mock.ANY,
            },
        ],
        total_count=2,
        debug_info={'db_query_count': 2},
    )


@pytest.mark.asyncio
async def test_delete(language_context):
    category = DjangoExampleCategory()
    record = await DjangoExampleFactory(title='delete me')

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


@pytest.mark.asyncio
async def test_list_uses_list_display_fields_only(language_context):
    category = DjangoExampleCompactCategory()
    user = UserABC(username='test')

    first = await DjangoExampleFactory(title='first', description='first description')
    second = await DjangoExampleFactory(title='second', description='second description')

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
                'owner': {'key': second.owner.pk, 'title': mock.ANY},
                'title': second.title,
            },
            {
                'id': first.pk,
                'owner': {'key': first.owner.pk, 'title': mock.ANY},
                'title': first.title,
            },
        ],
        total_count=2,
        debug_info={'db_query_count': 2},
    )

    queryset = category.optimize_list_queryset(category.get_queryset())
    record = await queryset.aget(pk=first.pk)
    deferred_fields = record.get_deferred_fields()

    assert 'description' in deferred_fields
    assert 'payload' in deferred_fields
