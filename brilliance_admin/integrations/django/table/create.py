from brilliance_admin import schema
from brilliance_admin.exceptions import AdminAPIException, APIError
from brilliance_admin.integrations.django.related_field import get_record_title
from brilliance_admin.schema.table.table_models import Record
from brilliance_admin.translations import TranslateText as _


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
        debug: bool,
        parent_category=None,
        parent_pk=None,
    ) -> schema.CreateResult:
        if not self.has_create:
            raise AdminAPIException(APIError(message=_('errors.method_not_allowed')), status_code=500)

        data = self.apply_parent_data(data, parent_category, parent_pk)
        debug_info = None
        if debug:
            record, debug_info = await self.table_schema.create(user, data, debug=True)
        else:
            record = await self.table_schema.create(user, data)
        pk_value = getattr(record, self.pk_name, None)
        choice = Record(
            key=pk_value,
            title=await get_record_title(record, self.raise_async_unsafe, debug=debug),
        )
        return schema.CreateResult(pk=pk_value, choice=choice, debug_info=debug_info)
