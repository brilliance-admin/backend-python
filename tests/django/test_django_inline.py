import pytest

from brilliance_admin.auth import UserABC
from brilliance_admin.integrations.django import DjangoAdmin, DjangoFieldsSchema, DjangoInlineField
from example.sections.django_models import (
    DjangoAnotherExample, DjangoAnotherExampleFactory, DjangoExample, DjangoExampleFactory, DjangoUserFactory)


class DjangoAnotherExampleInlineSchema(DjangoFieldsSchema):
    model = DjangoAnotherExample
    fields = ['id', 'title']


class DjangoExampleInlineAdmin(DjangoAdmin):
    model = DjangoExample
    table_schema = DjangoFieldsSchema(
        model=DjangoExample,
        fields=['id', 'owner', 'title', 'another_examples'],
        another_examples=DjangoInlineField(
            many=True,
            table_schema=DjangoAnotherExampleInlineSchema(),
        ),
    )


def get_category():
    return DjangoExampleInlineAdmin()


@pytest.mark.asyncio
async def test_inline_retrieve(language_context):
    category = get_category()
    user = UserABC(username='test')

    example = await DjangoExampleFactory()
    child_1 = await DjangoAnotherExampleFactory(example=example, title='child 1')
    child_2 = await DjangoAnotherExampleFactory(example=example, title='child 2')

    result = await category.retrieve(
        pk=example.id,
        user=user,
        language_context=language_context,
        debug=True,
    )

    assert result.data['another_examples'] == [
        {
            'id': child_1.id,
            'title': 'child 1',
        },
        {
            'id': child_2.id,
            'title': 'child 2',
        },
    ]


@pytest.mark.asyncio
async def test_inline_create(language_context):
    category = get_category()
    user = UserABC(username='test')
    owner = await DjangoUserFactory()

    result = await category.create(
        data={
            'owner': owner.id,
            'title': 'parent',
            'another_examples': [
                {'title': 'child 1'},
                {'title': 'child 2'},
            ],
        },
        user=user,
        language_context=language_context,
        debug=True,
    )

    created = await DjangoExample.objects.aget(pk=result.pk)
    children = [child async for child in created.another_examples.all().order_by('id')]

    assert [child.title for child in children] == ['child 1', 'child 2']


@pytest.mark.asyncio
async def test_inline_update(language_context):
    category = get_category()
    user = UserABC(username='test')

    example = await DjangoExampleFactory(title='parent')
    child = await DjangoAnotherExampleFactory(example=example, title='child 1')

    update_result = await category.update(
        pk=example.id,
        data={
            'title': 'parent updated',
            'another_examples': [
                {
                    'id': child.id,
                    'title': 'child updated',
                },
                {
                    'title': 'child 2',
                },
            ],
        },
        user=user,
        language_context=language_context,
        debug=True,
    )

    assert update_result.pk == example.id

    updated = await DjangoExample.objects.aget(pk=example.id)
    children = [child async for child in updated.another_examples.all().order_by('id')]

    assert [child.title for child in children] == ['child updated', 'child 2']
