from datetime import datetime, timezone

import pytest

from brilliance_admin import schema
from brilliance_admin.auth import UserABC
from brilliance_admin.integrations.django import DjangoAdmin, DjangoFieldsSchema
from example.sections.django_models import (
    DjangoAnotherExample,
    DjangoAnotherExampleFactory,
    DjangoExample,
    DjangoExampleFactory,
    DjangoUser,
)


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

    example_1 = await DjangoExampleFactory(title='Test terminal')
    example_2 = await DjangoExampleFactory(title='Test terminal second')

    await DjangoExampleFactory(title='Other')

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

    example_old = await DjangoExampleFactory()
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

    example_1 = await DjangoExampleFactory(title='Test terminal')
    example_2 = await DjangoExampleFactory(title='Test terminal second')

    await DjangoExampleFactory(title='Other')
    await DjangoExampleFactory(title='Nothing')

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
async def test_list_search_related_field(language_context):
    category = DjangoAdmin(
        search_fields=['owner__username'],
        model=DjangoExample,
        table_schema=DjangoFieldsSchema(
            model=DjangoExample,
            fields=['id'],
        ),
    )
    user = UserABC(username='test')

    owner = await DjangoUser.objects.acreate(username='john_search')
    example = await DjangoExampleFactory(owner=owner)
    await DjangoExampleFactory()

    list_result = await category.get_list(
        list_data=schema.ListData(search='john_search'),
        user=user,
        language_context=language_context,
        debug=False,
    )
    assert list_result == schema.TableListResult(
        data=[{'id': example.id}],
        total_count=1,
    )


@pytest.mark.asyncio
async def test_list_search_reverse_related_id(language_context):
    category = DjangoAdmin(
        search_fields=['another_examples__id'],
        model=DjangoExample,
        table_schema=DjangoFieldsSchema(
            model=DjangoExample,
            fields=['id'],
        ),
    )
    user = UserABC(username='test')

    example = await DjangoExampleFactory()
    another = await DjangoAnotherExampleFactory(example=example)
    await DjangoExampleFactory()

    list_result = await category.get_list(
        list_data=schema.ListData(search=str(another.id)),
        user=user,
        language_context=language_context,
        debug=False,
    )
    assert list_result == schema.TableListResult(
        data=[{'id': example.id}],
        total_count=1,
    )


@pytest.mark.asyncio
async def test_list_search_json_field(language_context):
    category = DjangoAdmin(
        search_fields=['payload__phone'],
        model=DjangoExample,
        table_schema=DjangoFieldsSchema(
            model=DjangoExample,
            fields=['id'],
        ),
    )
    user = UserABC(username='test')

    example = await DjangoExampleFactory(payload={'phone': '79990001122'})
    await DjangoExampleFactory(payload={'phone': '70000000000'})

    list_result = await category.get_list(
        list_data=schema.ListData(search='79990001122'),
        user=user,
        language_context=language_context,
        debug=False,
    )
    assert list_result == schema.TableListResult(
        data=[{'id': example.id}],
        total_count=1,
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

    example_1 = await DjangoExampleFactory(title='one')
    another_1 = await DjangoAnotherExampleFactory(example=example_1)

    example_2 = await DjangoExampleFactory()
    another_2 = await DjangoAnotherExampleFactory(example=example_2)

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

    example_1 = await DjangoExampleFactory()
    example_2 = await DjangoExampleFactory()

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
