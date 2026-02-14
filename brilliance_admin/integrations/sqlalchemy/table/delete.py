from brilliance_admin.exceptions import AdminAPIException, APIError
from brilliance_admin.integrations.sqlalchemy.utils import extract_integrity_detail
from brilliance_admin.schema.table.admin_action import ActionData, ActionResult, admin_action
from brilliance_admin.translations import TranslateText as _


class SQLAlchemyDeleteAction:
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
        variant='outlined',
    )
    async def delete(self, *args, action_data: ActionData, **kwargs):
        if not self.has_delete:
            raise AdminAPIException(APIError(message=_('errors.method_not_allowed')), status_code=500)

        assert action_data.pks

        # pylint: disable=import-outside-toplevel
        from sqlalchemy import inspect, select
        from sqlalchemy.exc import IntegrityError

        col = inspect(self.model).mapper.columns[self.pk_name]
        python_type = col.type.python_type
        typed_pks = [python_type(pk) for pk in action_data.pks]

        try:
            async with self.db_async_session() as session:
                stmt = select(self.model).where(getattr(self.model, self.pk_name).in_(typed_pks))
                results = (await session.execute(stmt)).scalars().all()

                if len(results) != len(typed_pks):
                    found_ids = {str(getattr(obj, self.pk_name)) for obj in results}
                    missing = [pk for pk in typed_pks if str(pk) not in found_ids]
                    raise AdminAPIException(
                        APIError(message=_('errors.items_not_found') % {'ids': ', '.join(str(pk) for pk in missing)}),
                        status_code=404,
                    )

                for obj in results:
                    await session.delete(obj)
                await session.commit()

        except IntegrityError as e:
            await session.rollback()
            detail = extract_integrity_detail(e)
            raise AdminAPIException(
                APIError(message=_('errors.delete_integrity_error') % {'detail': detail}),
                status_code=400,
            ) from e

        return ActionResult(_('deleted_successfully'))
