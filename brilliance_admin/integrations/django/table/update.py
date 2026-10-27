from brilliance_admin import schema
from brilliance_admin.exceptions import AdminAPIException, APIError, ValidationError
from brilliance_admin.translations import TranslateText as _
from brilliance_admin.utils import DeserializeAction


class DjangoAdminUpdate:
    has_update: bool = True

    async def update(
        self,
        pk,
        data: dict,
        user,
        language_context,
        parent_category=None,
        parent_pk=None,
        history_change_provider=None,
        *, admin_schema,
    ) -> schema.UpdateResult:
        if not self.has_update:
            raise AdminAPIException(APIError(message=_('errors.method_not_allowed')), status_code=500)

        if pk is None:
            raise AdminAPIException(
                APIError(message=_('errors.pk_not_found') % {'pk_name': self.pk_name}, code='pk_not_found'),
                status_code=400,
            )

        if history_change_provider is not None:
            before = await self._retrieve(
                pk,
                user,
                language_context,
                parent_category,
                parent_pk,
                admin_schema=admin_schema,
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
        self.table_schema.validate_incoming_data(data)
        try:
            deserialized_data = await self.table_schema.deserialize_fields(
                data,
                DeserializeAction.UPDATE,
                extra={'admin_schema': admin_schema, 'model': self.model, 'record': record, 'user': user},
            )
        except ValidationError as e:
            raise AdminAPIException(
                APIError(code='validation_error', field_errors=e.data), status_code=400,
            ) from e
        record = await self.table_schema.update(
            record, deserialized_data, user=user, admin_schema=admin_schema,
        )

        result = schema.UpdateResult(pk=pk)
        if history_change_provider is not None:
            history_data = await self.table_schema.serialize(
                record,
                extra={
                    'admin_schema': admin_schema,
                    'record': record,
                    'user': user,
                    'debug': admin_schema.debug,
                    'raise_async_unsafe': self.raise_async_unsafe,
                },
            )
            await history_change_provider.save_update(
                category=self,
                parent_category=parent_category,
                user=user,
                pk=pk,
                before=before.data,
                data=history_data,
                language_context=language_context,
            )
        return result
