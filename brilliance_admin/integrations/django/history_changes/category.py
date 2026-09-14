from brilliance_admin.integrations.django.table import DjangoAdmin
from brilliance_admin.translations import TranslateText as _


class DjangoLogsAdmin(DjangoAdmin):
    model = 'brilliance_admin_history_changes.HistoryChange'

    slug = 'history-logs'
    title = _('history.title')
    icon = 'mdi-history'

    list_display = [
        'action_time',
        'user',
        'content_type',
        'object_id',
        'log_type',
        'action_slug',
        'category_path',
    ]
    ordering_fields = ['action_time', 'log_type', 'category_path']
    default_ordering = '-action_time'

    has_create = False
    has_update = False
    has_delete = False
