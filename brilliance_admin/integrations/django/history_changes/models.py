from django.conf import settings
from django.db import models


class HistoryChange(models.Model):
    action_time = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, models.CASCADE)

    object_id = models.TextField(blank=True, null=True)

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
                fields=['log_type', 'action_time'],
                name='brilliance__log_typ_04fd19_idx',
            ),
        ]
