from asgiref.sync import async_to_sync
from celery import shared_task
from django.core.mail import send_mail

from brilliance_admin.integrations.django.table.export import django_export as run_django_export
from brilliance_admin.utils import get_logger


logger = get_logger()


EXPORT_EMAIL_TEMPLATE = '''{url}

Export time: {export_time_seconds:.2f} s'''

EXPORT_ERROR_EMAIL_TEMPLATE = 'Export failed. Try again later.'


@shared_task
def django_export(email, *args, **kwargs):
    try:
        export_result = async_to_sync(run_django_export)(*args, **kwargs)
        message = EXPORT_EMAIL_TEMPLATE.format(
            url=export_result.url,
            export_time_seconds=export_result.export_time_seconds,
        )

        send_mail(
            subject=f'Export: {kwargs["group_slug"]}/{kwargs["category_slug"]}',
            message=message,
            from_email=None,
            recipient_list=[email],
        )
    except Exception:
        logger.exception(
            'Django export failed: group=%s category=%s',
            kwargs['group_slug'],
            kwargs['category_slug'],
            extra={
                'extra_kwargs': {
                    'group_slug': kwargs['group_slug'],
                    'category_slug': kwargs['category_slug'],
                },
            },
        )
        send_mail(
            subject=f'Export failed: {kwargs["group_slug"]}/{kwargs["category_slug"]}',
            message=EXPORT_ERROR_EMAIL_TEMPLATE,
            from_email=None,
            recipient_list=[email],
        )
