from django.conf import settings
from django.db import models


class UserPermissionsSettings(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='brilliance_admin_permissions_settings',
    )
    rules = models.JSONField(default=dict)


class PermissionsGroup(models.Model):
    title = models.CharField(max_length=255)
    users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='brilliance_admin_permissions_groups',
        blank=True,
    )
    rules = models.JSONField(default=dict)
    is_superuser = models.BooleanField(default=False)
    priority = models.IntegerField(default=0)

    def __str__(self):
        return f'{self.title} (priority: {self.priority})'
