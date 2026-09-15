from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from brilliance_admin.schema.table.history_change_provider import LogType


class HistoryChange(models.Model):
    action_time = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, models.CASCADE)

    content_type = models.ForeignKey(
        ContentType,
        models.SET_NULL,
        blank=True,
        null=True,
    )
    object_id = models.TextField(blank=True, null=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    log_type = models.PositiveSmallIntegerField()
    action_slug = models.CharField(max_length=100, blank=True)
    category_path = models.CharField(max_length=255)
    data = models.JSONField(default=dict)

    class Meta:
        ordering = ['-action_time']
        indexes = [
            models.Index(
                fields=['category_path', 'action_time'],
                name='brilliance__categor_ee5c66_idx',
            ),
            models.Index(
                fields=['content_type', 'object_id'],
                name='brilliance__content_a53302_idx',
            ),
            models.Index(
                fields=['log_type', 'action_time'],
                name='brilliance__log_typ_04fd19_idx',
            ),
        ]
