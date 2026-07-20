from brilliance_admin import schema
from brilliance_admin.exceptions import AdminAPIException, APIError
from brilliance_admin.translations import TranslateText as _


class DjangoAdminRetrieveMixin:
    has_retrieve: bool = True

    async def retrieve(
        self,
        pk,
        user,
        language_context,
        debug: bool,
        parent_category=None,
        parent_pk=None,
    ) -> schema.RetrieveResult:
        if not self.has_retrieve:
            raise AdminAPIException(APIError(message=_('errors.method_not_allowed')), status_code=500)

        queryset = self.get_queryset().filter(**{self.pk_name: pk})
        queryset = self.apply_parent_filter(queryset, parent_category, parent_pk)
        record = await queryset.afirst()
        if record is None:
            raise AdminAPIException(
                APIError(message=_('errors.record_not_found') % {'pk_name': self.pk_name, 'pk': pk}, code='record_not_found'),
                status_code=400,
            )
        data = await self.table_schema.serialize(
            record,
            extra={"record": record, "user": user, "debug": debug},
        )
        return schema.RetrieveResult(data=data)
