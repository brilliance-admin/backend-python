from django.apps import AppConfig


class HistoryChangesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'brilliance_admin.integrations.django.history_changes'
    label = 'brilliance_admin_history_changes'
    verbose_name = 'Brilliance Admin history changes'
