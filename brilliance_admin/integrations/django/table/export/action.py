from brilliance_admin import schema
from brilliance_admin.exceptions import AdminAPIException, APIError, FieldError, ValidationError
from brilliance_admin.schema.table.admin_action import ActionData, ActionFileResult, ActionResult, admin_action
from brilliance_admin.schema.table.fields_schema import FieldsSchema
from brilliance_admin.translations import TranslateText as _
from brilliance_admin.utils import get_logger, humanize_field_name, validate_email

from .executer import django_export

logger = get_logger()


class ExportFieldsSchema(FieldsSchema):
    is_async = schema.BooleanField(
        label=_('export.is_async'),
        help_text=_('export.is_async__help_text'),
        default=False,
    )
    email = schema.StringField(
        label=_('export.email'),
        validator=lambda value, data: (
            value if value is None else validate_email(value) if data['is_async'] else value
        ),
    )
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


class DjangoPostgresExportAction:
    export_fields: list | None = None

    def get_export_queryset(self):
        return self.get_queryset(action='django_export')

    def get_actions(self):
        actions = super().get_actions()
        if not self.export_fields:
            actions.pop('django_export', None)
            return actions

        django_export_field = actions['django_export']
        fields_field = django_export_field.action_info['form_schema'].get_field('export_fields')

        annotations = self.get_export_queryset().query.annotations
        for field_path in self.export_fields:
            if field_path not in annotations:
                self.validate_lookup_path(field_path, 'export')

        fields_field.choices = [
            {
                'value': field_path,
                'title': (
                    humanize_field_name(field_path)
                    if field_path in annotations
                    else self.get_lookup_field_title(field_path)
                ),
            }
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
            logger.info('Django Export: celery task was sended for email=%s', action_data.form_data['email'])
            return ActionResult(_('export.successfully_async_message') % {'email': action_data.form_data['email']})

        export_result = await django_export(**export_kwargs)
        export_file = ActionFileResult(
            storage_name=export_result.storage_name,
            filename=export_result.filename,
            content_type='text/csv; charset=utf-8',
        )

        return ActionResult(download_file=export_file)
