from brilliance_admin.exceptions import AdminAPIException, APIError
from brilliance_admin.integrations.sqlalchemy.utils import extract_integrity_detail
from brilliance_admin.schema.table.admin_action import ActionData, ActionResult, admin_action
from brilliance_admin.schema.table.table_action import TableAction
from brilliance_admin.translations import TranslateText as _
from brilliance_admin.utils import format_limited_items


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

        # pylint: disable=import-outside-toplevel
        from sqlalchemy import inspect
        from sqlalchemy.exc import IntegrityError

        col = inspect(self.model).mapper.columns[self.pk_name]
        python_type = col.type.python_type
        typed_pks = [python_type(pk) for pk in action_data.pks]

        try:
            async with self.db_async_session() as session:
                stmt = self.get_queryset(action=TableAction.ADMIN_ACTION, action_slug='delete')
                stmt = self.apply_parent_filter(stmt, parent_category, parent_pk)
                stmt = stmt.where(getattr(self.model, self.pk_name).in_(typed_pks))
                results = (await session.execute(stmt)).unique().scalars().all()

                found_ids = {getattr(obj, self.pk_name) for obj in results}
                missing = [pk for pk in typed_pks if pk not in found_ids]
                if missing:
                    raise AdminAPIException(
                        APIError(message=_('errors.items_not_found') % {'ids': format_limited_items(missing)}),
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
