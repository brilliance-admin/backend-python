import pytest
from django.conf import settings

from brilliance_admin import schema
from brilliance_admin.integrations.django import DjangoFieldsSchema
from brilliance_admin.integrations.django.table import DjangoAdmin
from brilliance_admin.integrations.django.table.export import DjangoExportAction, django_export
from brilliance_admin.integrations.django.table.export_file_handler import MemoryExportFileHandler
from example.sections.django_models import DjangoExample, DjangoExampleFactory


class DjangoExportTestAdmin(DjangoExportAction, DjangoAdmin):
    pass


def test_export_rejects_unknown_field():
    category = DjangoExportTestAdmin(
        model=DjangoExample,
        export_fields=['not_a_model_field'],
    )

    with pytest.raises(AttributeError, match='export field "not_a_model_field" not found'):
        category.get_actions()


def test_export_fields_support_model_related_and_json_paths():
    category = DjangoExportTestAdmin(
        model=DjangoExample,
        export_fields=['title', 'owner__username', 'payload__source'],
    )

    action = category.get_actions()['django_export']
    fields_field = action.action_info['form_schema'].get_field('export_fields')

    assert fields_field.choices == [
        {'value': 'title', 'title': 'Title translated'},
        {'value': 'owner__username', 'title': 'Owner - Username'},
        {'value': 'payload__source', 'title': 'Payload - Source'},
    ]


@pytest.mark.asyncio
async def test_sync_export_applies_search_filters_and_default_ordering(monkeypatch):
    category = DjangoExportTestAdmin(
        model=DjangoExample,
        slug='examples',
        search_fields=['title'],
        default_ordering='-count',
        export_fields=['title', 'count'],
        table_filters=DjangoFieldsSchema(
            model=DjangoExample,
            fields=['is_active'],
        ),
    )
    admin_schema = schema.AdminSchema(
        categories=[schema.CategoryGroup(slug='group', subcategories=[category])],
        auth=None,
    )
    monkeypatch.setattr(settings, 'ADMIN_SCHEMA_PATH', 'backoffice.admin.admin_schema', raising=False)

    def get_admin_schema(path):
        assert path == settings.ADMIN_SCHEMA_PATH
        return admin_schema

    monkeypatch.setattr(
        'brilliance_admin.integrations.django.table.export.import_string',
        get_admin_schema,
    )

    await DjangoExampleFactory(title='alpha low', count=1, is_active=True)
    await DjangoExampleFactory(title='alpha high', count=2, is_active=True)
    await DjangoExampleFactory(title='alpha inactive', count=3, is_active=False)
    await DjangoExampleFactory(title='beta', count=4, is_active=True)

    file_handler = MemoryExportFileHandler()
    filename = await django_export(
        group_slug='group',
        category_slug='examples',
        subcategory_slug=None,
        export_fields=['title', 'count'],
        pks=[],
        send_to_all=True,
        search='alpha%',
        filters={'is_active': True},
        file_handler=file_handler,
    )

    assert filename == 'examples.csv'
    assert file_handler.get_content().decode() == 'title,count\nalpha high,2\nalpha low,1\n'
