from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='HistoryChange',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action_time', models.DateTimeField(auto_now_add=True)),
                ('object_id', models.TextField(blank=True, null=True)),
                ('log_type', models.PositiveSmallIntegerField()),
                ('action_slug', models.CharField(blank=True, max_length=100)),
                ('category_path', models.CharField(max_length=255)),
                ('data', models.JSONField(default=dict)),
                (
                    'content_type',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to='contenttypes.contenttype',
                    ),
                ),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-action_time']},
        ),
        migrations.AddIndex(
            model_name='historychange',
            index=models.Index(fields=['category_path', 'action_time'], name='brilliance__categor_ee5c66_idx'),
        ),
        migrations.AddIndex(
            model_name='historychange',
            index=models.Index(fields=['content_type', 'object_id'], name='brilliance__content_a53302_idx'),
        ),
        migrations.AddIndex(
            model_name='historychange',
            index=models.Index(fields=['log_type', 'action_time'], name='brilliance__log_typ_04fd19_idx'),
        ),
    ]
