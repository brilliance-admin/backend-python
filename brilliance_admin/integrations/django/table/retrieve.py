from brilliance_admin import schema
from brilliance_admin.exceptions import AdminAPIException, APIError
from brilliance_admin.schema.table.table_action import TableAction
from brilliance_admin.translations import TranslateText as _


class DjangoAdminRetrieveMixin:
    has_retrieve: bool = True

    async def _retrieve(
        self,
        pk,
        user,
        language_context,
        parent_category=None,
        parent_pk=None,
        *, admin_schema,
    ) -> schema.RetrieveResult:
        if not self.has_retrieve:
            raise AdminAPIException(APIError(message=_('errors.method_not_allowed')), status_code=500)

        queryset = self.get_queryset(action=TableAction.RETRIEVE).filter(**{self.pk_name: pk})
        queryset = self.apply_parent_filter(queryset, parent_category, parent_pk)
        record = await queryset.afirst()
        if record is None:
            error = APIError(
                message=_('errors.record_not_found') % {'pk_name': self.pk_name, 'pk': pk},
                code='record_not_found',
            )
            raise AdminAPIException(
                error,
                status_code=400,
            )
        data = await self.table_schema.serialize(
            record,
            extra={
                'admin_schema': admin_schema,
                "record": record,
                "user": user,
                "debug": admin_schema.debug,
                "raise_async_unsafe": self.raise_async_unsafe,
            },
        )

        tab_counts = await self.get_tabs_count(pk)
        return schema.RetrieveResult(data=data, tab_counts=tab_counts)

    async def retrieve(
            self,
            pk,
            user,
            language_context,
            parent_category=None,
            parent_pk=None,
            history_change_provider=None,
            *, admin_schema,
    ) -> schema.RetrieveResult:
        result = await self._retrieve(
            pk,
            user,
            language_context,
            parent_category,
            parent_pk,
            admin_schema=admin_schema,
        )
        return result
