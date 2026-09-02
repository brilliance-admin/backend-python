from asgiref.sync import sync_to_async
from django.conf import settings
from django.db import connections
from django.utils.module_loading import import_string

from brilliance_admin.api.utils import get_category
from brilliance_admin.exceptions import AdminAPIException, APIError, FieldError, ValidationError
from brilliance_admin.schema.admin_schema import AdminSchema
from brilliance_admin.schema.table.admin_action import (
    ActionData, ActionFileResult, ActionResult, admin_action)
from brilliance_admin.schema.table.category_table import CategoryTable
from brilliance_admin.schema.table.fields_schema import FieldsSchema
from brilliance_admin.schema.table.table_models import ListData
from brilliance_admin.translations import TranslateText as _
from brilliance_admin import schema
from .export_file_handler import MemoryExportFileHandler


def _write_queryset_to_copy(queryset, export_fields, file_handler) -> None:
    queryset = queryset.values(*export_fields)
    query_sql, params = queryset.query.sql_with_params()
    copy_sql = f'COPY ({query_sql}) TO STDOUT WITH CSV HEADER'

    with connections[queryset.db].cursor() as django_cursor:
        cursor = django_cursor.cursor
        if hasattr(cursor, 'copy'):
            with cursor.copy(copy_sql, params) as copy:
                for chunk in copy:
                    file_handler.write(chunk)
            return

        prepared_copy_sql = cursor.mogrify(copy_sql, params).decode()
        cursor.copy_expert(prepared_copy_sql, file_handler.file)


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


async def django_export(
    group_slug,
    category_slug,
    subcategory_slug,
    export_fields,
    pks,
    send_to_all,
    search,
    filters,
    file_handler,
):
    category, _ = get_category(
        _get_admin_schema(),
        group_slug,
        category_slug,
        subcategory_slug,
        check_type=CategoryTable,
    )

    queryset = category.get_queryset(action='django_export')
    queryset = await category.apply_filters(
        queryset,
        ListData(search=search, filters=filters),
    )
    queryset = category.apply_search(queryset, ListData(search=search, filters=filters))
    queryset = category.apply_ordering(queryset, ListData())

    if not send_to_all:
        queryset = queryset.filter(pk__in=pks)

    await sync_to_async(_write_queryset_to_copy, thread_sensitive=True)(
        queryset,
        export_fields,
        file_handler,
    )

    return f'{category.slug}.csv'


class ExportFieldsSchema(FieldsSchema):
    is_async = schema.BooleanField(
        label=_('export.is_async'),
        help_text=_('export.is_async__help_text'),
        default=False,
    )
    email = schema.StringField(label=_('export.email'))
    export_fields = schema.MultipleChoiceField(
        label=_('export.fields'),
        default_all_selected=True,
    )

    async def deserialize_fields(self, *args, **kwargs):
        data = await super().deserialize_fields(*args, **kwargs)
        if data['is_async'] and not data['email']:
            raise ValidationError(data={
                'email': FieldError(_('export.email_required_for_async'), 'email_required_for_async'),
            })
        return data


class DjangoExportAction:
    export_fields: list | None = None

    def get_actions(self):
        actions = super().get_actions()
        if not self.export_fields:
            actions.pop('django_export', None)
            return actions

        django_export_field = actions['django_export']
        fields_field = django_export_field.action_info['form_schema'].get_field('export_fields')

        for field_path in self.export_fields:
            self.validate_lookup_path(field_path, 'export')

        fields_field.choices = [
            {'value': field_path, 'title': self.get_lookup_field_title(field_path)}
            for field_path in self.export_fields
        ]

        return actions

    @admin_action(
        title=_('export.title'),
        icon='mdi-database-export-outline',
        form_schema=ExportFieldsSchema(),
    )
    async def django_export(self, *args, action_data: ActionData, **kwargs):
        if not self.export_fields:
            raise AdminAPIException(APIError(message=_('errors.method_not_allowed')), status_code=500)

        export_kwargs = {
            'group_slug': action_data.group_slug,
            'category_slug': action_data.category_slug,
            'subcategory_slug': action_data.subcategory_slug,
            'export_fields': action_data.form_data['export_fields'],
            'pks': action_data.pks,
            'send_to_all': action_data.send_to_all,
            'search': action_data.search,
            'filters': action_data.filters,
        }

        if action_data.form_data['is_async']:
            from brilliance_admin.integrations.django.celery import django_export as django_export_task

            django_export_task.delay(email=action_data.form_data['email'], **export_kwargs)
            return ActionResult(_('export.successfully_async_message') % {'email': action_data.form_data['email']})

        file_handler = MemoryExportFileHandler()
        try:
            filename = await django_export(**export_kwargs, file_handler=file_handler)
            content = file_handler.get_content()
        finally:
            file_handler.close()

        export_file = ActionFileResult(
            content=content,
            filename=filename,
            content_type='text/csv; charset=utf-8',
        )

        return ActionResult(download_file=export_file)
