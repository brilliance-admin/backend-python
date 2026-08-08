import pytest

from brilliance_admin.auth import UserABC
from brilliance_admin.integrations.django import DjangoAdmin, DjangoFieldsSchema
from brilliance_admin.schema.table.table_models import AutocompleteData
from example.sections.django_models import DjangoExample, DjangoUserFactory


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
