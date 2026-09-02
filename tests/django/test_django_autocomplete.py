import pytest

from brilliance_admin.auth import UserABC
from brilliance_admin.exceptions import APIError, AdminAPIException
from brilliance_admin.integrations.django import DjangoAdmin, DjangoFieldsSchema, DjangoRelatedField
from brilliance_admin.schema.table.table_models import AutocompleteData
from example.sections.django_models import DjangoAnotherExample, DjangoExample, DjangoExampleFactory, DjangoUserFactory


async def get_examples_queryset(queryset, data, user):
    return queryset.select_related('owner')


@pytest.mark.asyncio
async def test_django_related_autocomplete(language_context):
    category = DjangoAdmin(
        model=DjangoExample,
        table_schema=DjangoFieldsSchema(
            model=DjangoExample,
            fields=['owner'],
        ),
    )
    user = UserABC(username='test')

    owner_1 = await DjangoUserFactory(username='active_owner')
    await DjangoUserFactory(username='other_owner')

    result = await category.autocomplete(
        data=AutocompleteData(
            search_string='active',
            field_slug='owner',
            is_filter=False,
            form_data={},
            existed_choices=[],
            limit=30,
        ),
        user=user,
        language_context=language_context,
        debug=True,
    )

    assert result.model_dump() == {
        'results': [
            {
                'key': owner_1.pk,
                'title': str(owner_1),
            },
        ],
        'total_count': 2,
    }


@pytest.mark.asyncio
async def test_django_related_autocomplete_keeps_existing_choices_and_other_results(language_context):
    category = DjangoAdmin(
        model=DjangoExample,
        table_schema=DjangoFieldsSchema(
            model=DjangoExample,
            fields=['owner'],
        ),
    )
    user = UserABC(username='test')

    owner_1 = await DjangoUserFactory(username='first_owner')
    owner_2 = await DjangoUserFactory(username='second_owner')

    result = await category.autocomplete(
        data=AutocompleteData(
            search_string='second',
            field_slug='owner',
            is_filter=False,
            form_data={},
            existed_choices=[{'key': owner_1.pk, 'title': str(owner_1)}],
            limit=30,
        ),
        user=user,
        language_context=language_context,
        debug=True,
    )

    assert result.model_dump() == {
        'results': [
            {'key': owner_1.pk, 'title': str(owner_1)},
            {'key': owner_2.pk, 'title': str(owner_2)},
        ],
        'total_count': 2,
    }


@pytest.mark.asyncio
async def test_django_related_autocomplete_title_error_shows_field(language_context):
    category = DjangoAdmin(
        model=DjangoAnotherExample,
        raise_async_unsafe=True,
        table_schema=DjangoFieldsSchema(
            model=DjangoAnotherExample,
            fields=['example'],
        ),
    )
    user = UserABC(username='test')
    await DjangoExampleFactory(title='title match')

    with pytest.raises(AdminAPIException) as exc:
        await category.autocomplete(
            data=AutocompleteData(
                search_string='title',
                field_slug='example',
                is_filter=False,
                form_data={},
                existed_choices=[],
                limit=30,
            ),
            user=user,
            language_context=language_context,
            debug=True,
        )

    assert exc.value.error == APIError(
        message=(
            'Async unsafe title load: field="example" rel_name="example" '
            'parent_model="None" parent_pk=None '
            'model="DjangoExample" pk=1. '
            'SynchronousOnlyOperation: Add required select_related to get_queryset method, or define async admin_title().'
            '\n__str__ source:\n'
            '    def __str__(self):\n'
            "        return f'#{self.pk} {self.title} (owner: {self.owner.username})'\n"
        ),
        code='async_unsafe_title_load',
    )


@pytest.mark.asyncio
async def test_django_related_autocomplete_uses_select_related(language_context):
    category = DjangoAdmin(
        model=DjangoAnotherExample,
        table_schema=DjangoFieldsSchema(
            model=DjangoAnotherExample,
            fields=['example'],
            example=DjangoRelatedField(select_related=['owner']),
        ),
    )
    user = UserABC(username='test')
    example = await DjangoExampleFactory(title='title match')

    result = await category.autocomplete(
        data=AutocompleteData(
            search_string='title',
            field_slug='example',
            is_filter=False,
            form_data={},
            existed_choices=[],
            limit=30,
        ),
        user=user,
        language_context=language_context,
        debug=True,
    )

    assert result.model_dump() == {
        'results': [
            {
                'key': example.pk,
                'title': str(example),
            },
        ],
        'total_count': 1,
    }


@pytest.mark.asyncio
async def test_django_related_autocomplete_uses_get_queryset(language_context):
    category = DjangoAdmin(
        model=DjangoAnotherExample,
        table_schema=DjangoFieldsSchema(
            model=DjangoAnotherExample,
            fields=['example'],
            example=DjangoRelatedField(get_queryset=get_examples_queryset),
        ),
    )
    user = UserABC(username='test')
    example = await DjangoExampleFactory(title='title match')

    result = await category.autocomplete(
        data=AutocompleteData(
            search_string='title',
            field_slug='example',
            is_filter=False,
            form_data={},
            existed_choices=[],
            limit=30,
        ),
        user=user,
        language_context=language_context,
        debug=True,
    )

    assert result.model_dump() == {
        'results': [
            {
                'key': example.pk,
                'title': str(example),
            },
        ],
        'total_count': 1,
    }
