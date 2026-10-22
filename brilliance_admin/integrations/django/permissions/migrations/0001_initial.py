from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='UserPermissionsSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rules', models.JSONField(default=dict)),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='brilliance_admin_permissions_settings',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
        ),
        migrations.CreateModel(
            name='PermissionsGroup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('rules', models.JSONField(default=dict)),
                ('is_superuser', models.BooleanField(default=False)),
                ('priority', models.IntegerField(default=0)),
                ('users', models.ManyToManyField(
                    blank=True,
                    related_name='brilliance_admin_permissions_groups',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
        ),
    ]
