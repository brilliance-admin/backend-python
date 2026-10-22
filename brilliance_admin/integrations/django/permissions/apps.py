from django.apps import AppConfig


class PermissionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'brilliance_admin.integrations.django.permissions'
    label = 'brilliance_admin_permissions'
    verbose_name = 'Brilliance Admin permissions'
