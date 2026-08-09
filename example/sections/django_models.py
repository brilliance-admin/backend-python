import uuid
import factory
import timezone_field

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils.translation import gettext_lazy as _
from example.utils import DjangoFactoryBase


class DjangoExampleStatus(models.TextChoices):
    PENDING = "pending", _("Pending translated")
    DONE = "done", _("Done translated")


class DjangoUser(models.Model):
    username = models.CharField(max_length=150, unique=True)
    password = models.CharField(max_length=255, null=True, blank=True)
    is_admin = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "django_user"

    def __str__(self):
        return f'#{self.pk} {self.username}'


class DjangoUserFactory(DjangoFactoryBase):
    class Meta:
        model = DjangoUser

    username = factory.Faker("word")


class DjangoExample(models.Model):
    owner = models.ForeignKey(
        DjangoUser,
        on_delete=models.CASCADE,
        related_name="examples",
    )
    title = models.CharField(max_length=255, verbose_name=_('Title translated'))
    allowed_ips = ArrayField(models.CharField(max_length=255), default=list, blank=True)
    description = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=32, choices=DjangoExampleStatus.choices, default=DjangoExampleStatus.PENDING)
    is_active = models.BooleanField(default=True)
    count = models.IntegerField(default=0)
    uuid = models.UUIDField(default=uuid.uuid4, unique=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    rating = models.FloatField(default=0)
    payload = models.JSONField(default=dict, blank=True)
    event_date = models.DateField(null=True, blank=True)
    event_time = models.TimeField(null=True, blank=True)
    timezone = timezone_field.TimeZoneField(default='UTC')
    ttl = models.DurationField(null=True, blank=True)
    file = models.FileField(upload_to="django_example/files/", null=True, blank=True)
    image = models.ImageField(upload_to="django_example/images/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "django_example"
        verbose_name = _("Django example translated")
        verbose_name_plural = _("Django examples translated")

    def __str__(self):
        return f'#{self.pk} {self.title} (owner: {self.owner.username})'


class DjangoExampleFactory(DjangoFactoryBase):
    class Meta:
        model = DjangoExample

    owner = factory.SubFactory(DjangoUserFactory)
    title = factory.Faker("word")


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
        return f'#{self.pk} {self.title}'


class DjangoAnotherExampleFactory(DjangoFactoryBase):
    class Meta:
        model = DjangoAnotherExample

    example = factory.SubFactory(DjangoExampleFactory)
    title = factory.Faker("word")
