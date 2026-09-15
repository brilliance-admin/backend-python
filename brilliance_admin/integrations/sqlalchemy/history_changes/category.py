from brilliance_admin.integrations.sqlalchemy.fields_schema import SQLAlchemyFieldsSchema
from brilliance_admin.integrations.sqlalchemy.table import SQLAlchemyAdmin
from brilliance_admin.schema.table.fields.base import ChoiceField
from brilliance_admin.schema.table.fields_schema import FormField, FormSet
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

from .models import HistoryChange, LogType


class SQLAlchemyLogsFieldsSchema(SQLAlchemyFieldsSchema):
    model = HistoryChange
    data = HistoryChangeDataField()
    log_type = ChoiceField(choices=LogType)

    extra_kwargs = {
        **HISTORY_LOGS_EXTRA_KWARGS,
        'pk': {'label': _('history.fields.pk')},
    }
    formset = FormSet(
        fields=[
            FormField('id', col_span=6),
            FormField('action_time', col_span=6),
            FormField('user', col_span=6),
            FormField('log_type', col_span=6),
            FormField('category_path', col_span=6),
            FormField('pk', col_span=6),
            FormField('action_slug', col_span=6),
            FormField('data', col_span=12),
        ],
    )


class SQLAlchemyLogsFiltersSchema(SQLAlchemyLogsFieldsSchema):
    model = HistoryChange

    formset = None
    data = None
    log_type = ChoiceField(choices=LogType)

    category_path = HistoryCategoryField()
    action_slug = HistoryActionField()

    fields = [
        *HISTORY_LOGS_FILTER_FIELDS,
        'pk',
        'log_type',
    ]
    extra_kwargs = {
        **HISTORY_LOGS_FILTER_EXTRA_KWARGS,
        'pk': {'label': _('history.fields.pk')},
    }


class SQLAlchemyLogsAdmin(HistoryLogsAdmin, SQLAlchemyAdmin):
    model = HistoryChange

    list_display = [
        'category_path',
        'action_time',
        'user',
        'pk',
        'log_type',
        'action_slug',
    ]

    table_schema = SQLAlchemyLogsFieldsSchema()
    table_filters = SQLAlchemyLogsFiltersSchema()
