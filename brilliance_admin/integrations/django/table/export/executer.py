from dataclasses import dataclass
from tempfile import TemporaryFile
from time import perf_counter
from uuid import uuid4

from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.files import File
from django.core.files.storage import default_storage
from django.db import connections
from django.utils.dateparse import parse_datetime
from django.utils.module_loading import import_string
from django.utils.text import get_valid_filename

from brilliance_admin.api.utils import get_category
from brilliance_admin.schema.admin_schema import AdminSchema
from brilliance_admin.schema.table.category_table import CategoryTable
from brilliance_admin.schema.table.fields.base import DateTimeField
from brilliance_admin.schema.table.table_models import ListData


def _write_queryset_to_copy(queryset, export_fields, file) -> None:
    queryset = queryset.values(*export_fields)
    query_sql, params = queryset.query.sql_with_params()
    copy_sql = f'COPY ({query_sql}) TO STDOUT WITH CSV HEADER'

    with connections[queryset.db].cursor() as django_cursor:
        cursor = django_cursor.cursor
        if hasattr(cursor, 'copy'):
            with cursor.copy(copy_sql, params) as copy:
                for chunk in copy:
                    file.write(chunk)
            return

        prepared_copy_sql = cursor.mogrify(copy_sql, params).decode()
        cursor.copy_expert(prepared_copy_sql, file)


def _get_admin_schema() -> AdminSchema:
    try:
        admin_schema_path = settings.ADMIN_SCHEMA_PATH
    except AttributeError as e:
        raise RuntimeError('ADMIN_SCHEMA_PATH setting is required') from e

    try:
        admin_schema = import_string(admin_schema_path)
    except (ImportError, AttributeError) as e:
        raise RuntimeError(f'Cannot import ADMIN_SCHEMA_PATH "{admin_schema_path}"') from e

    if not isinstance(admin_schema, AdminSchema):
        raise RuntimeError(
            f'ADMIN_SCHEMA_PATH "{admin_schema_path}" must resolve to AdminSchema, '
            f'got {type(admin_schema).__name__}'
        )

    return admin_schema


@dataclass
class DjangoExportResult:
    storage_name: str
    url: str
    filename: str
    export_time_seconds: float


def _truncate_filename(filename) -> str:
    stem, suffix = filename.rsplit('.', 1)
    suffix = f'.{suffix}'
    stem_max_bytes = 255 - len(suffix.encode())
    stem = stem.encode()[:stem_max_bytes].decode('utf-8', errors='ignore')
    return f'{stem}{suffix}'


def _get_export_filename(category, filters, search) -> str:
    def format_value(value, is_datetime):
        if isinstance(value, bool):
            return str(value).lower()
        if is_datetime and isinstance(value, str):
            datetime_value = parse_datetime(value)
            if datetime_value:
                return datetime_value.strftime('%Y-%m-%d_%H-%M-%S')
        if isinstance(value, (list, tuple)):
            return '-'.join(format_value(item, is_datetime) for item in value)
        if isinstance(value, dict):
            return '-'.join(
                f'{key}-{format_value(item, is_datetime)}'
                for key, item in sorted(value.items())
            )
        return str(value)

    filter_parts = []
    for field_name, value in sorted(filters.items()):
        if value in (None, '', [], {}):
            continue
        field = category.table_filters.get_field(field_name)
        filter_parts.append(f'{field_name}-{format_value(value, isinstance(field, DateTimeField))}')

    parts = [category.slug, *filter_parts]
    if search:
        parts.append(f'search-{search}')
    return _truncate_filename(f'{get_valid_filename("__".join(parts))}.csv')


async def django_export(
    group_slug,
    category_slug,
    subcategory_slug,
    export_fields,
    pks,
    send_to_all,
    search,
    filters,
):
    started_at = perf_counter()
    category, _ = get_category(
        _get_admin_schema(),
        group_slug,
        category_slug,
        subcategory_slug,
        check_type=CategoryTable,
    )

    queryset = category.get_export_queryset()
    queryset = await category.apply_filters(
        queryset,
        ListData(search=search, filters=filters),
    )
    queryset = category.apply_search(queryset, ListData(search=search, filters=filters))
    queryset = category.apply_ordering(queryset, ListData())

    if not send_to_all:
        queryset = queryset.filter(pk__in=pks)

    filename = _get_export_filename(category, filters, search)
    storage_name = f'exports/{uuid4()}/{filename}'
    with TemporaryFile(mode='w+b') as file:
        await sync_to_async(_write_queryset_to_copy, thread_sensitive=True)(
            queryset,
            export_fields,
            file,
        )
        file.seek(0)
        saved_storage_name = await sync_to_async(default_storage.save, thread_sensitive=True)(
            storage_name,
            File(file, name=filename),
        )

    url = await sync_to_async(default_storage.url, thread_sensitive=True)(saved_storage_name)
    return DjangoExportResult(
        storage_name=saved_storage_name,
        url=url,
        filename=filename,
        export_time_seconds=perf_counter() - started_at,
    )
