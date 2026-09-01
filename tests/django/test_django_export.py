from datetime import datetime, timezone

import pytest
from django.conf import settings
from django.core.files.storage import default_storage
from django.db import connection, models
from django.db.models import CharField, DecimalField, ExpressionWrapper, F, Func, Value

from brilliance_admin import schema
from brilliance_admin.integrations.django import DjangoFieldsSchema
from brilliance_admin.integrations.django.table import DjangoAdmin
from brilliance_admin.integrations.django.table.export import DjangoPostgresExportAction, django_export
from example.sections.django_models import DjangoExample, DjangoExampleFactory


class DjangoExportTestAdmin(DjangoPostgresExportAction, DjangoAdmin):
    pass


class DjangoExportPayment(models.Model):
    amount = models.BigIntegerField()

    class Meta:
        app_label = 'sections'
        db_table = 'django_export_payment'


@pytest.fixture
def django_export_payment_schema():
    with connection.schema_editor() as schema_editor:
        schema_editor.create_model(DjangoExportPayment)

    yield

    with connection.schema_editor() as schema_editor:
        schema_editor.delete_model(DjangoExportPayment)


class DjangoExportFormattedAmountTestAdmin(DjangoPostgresExportAction, DjangoAdmin):
    def get_export_queryset(self):
        return super().get_export_queryset().annotate(
            amount=Func(
                ExpressionWrapper(
                    F('count') / Value(100.0),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                ),
                Value('FM9999999990D00'),
                function='TO_CHAR',
                output_field=CharField(),
            ),
        )


class DjangoExportFormattedBigAmountTestAdmin(DjangoPostgresExportAction, DjangoAdmin):
    def get_export_queryset(self):
        return super().get_export_queryset().annotate(
            amount_minor=Func(
                ExpressionWrapper(
                    F('amount') / Value(100.0),
                    output_field=DecimalField(max_digits=20, decimal_places=2),
                ),
                Value('FM9999999990D00'),
                function='TO_CHAR',
                output_field=CharField(),
            ),
        )


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
            fields=['is_active', 'created_at', 'description'],
            created_at=schema.DateTimeField(range=True),
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
        'brilliance_admin.integrations.django.table.export.executer.import_string',
        get_admin_schema,
    )

    alpha_low = await DjangoExampleFactory(title='alpha low', count=1, is_active=True, description='export')
    alpha_high = await DjangoExampleFactory(title='alpha high', count=2, is_active=True, description='export')
    alpha_outside_range = await DjangoExampleFactory(
        title='alpha outside', count=4, is_active=True, description='export',
    )
    await DjangoExampleFactory(title='alpha inactive', count=3, is_active=False)
    await DjangoExampleFactory(title='beta', count=4, is_active=True)
    await DjangoExample.objects.filter(pk__in=[alpha_low.pk, alpha_high.pk]).aupdate(
        created_at=datetime(2023, 1, 1, 12, 0, tzinfo=timezone.utc),
    )
    await DjangoExample.objects.filter(pk=alpha_outside_range.pk).aupdate(
        created_at=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
    )

    filters = {
        'is_active': True,
        'description': 'export',
        'created_at': {
            'from': '2023-01-01T00:00:00+00:00',
            'to': '2023-01-01T23:59:59+00:00',
        },
    }

    export_result = await django_export(
        group_slug='group',
        category_slug='examples',
        subcategory_slug=None,
        export_fields=['title', 'count'],
        pks=[],
        send_to_all=True,
        search='alpha%',
        filters=filters,
    )

    assert export_result.filename == (
        'examples__created_at-from-2023-01-01_00-00-00-to-2023-01-01_23-59-59'
        '__description-export__is_active-true__search-alpha.csv'
    )
    with default_storage.open(export_result.storage_name, mode='rb') as file:
        assert file.read().decode() == 'title,count\nalpha high,2\nalpha low,1\n'
    default_storage.delete(export_result.storage_name)


@pytest.mark.asyncio
async def test_export_supports_formatted_annotation(monkeypatch):
    category = DjangoExportFormattedAmountTestAdmin(
        model=DjangoExample,
        slug='examples',
        export_fields=['amount'],
    )
    admin_schema = schema.AdminSchema(
        categories=[schema.CategoryGroup(slug='group', subcategories=[category])],
        auth=None,
    )
    monkeypatch.setattr(settings, 'ADMIN_SCHEMA_PATH', 'backoffice.admin.admin_schema', raising=False)
    monkeypatch.setattr(
        'brilliance_admin.integrations.django.table.export.executer.import_string',
        lambda path: admin_schema,
    )

    assert category.get_actions()['django_export'].action_info['form_schema'].get_field(
        'export_fields',
    ).choices == [{'value': 'amount', 'title': 'Amount'}]

    await DjangoExampleFactory(count=1250)
    export_result = await django_export(
        group_slug='group',
        category_slug='examples',
        subcategory_slug=None,
        export_fields=['amount'],
        pks=[],
        send_to_all=True,
        search=None,
        filters={},
    )

    with default_storage.open(export_result.storage_name, mode='rb') as file:
        assert file.read().decode() == 'amount\n12.50\n'
    default_storage.delete(export_result.storage_name)


@pytest.mark.asyncio
async def test_export_formats_big_minor_amount(monkeypatch, django_export_payment_schema):
    category = DjangoExportFormattedBigAmountTestAdmin(
        model=DjangoExportPayment,
        slug='payments',
        export_fields=['amount_minor'],
    )
    admin_schema = schema.AdminSchema(
        categories=[schema.CategoryGroup(slug='group', subcategories=[category])],
        auth=None,
    )
    monkeypatch.setattr(settings, 'ADMIN_SCHEMA_PATH', 'backoffice.admin.admin_schema', raising=False)
    monkeypatch.setattr(
        'brilliance_admin.integrations.django.table.export.executer.import_string',
        lambda path: admin_schema,
    )

    await DjangoExportPayment.objects.acreate(amount=234234234243)
    export_result = await django_export(
        group_slug='group',
        category_slug='payments',
        subcategory_slug=None,
        export_fields=['amount_minor'],
        pks=[],
        send_to_all=True,
        search=None,
        filters={},
    )

    with default_storage.open(export_result.storage_name, mode='rb') as file:
        assert file.read().decode() == 'amount_minor\n2342342342.43\n'
    default_storage.delete(export_result.storage_name)
