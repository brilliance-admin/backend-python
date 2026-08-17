from asgiref.sync import sync_to_async
from django.db.models.deletion import ProtectedError

from brilliance_admin.exceptions import AdminAPIException, APIError
from brilliance_admin.schema.table.admin_action import ActionData, ActionResult, admin_action
from brilliance_admin.translations import TranslateText as _
from brilliance_admin.utils import SupportsStr


class DjangoDeleteAction:
    has_delete: bool = True

    def _format_protected_delete_error(self, action_data: ActionData, error: ProtectedError) -> SupportsStr:
        deleted_model = self.model._meta.verbose_name
        deleted_pks = ', '.join(str(pk) for pk in action_data.pks)
        protected_objects_by_model = {}

        for protected_object in error.protected_objects:
            protected_model = protected_object._meta.verbose_name
            protected_objects_by_model.setdefault(protected_model, []).append(str(protected_object))

        details = '\n'.join(
            f'{model_name} - {", ".join(objects)}'
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
    async def delete(self, *args, action_data: ActionData, **kwargs):
        if not self.has_delete:
            raise AdminAPIException(APIError(message=_('errors.method_not_allowed')), status_code=500)

        assert action_data.pks

        queryset = self.model.objects.filter(**{f'{self.pk_name}__in': action_data.pks})
        try:
            await queryset.adelete()
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
