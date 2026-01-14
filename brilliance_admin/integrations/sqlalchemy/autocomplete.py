from brilliance_admin.auth import UserABC
from brilliance_admin.schema.admin_schema import AdminSchema
from brilliance_admin.schema.table.table_models import AutocompleteData, AutocompleteResult
from brilliance_admin.translations import LanguageContext


class SQLAlchemyAdminAutocompleteMixin:
    async def autocomplete(
            self,
            data: AutocompleteData,
            user: UserABC,
            language_context: LanguageContext,
            admin_schema: AdminSchema,
    ) -> AutocompleteResult:
        form_schema = None

        if data.action_name is not None:
            action_fn = self._get_action_fn(data.action_name)
            if not action_fn:
                raise Exception(f'Action "{data.action_name}" is not found')

            if not action_fn.form_schema:
                raise Exception(f'Action "{data.action_name}" form_schema is None')

            form_schema = action_fn.form_schema

        elif data.is_filter:
            if not self.table_filters:
                raise Exception(f'Action "{data.action_name}" table_filters is None')

            form_schema = self.table_filters

        else:
            form_schema = self.table_schema

        field = form_schema.get_field(data.field_slug)
        if not field:
            raise Exception(f'Field "{data.field_slug}" is not found')

        results = await field.autocomplete(
            self.model,
            data,
            user,
            extra={'db_async_session': self.db_async_session},
        )

        return AutocompleteResult(results=results)
