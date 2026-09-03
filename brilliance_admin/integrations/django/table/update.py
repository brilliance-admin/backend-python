from brilliance_admin import schema
from brilliance_admin.exceptions import AdminAPIException, APIError
from brilliance_admin.translations import TranslateText as _
from brilliance_admin.utils import get_logger


logger = get_logger()


class DjangoAdminUpdate:
    has_update: bool = True

    async def update(
        self,
        pk,
        data: dict,
        user,
        language_context,
        debug: bool,
        parent_category=None,
        parent_pk=None,
    ) -> schema.UpdateResult:
        if not self.has_update:
            raise AdminAPIException(APIError(message=_('errors.method_not_allowed')), status_code=500)

        if pk is None:
            raise AdminAPIException(
                APIError(message=_('errors.pk_not_found') % {'pk_name': self.pk_name}, code='pk_not_found'),
                status_code=400,
            )

        queryset = self.model.objects.filter(**{self.pk_name: pk})
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
        debug_info = None
        if debug:
            record, debug_info = await self.table_schema.update(record, user, data, debug=True)
        else:
            await self.table_schema.update(record, user, data)

        logger.info(
            '%s model %s #%s updated by %s',
            type(self).__name__, self.table_schema.model.__name__, pk, user.username,
            extra={'data': data},
        )
        return schema.UpdateResult(pk=pk, debug_info=debug_info)
