from asgiref.sync import sync_to_async
from django.db import transaction
from django.db.models.deletion import ProtectedError

from brilliance_admin.exceptions import AdminAPIException, APIError
from brilliance_admin.schema.table.admin_action import ActionData, ActionResult, admin_action
from brilliance_admin.schema.table.table_action import TableAction
from brilliance_admin.translations import TranslateText as _
from brilliance_admin.utils import SupportsStr, format_limited_items


class DjangoDeleteAction:
    has_delete: bool = True

    def _delete_queryset(self, queryset, typed_pks):
        with transaction.atomic(using=queryset.db):
            found_ids = set(queryset.select_for_update(of=('self',)).values_list(self.pk_name, flat=True))
            missing = [pk for pk in typed_pks if pk not in found_ids]
            if missing:
                raise AdminAPIException(
                    APIError(message=_('errors.items_not_found') % {'ids': format_limited_items(missing)}),
                    status_code=404,
                )
            queryset.delete()

    def _format_protected_delete_error(self, action_data: ActionData, error: ProtectedError) -> SupportsStr:
        deleted_model = self.model._meta.verbose_name
        deleted_pks = ', '.join(str(pk) for pk in action_data.pks)
        protected_objects_by_model = {}

        for protected_object in error.protected_objects:
            protected_model = protected_object._meta.verbose_name
            protected_objects_by_model.setdefault(protected_model, []).append(str(protected_object))

        details = '\n'.join(
            f'{model_name} - {format_limited_items(objects)}'
            for model_name, objects in protected_objects_by_model.items()
        )
        return _('errors.delete_protected') % {
            'model': deleted_model,
            'pks': deleted_pks,
            'details': details,
        }

    def get_actions(self):
        actions = super().get_actions()
        if not self.has_delete:
            actions.pop('delete', None)
        return actions

    @admin_action(
        title=_('delete'),
        confirmation_text=_('delete_confirmation_text'),
        base_color='red-lighten-2',
        icon='mdi-delete-outline',
        variant='outlined',
    )
    async def delete(self, *args, action_data: ActionData, parent_category=None, parent_pk=None, **kwargs):
        if not self.has_delete:
            raise AdminAPIException(APIError(message=_('errors.method_not_allowed')), status_code=500)

        assert action_data.pks

        if parent_category is not None and parent_pk is None:
            raise AdminAPIException(
                APIError(message='parent_pk is required for subcategory deletion', code='parent_pk_required'),
                status_code=400,
            )

        pk_field = self.model._meta.get_field(self.pk_name)
        typed_pks = [pk_field.to_python(pk) for pk in action_data.pks]
        queryset = self.get_queryset(action=TableAction.ADMIN_ACTION, action_slug='delete')
        queryset = self.apply_parent_filter(queryset, parent_category, parent_pk)
        queryset = queryset.filter(**{f'{self.pk_name}__in': typed_pks})
        try:
            await sync_to_async(self._delete_queryset, thread_sensitive=True)(queryset, typed_pks)
        except ProtectedError as e:
            error_message = await sync_to_async(
                self._format_protected_delete_error,
                thread_sensitive=True,
            )(action_data, e)
            raise AdminAPIException(
                APIError(message=error_message, code='protected_error'),
                status_code=400,
            ) from e

        return ActionResult(_('deleted_successfully'))
