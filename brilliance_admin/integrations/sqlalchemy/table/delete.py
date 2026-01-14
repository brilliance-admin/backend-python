from brilliance_admin.exceptions import APIError, AdminAPIException
from brilliance_admin.schema.table.admin_action import ActionData, ActionMessage, ActionResult, admin_action
from brilliance_admin.translations import TranslateText as _


class SQLAlchemyDeleteAction:
    has_delete: bool = True

    @admin_action(
        title=_('delete'),
        confirmation_text=_('delete_confirmation_text'),
        base_color='red-lighten-2',
        variant='outlined',
    )
    async def delete(self, *args, action_data: ActionData, **kwargs):
        if not self.has_delete:
            raise AdminAPIException(APIError(message=_('errors.method_not_allowed')), status_code=500)
        return ActionResult(message=ActionMessage(_('deleted_successfully')))
