import django
import pytest
from django.conf import settings
from django.db import connection
from tests.conftest import POSTGRES_PARSED

if not settings.configured:
    settings.configure(
        INSTALLED_APPS=[
            "django.contrib.contenttypes",
            "example.sections",
        ],
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": POSTGRES_PARSED.path.lstrip("/"),
                "USER": POSTGRES_PARSED.username,
                "PASSWORD": POSTGRES_PARSED.password,
                "HOST": POSTGRES_PARSED.hostname,
                "PORT": POSTGRES_PARSED.port,
            }
        },
        SECRET_KEY="test-secret-key",
        USE_TZ=True,
        DEFAULT_AUTO_FIELD="django.db.models.AutoField",
    )
    django.setup()


@pytest.fixture(scope="session", autouse=True)
def django_test_schema():
    from example.sections.django_models import DjangoAnotherExample, DjangoExample, DjangoUser

    with connection.schema_editor() as schema_editor:
        schema_editor.create_model(DjangoExample)
        schema_editor.create_model(DjangoAnotherExample)
        schema_editor.create_model(DjangoUser)

    yield

    with connection.schema_editor() as schema_editor:
        schema_editor.delete_model(DjangoUser)
        schema_editor.delete_model(DjangoAnotherExample)
        schema_editor.delete_model(DjangoExample)


@pytest.fixture(autouse=True)
def cleanup_django_tables():
    yield

    with connection.cursor() as cursor:
        cursor.execute(
            'TRUNCATE TABLE "django_user", "django_another_example", "django_example" RESTART IDENTITY CASCADE'
        )
