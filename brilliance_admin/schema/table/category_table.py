import abc
import copy
import inspect
from typing import Awaitable, Dict, List

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
from brilliance_admin.utils import DeserializeAction, SupportsStr, get_logger

logger = get_logger()


class CategoryTable(BaseCategory):
    _type_slug: str = 'table'

    search_enabled: bool = False
    search_help: SupportsStr | None = None

    table_schema: FieldsSchema = None
    table_filters: FieldsSchema | None = None

    list_display: List[str] | None = None

    ordering_fields: List[str] = Field(default_factory=list)
    default_ordering: str | None = None

    pk_name: str | None = None

    def __init__(self, *args, table_schema=None, table_filters=None, **kwargs):
        super().__init__(*args, **kwargs)

        if table_schema:
            self.table_schema = table_schema

        if table_filters:
            self.table_filters = table_filters

        if self.list_display and self.table_schema:
            for field_slug in self.list_display:
                if field_slug not in self.table_schema.fields:
                    msg = f'Field "{field_slug}" inside {type(self).__name__}.list_display, but not presented in table_schema fields; available options: {self.table_schema.fields}'
                    raise AttributeError(msg)
            self.table_schema.list_display = self.list_display

        if self.slug is None:
            msg = f'Category table attribute {type(self).__name__}.slug must be set'
            raise Exception(msg)

    @property
    def has_retrieve(self):
        if not self.pk_name:
            return False

        fn = getattr(self, 'retrieve', None)
        return inspect.iscoroutinefunction(fn)

    @property
    def has_create(self):
        fn = getattr(self, 'create', None)
        return inspect.iscoroutinefunction(fn)

    @property
    def has_update(self):
        fn = getattr(self, 'update', None)
        return inspect.iscoroutinefunction(fn)

    def get_actions(self) -> Dict[str, Awaitable]:
        actions = {}
        for attribute_name in dir(self):
            if '__' in attribute_name:
                continue

            attribute = getattr(self, attribute_name)
            if inspect.iscoroutinefunction(attribute) and getattr(attribute, '__action__', False):
                actions[attribute.__name__] = attribute

        return actions

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
        for action_slug, action in self.get_actions().items():
            action = copy.copy(action.action_info)

            action['title'] = language_context.get_text(action.get('title'))
            action['description'] = language_context.get_text(action.get('description'))
            action['confirmation_text'] = language_context.get_text(action.get('confirmation_text'))

            form_schema = action['form_schema']
            if form_schema:
                try:
                    action['form_schema'] = form_schema.generate_schema(user, language_context)
                except Exception as e:
                    msg = f'Action {action_slug} form schema {form_schema} error: {e}'
                    raise Exception(msg) from e

            actions[action_slug] = action

        table.actions = actions
        schema.table_info = table
        return schema

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
        action_fn = self.get_actions().get(action)

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

            result: ActionResult = await action_fn(action_data=action_data)
        except AdminAPIException as e:
            raise e
        except Exception as e:
            logger.exception('Admin action %s "%s" exception: %s', type(self).__name__, action, e)
            msg = str(e) if admin_schema.debug else type(e).__name__
            raise AdminAPIException(
                APIError(message=msg, code='user_action_error'),
                status_code=500,
            ) from e

        return result

    def get_extra_autocomplete(self) -> dict:
        return {}

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
            data,
            user,
            extra=self.get_extra_autocomplete(),
        )

        return AutocompleteResult(results=results)

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
