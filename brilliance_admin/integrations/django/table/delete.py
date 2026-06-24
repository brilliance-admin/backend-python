from brilliance_admin.exceptions import AdminAPIException, APIError
from brilliance_admin.schema.table.admin_action import ActionData, ActionResult, admin_action
from brilliance_admin.translations import TranslateText as _


class DjangoDeleteAction:
    has_delete: bool = True

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
        await queryset.adelete()
        return ActionResult(_('deleted_successfully'))
