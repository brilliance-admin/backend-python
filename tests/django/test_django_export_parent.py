import csv
from io import StringIO

import pytest
from django.core.files.storage import default_storage

from brilliance_admin import schema
from brilliance_admin.auth import UserABC
from brilliance_admin.integrations.django import DjangoFieldsSchema
from brilliance_admin.integrations.django.table import DjangoAdmin
from brilliance_admin.integrations.django.table.export import DjangoPostgresExportAction
from brilliance_admin.schema.table.admin_action import ActionData
from example.sections.django_models import (
    DjangoAnotherExample,
    DjangoAnotherExampleFactory,
    DjangoExample,
    DjangoExampleFactory,
)


class ExportChildCategory(DjangoPostgresExportAction, DjangoAdmin):
    model = DjangoAnotherExample
    slug = 'children'
    export_fields = ['id', 'title']
    table_schema = DjangoFieldsSchema(
        model=DjangoAnotherExample,
        fields=['id', 'title', 'example'],
    )


class ExportParentCategory(DjangoAdmin):
    model = DjangoExample
    slug = 'parents'
    table_schema = DjangoFieldsSchema(
        model=DjangoExample,
        fields=['id', 'title'],
    )
    subcategories = [ExportChildCategory()]


EXPORT_SCHEMA = schema.AdminSchema(
    categories=[
        schema.CategoryGroup(
            slug='group',
            subcategories=[ExportParentCategory()],
        ),
    ],
    auth=None,
)


@pytest.mark.asyncio
async def test_export_parent(monkeypatch, language_context):
    monkeypatch.setattr(
        'brilliance_admin.integrations.django.table.export.executer._get_admin_schema',
        lambda: EXPORT_SCHEMA,
    )
    parent_category = EXPORT_SCHEMA.get_group('group').get_category('parents')
    child_category = parent_category.get_subcategory('children')

    parent = await DjangoExampleFactory()
    other_parent = await DjangoExampleFactory()
    own = await DjangoAnotherExampleFactory(example=parent, title='own')
    await DjangoAnotherExampleFactory(example=other_parent, title='other')

    result = await child_category._perform_action(
        request=None,
        action='django_export',
        action_data=ActionData(
            group_slug='group',
            category_slug='parents',
            subcategory_slug='children',
            send_to_all=True,
            form_data={
                'is_async': False,
                'email': None,
                'export_fields': ['id', 'title'],
            },
        ),
        language_context=language_context,
        user=UserABC(username='test'),
        debug=True,
        parent_category=parent_category,
        parent_pk=parent.pk,
    )

    assert result.download_file is not None
    storage_name = result.download_file.storage_name
    try:
        with default_storage.open(storage_name, 'rb') as file:
            rows = list(csv.DictReader(StringIO(file.read().decode('utf-8'))))

        assert rows == [{'id': str(own.pk), 'title': 'own'}]
    finally:
        default_storage.delete(storage_name)
