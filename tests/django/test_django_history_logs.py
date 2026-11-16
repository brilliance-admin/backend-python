import pytest

from brilliance_admin.integrations.django import DjangoAdmin, DjangoFieldsSchema, DjangoLogsProvider
from brilliance_admin.integrations.django.history_changes.models import HistoryChange
from example.main import admin_schema
from example.sections.django_models import DjangoExample, DjangoUserFactory


class DatetimeHistoryCategory(DjangoAdmin):
    model = DjangoExample
    table_schema = DjangoFieldsSchema(
        model=DjangoExample,
        exclude_fields=[
            field.name for field in DjangoExample._meta.fields
            if field.name not in {'id', 'owner', 'title', 'created_at'}
        ],
    )


@pytest.mark.asyncio
async def test_create_history_serializes_datetime(language_context, mocker):
    log_error = mocker.patch('brilliance_admin.integrations.django.table.create.logger.exception')
    user = await DjangoUserFactory()
    category = DatetimeHistoryCategory()
    category._group_slug = 'examples'

    result = await category.create(
        admin_schema=admin_schema,
        data={'owner': user.pk, 'title': 'Datetime history'},
        user=user,
        language_context=language_context,
        history_change_provider=DjangoLogsProvider(),
    )

    record = await DjangoExample.objects.aget(pk=result.pk)
    assert record.title == 'Datetime history'
    entry = await HistoryChange.objects.aget(object_id=str(result.pk))
    assert entry.data['created_at'] == record.created_at.isoformat().replace('+00:00', 'Z')
    log_error.assert_not_called()
