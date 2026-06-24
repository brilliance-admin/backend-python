from datetime import datetime, timezone

import pytest

from brilliance_admin import schema
from brilliance_admin.auth import UserABC
from brilliance_admin.integrations.django import DjangoAdmin, DjangoFieldsSchema
from example.sections.django_models import DjangoAnotherExample, DjangoExample


@pytest.mark.asyncio
async def test_list_filter(language_context):
    category = DjangoAdmin(
        model=DjangoExample,
        table_schema=DjangoFieldsSchema(
            model=DjangoExample,
            fields=['id'],
        ),
        table_filters=DjangoFieldsSchema(
            model=DjangoExample,
            fields=['id', 'title', 'created_at'],
            created_at=schema.DateTimeField(range=True),
        ),
    )
    user = UserABC(username='test')

    example_1 = await DjangoExample.objects.acreate(title='Test terminal', description='a')
    example_2 = await DjangoExample.objects.acreate(title='Test terminal second', description='b')
    await DjangoExample.objects.acreate(title='other', description='c')

    list_result = await category.get_list(
        list_data=schema.ListData(filters={'id': example_1.id}),
        user=user,
        language_context=language_context,
        debug=False,
    )
    assert list_result == schema.TableListResult(data=[{'id': example_1.id}], total_count=1)

    list_result = await category.get_list(
        list_data=schema.ListData(filters={'title': 'Test terminal second'}),
        user=user,
        language_context=language_context,
        debug=False,
    )
    assert list_result == schema.TableListResult(data=[{'id': example_2.id}], total_count=1)

    list_result = await category.get_list(
        list_data=schema.ListData(filters={'title': 'Test%'}),
        user=user,
        language_context=language_context,
        debug=False,
    )
    assert list_result == schema.TableListResult(
        data=[{'id': example_2.id}, {'id': example_1.id}],
        total_count=2,
    )

    example_old = await DjangoExample.objects.acreate(title='Old terminal', description='old')
    await DjangoExample.objects.filter(pk=example_old.pk).aupdate(
        created_at=datetime(2023, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    )

    list_result = await category.get_list(
        list_data=schema.ListData(filters={
            'created_at': {
                'from': '2022-12-04T18:55:00+00:00',
                'to': '2023-12-17T18:55:00+00:00',
            }
        }),
        user=user,
        language_context=language_context,
        debug=False,
    )
    assert list_result == schema.TableListResult(data=[{'id': example_old.id}], total_count=1)


@pytest.mark.asyncio
async def test_list_search(language_context):
    category = DjangoAdmin(
        search_fields=['title'],
        model=DjangoExample,
        table_schema=DjangoFieldsSchema(
            model=DjangoExample,
            fields=['id'],
        ),
    )
    user = UserABC(username='test')

    example_1 = await DjangoExample.objects.acreate(title='Test terminal', description='a')
    example_2 = await DjangoExample.objects.acreate(title='Test terminal second', description='b')
    await DjangoExample.objects.acreate(title='other', description='c')
    await DjangoExample.objects.acreate(title='other second', description='d')

    list_result = await category.get_list(
        list_data=schema.ListData(search='Test%'),
        user=user,
        language_context=language_context,
        debug=False,
    )
    assert list_result == schema.TableListResult(
        data=[{'id': example_2.id}, {'id': example_1.id}],
        total_count=2,
    )


@pytest.mark.asyncio
async def test_filter_related_many(language_context):
    category = DjangoAdmin(
        model=DjangoAnotherExample,
        table_schema=DjangoFieldsSchema(
            model=DjangoAnotherExample,
            fields=['id'],
        ),
        table_filters=DjangoFieldsSchema(
            model=DjangoAnotherExample,
            fields=['example'],
        ),
    )
    user = UserABC(username='test')

    example_1 = await DjangoExample.objects.acreate(title='one')
    another_1 = await DjangoAnotherExample.objects.acreate(example=example_1, title='a1')

    example_2 = await DjangoExample.objects.acreate(title='two')
    another_2 = await DjangoAnotherExample.objects.acreate(example=example_2, title='a2')

    list_result = await category.get_list(
        list_data=schema.ListData(filters={
            'example': {'key': example_2.id, 'title': 'test'}
        }),
        user=user,
        language_context=language_context,
        debug=False,
    )
    assert list_result == schema.TableListResult(data=[{'id': another_2.id}], total_count=1)


@pytest.mark.asyncio
async def test_list_bad_search_field():
    with pytest.raises(AttributeError) as e:
        DjangoAdmin(
            search_fields=['no_field'],
            model=DjangoExample,
        )

    assert str(e.value) == 'DjangoAdmin: search field "no_field" not found in model DjangoExample'


@pytest.mark.asyncio
async def test_ordering(language_context):
    category = DjangoAdmin(
        model=DjangoExample,
        ordering_fields=['id'],
        table_schema=DjangoFieldsSchema(
            model=DjangoExample,
            fields=['id'],
        ),
    )
    user = UserABC(username='test')

    example_1 = await DjangoExample.objects.acreate(title='one')
    example_2 = await DjangoExample.objects.acreate(title='two')

    list_result = await category.get_list(
        list_data=schema.ListData(ordering='id'),
        user=user,
        language_context=language_context,
        debug=False,
    )
    assert list_result == schema.TableListResult(
        data=[{'id': example_1.id}, {'id': example_2.id}],
        total_count=2,
    )

    list_result = await category.get_list(
        list_data=schema.ListData(ordering='-id'),
        user=user,
        language_context=language_context,
        debug=False,
    )
    assert list_result == schema.TableListResult(
        data=[{'id': example_2.id}, {'id': example_1.id}],
        total_count=2,
    )
