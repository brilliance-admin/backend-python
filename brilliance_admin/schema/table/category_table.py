import abc
import asyncio
import copy
from typing import Awaitable, List

from fastapi import HTTPException, Request
from pydantic import Field

from brilliance_admin.auth import UserABC
from brilliance_admin.exceptions import AdminAPIException, APIError
from brilliance_admin.schema.admin_schema import AdminSchema
from brilliance_admin.schema.category import BaseCategory, TableInfoSchemaData
from brilliance_admin.schema.table.admin_action import ActionData, ActionResult
from brilliance_admin.schema.table.fields_schema import FieldsSchema
from brilliance_admin.schema.table.table_models import AutocompleteData, AutocompleteResult, ListData, TableListResult
from brilliance_admin.translations import LanguageContext
from brilliance_admin.utils import DeserializeAction, SupportsStr


class CategoryTable(BaseCategory):
    _type_slug: str = 'table'

    search_enabled: bool = False
    search_help: SupportsStr | None = None

    table_schema: FieldsSchema = None
    table_filters: FieldsSchema | None = None

    ordering_fields: List[str] = Field(default_factory=list)
    default_ordering: str | None = None

    pk_name: str | None = None

    def __init__(self, *args, table_schema=None, table_filters=None, **kwargs):
        super().__init__(*args, **kwargs)

        if table_schema:
            self.table_schema = table_schema

        if table_filters:
            self.table_filters = table_filters

        if self.slug is None:
            msg = f'Category table attribute {type(self).__name__}.slug must be set'
            raise Exception(msg)

    @property
    def has_retrieve(self):
        if not self.pk_name:
            return False

        fn = getattr(self, 'retrieve', None)
        return asyncio.iscoroutinefunction(fn)

    @property
    def has_create(self):
        fn = getattr(self, 'create', None)
        return asyncio.iscoroutinefunction(fn)

    @property
    def has_update(self):
        fn = getattr(self, 'update', None)
        return asyncio.iscoroutinefunction(fn)

    def generate_schema(self, user, language_context: LanguageContext) -> dict:
        schema = super().generate_schema(user, language_context)

        table_schema = getattr(self, 'table_schema', None)
        if not table_schema or not issubclass(table_schema.__class__, FieldsSchema):
            raise AttributeError(f'Admin category {self.__class__} must have table_schema instance of FieldsSchema')

        table = TableInfoSchemaData(
            table_schema=self.table_schema.generate_schema(user, language_context),
            ordering_fields=self.ordering_fields,
            default_ordering=self.default_ordering,

            search_enabled=self.search_enabled,
            search_help=language_context.get_text(self.search_help),

            pk_name=self.pk_name,
            can_retrieve=self.has_retrieve,

            can_create=self.has_create,
            can_update=self.has_update,
        )

        if self.table_filters:
            table.table_filters = self.table_filters.generate_schema(user, language_context)

        actions = {}
        for attribute_name in dir(self):
            if '__' in attribute_name:
                continue

            attribute = getattr(self, attribute_name)
            if asyncio.iscoroutinefunction(attribute) and getattr(attribute, '__action__', False):
                action = copy.copy(attribute.action_info)

                action['title'] = language_context.get_text(action.get('title'))
                action['description'] = language_context.get_text(action.get('description'))
                action['confirmation_text'] = language_context.get_text(action.get('confirmation_text'))

                form_schema = action['form_schema']
                if form_schema:
                    try:
                        action['form_schema'] = form_schema.generate_schema(user, language_context)
                    except Exception as e:
                        msg = f'Action {attribute} form schema {form_schema} error: {e}'
                        raise Exception(msg) from e

                actions[attribute_name] = action

        table.actions = actions
        schema.table_info = table
        return schema

    def _get_action_fn(self, action: str) -> Awaitable | None:
        attribute = getattr(self, action)
        if not asyncio.iscoroutinefunction(attribute) or not getattr(attribute, '__action__', False):
            return None

        return attribute

    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-positional-arguments
    async def _perform_action(
            self,
            request: Request,
            action: str,
            action_data: ActionData,
            language_context: LanguageContext,
            user: UserABC,
            admin_schema: AdminSchema,
    ) -> ActionResult:
        action_fn = self._get_action_fn(action)
        if action_fn is None:
            raise HTTPException(status_code=404, detail=f'Action "{action}" is not found')

        try:
            form_schema = action_fn.action_info['form_schema']
            if form_schema:
                deserialized_data = await form_schema.deserialize(
                    action_data.form_data,
                    action=DeserializeAction.TABLE_ACTION,
                    extra={'user': user, 'request': request}
                )
                action_data.form_data = deserialized_data

            result: ActionResult = await action_fn(action_data)
        except AdminAPIException as e:
            raise e
        except Exception as e:
            raise AdminAPIException(
                APIError(message=str(e), code='user_action_error'),
                status_code=500,
            ) from e

        return result

    async def autocomplete(self, data: AutocompleteData, user: UserABC, schema: AdminSchema) -> AutocompleteResult:
        """
        Retrieves list of found options to select.
        """
        raise NotImplementedError('autocomplete is not implemented')

    # pylint: disable=too-many-arguments
    @abc.abstractmethod
    async def get_list(
            self, list_data: ListData, user: UserABC, language_context: LanguageContext, admin_schema: AdminSchema
    ) -> TableListResult:
        raise NotImplementedError()

#     async def retrieve(self, pk: Any, user: UserABC, language_context: LanguageContext, admin_schema: AdminSchema) -> RetrieveResult:
#        raise NotImplementedError()

#    async def create(self, data: dict, user: UserABC, language_context: LanguageContext, admin_schema: AdminSchema) -> CreateResult:
#        raise NotImplementedError()

#    async def update(self, pk: Any, data: dict, user: UserABC, language_context: LanguageContext, admin_schema: AdminSchema) -> UpdateResult:
#        raise NotImplementedError()
