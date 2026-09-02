import pytest

from brilliance_admin import schema
from brilliance_admin.auth import UserABC
from brilliance_admin.exceptions import AdminAPIException
from brilliance_admin.integrations.django import DjangoAdmin, DjangoFieldsSchema
from example.sections.django_models import (
    DjangoAnotherExample,
    DjangoAnotherExampleFactory,
    DjangoExample,
    DjangoExampleFactory,
)


class DjangoExampleAdmin(DjangoAdmin):
    model = DjangoExample
    table_schema = DjangoFieldsSchema(
        model=DjangoExample,
        fields=['id', 'title'],
    )


class DjangoAnotherExampleAdmin(DjangoAdmin):
    model = DjangoAnotherExample
    table_schema = DjangoFieldsSchema(
        model=DjangoAnotherExample,
        fields=['id', 'title', 'example'],
        formset=schema.FormSet(
            fields=[
                schema.FormSet(
                    fields=[
                        'id',
                        'title',
                        'example',
                    ],
                ),
            ],
        ),
    )

    def get_queryset(self, *args, **kwargs):
        return super().get_queryset(*args, **kwargs).select_related('example', 'example__owner')


def get_example_another_subcategory():
    example_category = DjangoExampleAdmin(
        subcategories=[
            DjangoAnotherExampleAdmin(),
        ],
    )
    another_subcategory = example_category.get_subcategory('djangoanotherexample')
    assert another_subcategory
    return example_category, another_subcategory


@pytest.mark.asyncio
async def test_subcategory_list(language_context):
    example_category, another_subcategory = get_example_another_subcategory()
    user = UserABC(username='test')

    example_1 = await DjangoExampleFactory()
    example_2 = await DjangoExampleFactory()

    another_1 = await DjangoAnotherExampleFactory(example=example_1)
    another_2 = await DjangoAnotherExampleFactory(example=example_1)
    await DjangoAnotherExampleFactory(example=example_2)
    await DjangoAnotherExampleFactory(example=example_2)

    list_result = await another_subcategory.get_list(
        schema.ListData(page=1, limit=25),
        user,
        language_context,
        debug=True,
        parent_category=example_category,
        parent_pk=example_1.id,
    )

    assert [row['id'] for row in list_result.data] == [another_2.id, another_1.id]


@pytest.mark.asyncio
async def test_subcategory_retrieve(language_context):
    example_category, another_subcategory = get_example_another_subcategory()
    user = UserABC(username='test')

    example_1 = await DjangoExampleFactory()
    another_1 = await DjangoAnotherExampleFactory(example=example_1)

    example_2 = await DjangoExampleFactory()
    another_2 = await DjangoAnotherExampleFactory(example=example_2)

    retrieve_result = await another_subcategory.retrieve(
        pk=another_1.id,
        user=user,
        language_context=language_context,
        debug=True,
        parent_category=example_category,
        parent_pk=example_1.id,
    )

    assert retrieve_result.data['id'] == another_1.id
    assert retrieve_result.data['title'] == another_1.title

    with pytest.raises(AdminAPIException) as exc_info:
        await another_subcategory.retrieve(
            pk=another_2.id,
            user=user,
            language_context=language_context,
            debug=True,
            parent_category=example_category,
            parent_pk=example_1.id,
        )

    assert exc_info.value.get_error().code == 'record_not_found'


@pytest.mark.asyncio
async def test_subcategory_create(language_context):
    example_category, another_subcategory = get_example_another_subcategory()
    user = UserABC(username='test')

    example = await DjangoExampleFactory()

    create_result = await another_subcategory.create(
        data={
            'title': 'created child',
        },
        user=user,
        language_context=language_context,
        debug=True,
        parent_category=example_category,
        parent_pk=example.id,
    )

    child = await DjangoAnotherExample.objects.aget(pk=create_result.pk)

    assert child.title == 'created child'
    assert child.example_id == example.id


@pytest.mark.asyncio
async def test_subcategory_update(language_context):
    example_category, another_subcategory = get_example_another_subcategory()
    user = UserABC(username='test')

    example_1 = await DjangoExampleFactory()
    another_1 = await DjangoAnotherExampleFactory(example=example_1)

    example_2 = await DjangoExampleFactory()
    another_2 = await DjangoAnotherExampleFactory(example=example_2)

    update_result = await another_subcategory.update(
        pk=another_1.id,
        data={
            'title': 'updated child',
        },
        user=user,
        language_context=language_context,
        debug=True,
        parent_category=example_category,
        parent_pk=example_1.id,
    )

    assert update_result.pk == another_1.id

    updated = await DjangoAnotherExample.objects.aget(pk=another_1.id)
    assert updated.title == 'updated child'
    assert updated.example_id == example_1.id

    with pytest.raises(AdminAPIException) as exc_info:
        await another_subcategory.update(
            pk=another_2.id,
            data={'title': 'must fail'},
            user=user,
            language_context=language_context,
            debug=True,
            parent_category=example_category,
            parent_pk=example_1.id,
        )

    assert exc_info.value.get_error().code == 'record_not_found'


def test_subcategory_schema_removes_reverse_fk(language_context):
    example_category, another_subcategory = get_example_another_subcategory()
    user = UserABC(username='test')
    admin_schema = schema.AdminSchema(
        categories=[schema.CategoryGroup(slug='examples', title='Examples', subcategories=[example_category])],
        auth=None,
        language_manager=language_context.language_manager,
    )

    example_schema = example_category.generate_category_schema(user, language_context, admin_schema)
    subcategories = example_schema.table_info.subcategories
    subcategory_schema = (
        subcategories['djangonotherexample']
        if 'djangonotherexample' in subcategories
        else subcategories['djangoanotherexample']
    )
    subcategory_fields = subcategory_schema['table_info']['table_schema']['fields']
    subcategory_formset_fields = another_subcategory.table_schema._collect_formset_fields(
        subcategory_schema['table_info']['table_schema']['formset']
    )

    assert 'example' not in subcategory_fields
    assert 'example' not in subcategory_formset_fields

    direct_subcategory_schema = another_subcategory.generate_category_schema(
        user,
        language_context,
        admin_schema,
    )
    direct_subcategory_fields = direct_subcategory_schema.table_info.table_schema.fields
    direct_formset_fields = another_subcategory.table_schema._collect_formset_fields(
        direct_subcategory_schema.table_info.table_schema.formset
    )

    assert 'example' in direct_subcategory_fields
    assert 'example' in direct_formset_fields

    group_schema = schema.CategoryGroup(
        slug='examples',
        title='Examples',
        subcategories=[example_category],
    ).generate_category_schema(user, language_context, admin_schema)

    assert 'djangoexample' in group_schema.categories
