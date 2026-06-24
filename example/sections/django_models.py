import uuid

from django.db import models


class DjangoExample(models.Model):
    title = models.CharField(max_length=255)
    description = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    count = models.IntegerField(default=0)
    uuid = models.UUIDField(default=uuid.uuid4, unique=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    rating = models.FloatField(default=0)
    payload = models.JSONField(default=dict, blank=True)
    event_date = models.DateField(null=True, blank=True)
    event_time = models.TimeField(null=True, blank=True)
    file = models.FileField(upload_to="django_example/files/", null=True, blank=True)
    image = models.ImageField(upload_to="django_example/images/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "django_example"

    def __str__(self):
        return self.title


class DjangoAnotherExample(models.Model):
    example = models.ForeignKey(
        DjangoExample,
        on_delete=models.CASCADE,
        related_name="another_examples",
    )
    title = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "django_another_example"

    def __str__(self):
        return self.title


class DjangoUser(models.Model):
    username = models.CharField(max_length=150, unique=True)
    password = models.CharField(max_length=255, null=True, blank=True)
    is_admin = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "django_user"

    def __str__(self):
        return self.username
