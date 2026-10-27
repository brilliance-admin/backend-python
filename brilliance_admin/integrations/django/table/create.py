from brilliance_admin import schema
from brilliance_admin.exceptions import AdminAPIException, APIError, ValidationError
from brilliance_admin.integrations.django.related_field import get_record_title
from brilliance_admin.schema.table.table_models import Record
from brilliance_admin.translations import TranslateText as _
from brilliance_admin.utils import DeserializeAction


class DjangoAdminCreate:
    has_create: bool = True

    def apply_parent_data(self, data: dict, parent_category=None, parent_pk=None) -> dict:
        if parent_category is None or parent_pk is None:
            return data

        fk_field_name = self.get_parent_fk_field_name(parent_category)
        result = dict(data)
        result[fk_field_name] = parent_pk
        return result

    async def create(
        self,
        data: dict,
        user,
        language_context,
        parent_category=None,
        parent_pk=None,
        history_change_provider=None,
        *, admin_schema,
    ) -> schema.CreateResult:
        if not self.has_create:
            raise AdminAPIException(APIError(message=_('errors.method_not_allowed')), status_code=500)

        data = self.apply_parent_data(data, parent_category, parent_pk)
        self.table_schema.validate_incoming_data(data)
        try:
            deserialized_data = await self.table_schema.deserialize_fields(
                data,
                DeserializeAction.CREATE,
                extra={'admin_schema': admin_schema, 'model': self.model, 'record': None, 'user': user},
            )
        except ValidationError as e:
            raise AdminAPIException(
                APIError(code='validation_error', field_errors=e.data), status_code=400,
            ) from e
        record = await self.table_schema.create(
            deserialized_data, user=user, admin_schema=admin_schema,
        )
        pk_value = getattr(record, self.pk_name, None)
        choice = Record(
            key=pk_value,
            title=await get_record_title(record, self.raise_async_unsafe, debug=admin_schema.debug),
        )

        result = schema.CreateResult(pk=pk_value, choice=choice)
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
            await history_change_provider.save_create(
                category=self, parent_category=parent_category, user=user, pk=pk_value, data=history_data,
            )
        return result
