from time import perf_counter

from asgiref.sync import async_to_sync
from celery import shared_task
from django.core.mail import send_mail

from .action import django_export as run_django_export
from .file_handler import StorageExportFileHandler


EXPORT_EMAIL_TEMPLATE = """{url}

Export time: {export_time_seconds:.2f} s"""


@shared_task
def django_export(email, *args, **kwargs):
    started_at = perf_counter()
    file_handler = StorageExportFileHandler()
    try:
        filename = async_to_sync(run_django_export)(*args, **kwargs, file_handler=file_handler)
        url = file_handler.save(filename)
    finally:
        file_handler.close()

    export_time_seconds = perf_counter() - started_at
    message = EXPORT_EMAIL_TEMPLATE.format(
        url=url,
        export_time_seconds=export_time_seconds,
    )

    send_mail(
        subject='Export',
        message=message,
        from_email=None,
        recipient_list=[email],
    )
