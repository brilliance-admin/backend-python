from brilliance_admin.integrations.django.table import DjangoAdmin
from brilliance_admin.integrations.django.fields_schema import DjangoFieldsSchema
from brilliance_admin.schema.table.fields.base import ChoiceField
from brilliance_admin.schema.table.fields_schema import FormField, FormSet
from brilliance_admin.schema.table.history_change_provider import LogType
from brilliance_admin.schema.table.history_logs_category import (
    HISTORY_LOGS_EXTRA_KWARGS,
    HISTORY_LOGS_FILTER_EXTRA_KWARGS,
    HISTORY_LOGS_FILTER_FIELDS,
    HistoryChangeDataField,
    HistoryActionField,
    HistoryCategoryField,
    HistoryLogsAdmin,
)
from brilliance_admin.translations import TranslateText as _


class DjangoLogsFieldsSchema(DjangoFieldsSchema):
    model = 'brilliance_admin_history_changes.HistoryChange'
    data = HistoryChangeDataField()
    log_type = ChoiceField(choices=LogType)

    extra_kwargs = {
        **HISTORY_LOGS_EXTRA_KWARGS,
        'object_id': {'label': _('history.fields.object_id')},
    }
    formset = FormSet(
        fields=[
            FormField('id', col_span=2),
            FormField('action_time', col_span=4),
            FormField('user', col_span=3),
            FormField('log_type', col_span=3),
            FormField('category_path', col_span=6),
            FormField('object_id', col_span=3),
            FormField('action_slug', col_span=12),
            FormField('data', col_span=12),
        ],
    )


class DjangoLogsFiltersSchema(DjangoLogsFieldsSchema):
    model = 'brilliance_admin_history_changes.HistoryChange'

    formset = None
    data = None
    category_path = HistoryCategoryField()
    action_slug = HistoryActionField()
    log_type = ChoiceField(choices=LogType)

    fields = [
        *HISTORY_LOGS_FILTER_FIELDS,
        'object_id',
        'log_type',
    ]
    extra_kwargs = {
        **HISTORY_LOGS_FILTER_EXTRA_KWARGS,
        'object_id': {'label': _('history.fields.object_id')},
    }


class DjangoLogsAdmin(HistoryLogsAdmin, DjangoAdmin):
    model = 'brilliance_admin_history_changes.HistoryChange'

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            table_schema=DjangoLogsFieldsSchema(),
            table_filters=DjangoLogsFiltersSchema(),
            **kwargs,
        )
