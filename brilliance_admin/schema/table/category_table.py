import abc
import copy
import inspect
from typing import Any, Awaitable, Dict, List

from fastapi import HTTPException, Request
from pydantic import Field

from brilliance_admin.auth import UserABC
from brilliance_admin.exceptions import AdminAPIException, APIError, ValidationError
from brilliance_admin.schema.category import BaseCategory, TableInfoSchemaData
from brilliance_admin.schema.table.admin_action import ActionData, ActionResult
from brilliance_admin.schema.table.fields.base import InlineField
from brilliance_admin.schema.table.fields_schema import FieldsSchema
from brilliance_admin.schema.table.schema_type import SchemaType
from brilliance_admin.schema.table.table_models import AutocompleteData, AutocompleteResult, ListData, TableListResult
from brilliance_admin.translations import LanguageContext
from brilliance_admin.utils import DeserializeAction, SupportsStr, get_logger

logger = get_logger()


class CategoryTable(BaseCategory):
    _type_slug: str = 'table'

    # Instances of categories
    subcategories: List[Any] = Field(default_factory=list)

    search_enabled: bool = False
    search_help: SupportsStr | None = None

    table_schema: FieldsSchema = None
    table_filters: FieldsSchema | None = None

    list_display: List[str] | None = None

    ordering_fields: List[str] = Field(default_factory=list)
    default_ordering: str | None = None

    pk_name: str | None = None

    def __init__(self, *args, table_schema=None, table_filters=None, subcategories=None, **kwargs):
        super().__init__(*args, **kwargs)

        if subcategories:
            if self.subcategories:
                msg = (
                    f'{type(self).__name__} already has default subcategories; '
                    'passing subcategories to __init__ would overwrite them'
                )
                raise ValueError(msg)
            self.subcategories = subcategories

        for category in self.subcategories:
            if not issubclass(category.__class__, BaseCategory):
                raise TypeError(f'{type(self).__name__} subcategory "{category}" is not subclass of BaseCategory')

        if table_schema:
            self.table_schema = table_schema

        if table_filters:
            self.table_filters = table_filters

        if self.list_display and self.table_schema:
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
        for cls in reversed(type(self).mro()):
            for attribute_name, attribute in cls.__dict__.items():
                if '__' in attribute_name:
                    continue

                bound_attribute = getattr(self, attribute_name, None)
                if inspect.iscoroutinefunction(bound_attribute) and getattr(bound_attribute, '__action__', False):
                    actions[attribute_name] = bound_attribute

        return actions

    def get_subcategory(self, subcategory: str):
        for category in self.subcategories:
            if category.slug == subcategory:
                return category
        return None

    def _get_form_schema(self, user, language_context: LanguageContext, parent_category=None):
        return self.table_schema.generate_form_schema(
            user,
            language_context,
            schema_type=SchemaType.TABLE,
        )

    def generate_category_schema(self, user, language_context: LanguageContext, parent_category=None) -> dict:
        schema = super().generate_category_schema(user, language_context, parent_category)

        table_schema = getattr(self, 'table_schema', None)
        if not table_schema or not issubclass(table_schema.__class__, FieldsSchema):
            msg = f'Admin category {type(self).__name__} must have table_schema instance of FieldsSchema'
            raise AttributeError(msg)

        table = TableInfoSchemaData(
            table_schema=self._get_form_schema(user, language_context, parent_category),
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
            table.table_filters = self.table_filters.generate_form_schema(
                user,
                language_context,
                schema_type=SchemaType.FILTERS,
            )

        actions = {}
        for action_slug, action in self.get_actions().items():
            action = copy.copy(action.action_info)

            action['title'] = language_context.get_text(action.get('title'))
            action['description'] = language_context.get_text(action.get('description'))
            action['confirmation_text'] = language_context.get_text(action.get('confirmation_text'))

            form_schema = action['form_schema']
            if form_schema:
                try:
                    action['form_schema'] = form_schema.generate_form_schema(
                        user,
                        language_context,
                        schema_type=SchemaType.ACTION,
                    )
                except Exception as e:
                    msg = f'Action {action_slug} form schema {form_schema} error: {e}'
                    raise Exception(msg) from e

            actions[action_slug] = action

        table.actions = actions
        schema.table_info = table

        # Подвкладки subtab
        for category in self.subcategories:
            if not category.slug:
                msg = f'{type(self).__name__}.slug subcategory {type(category).__name__}.slug is empty'
                raise AttributeError(msg)

            category_schema = category.generate_category_schema(user, language_context, parent_category=self)
            table.subcategories[category.slug] = category_schema.to_dict(keep_none=False)

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
            debug: bool,
            parent_category: BaseCategory | None = None,
            parent_pk: Any | None = None,
    ) -> ActionResult:
        action_fn = self.get_actions().get(action)

        if action_fn is None:
            raise HTTPException(status_code=404, detail=f'Action "{action}" is not found')

        try:
            form_schema = action_fn.action_info['form_schema']
            if form_schema:
                deserialized_data = await form_schema.deserialize_fields(
                    action_data.form_data,
                    action=DeserializeAction.TABLE_ACTION,
                    extra={'user': user, 'request': request}
                )
                action_data.form_data = deserialized_data

            action_data.user = user
            result: ActionResult | None = await action_fn(action_data=action_data, user=user)
            if result is None:
                result = ActionResult()

        except ValidationError as e:
            raise AdminAPIException(
                APIError(
                    code='validation_error',
                    field_errors=e.data,
                ),
                status_code=400,
            ) from e

        except AdminAPIException:
            raise

        except Exception as e:
            logger.exception('Admin action %s "%s" exception: %s', type(self).__name__, action, e)
            msg = str(e) if debug else type(e).__name__
            raise AdminAPIException(
                APIError(message=msg, code='user_action_error'),
                status_code=500,
            ) from e

        return result

    def get_extra_autocomplete(self, data: AutocompleteData) -> dict:
        return {}

    async def autocomplete(
            self,
            data: AutocompleteData,
            user: UserABC,
            language_context: LanguageContext,
            debug: bool,
            parent_category: BaseCategory | None = None,
            parent_pk: Any | None = None,
    ) -> AutocompleteResult:
        form_schema = None

        if data.action_name is not None:
            action_fn = self._get_action_fn(data.action_name)
            if not action_fn:
                msg = f'Autocomplete: action "{data.action_name}" is not found'
                raise AdminAPIException(APIError(message=msg), status_code=500)

            if not action_fn.form_schema:
                msg = f'Autocomplete: action "{data.action_name}" form_schema is None'
                raise AdminAPIException(APIError(message=msg), status_code=500)

            form_schema = action_fn.form_schema

        elif data.is_filter:
            if not self.table_filters:
                msg = f'Autocomplete: action "{data.action_name}" table_filters is None'
                raise AdminAPIException(APIError(message=msg), status_code=500)

            form_schema = self.table_filters

        else:
            form_schema = self.table_schema

        # Inline fields
        if data.inline_field_slug:
            inline_field = form_schema.get_field(data.inline_field_slug)
            if not inline_field:
                msg = (
                    f'Autocomplete: inline field "{data.inline_field_slug}" '
                    f'is not found inside {type(form_schema).__name__}'
                )
                raise AdminAPIException(APIError(message=msg), status_code=500)

            if not issubclass(type(inline_field), InlineField):
                msg = (
                    f'Autocomplete: inline field "{data.inline_field_slug}" '
                    f'is not subclass of InlineField: {type(inline_field).__name__}'
                )
                raise AdminAPIException(APIError(message=msg), status_code=500)

            form_schema = inline_field.table_schema

        field = form_schema.get_field(data.field_slug)
        if not field:
            msg = f'Autocomplete: field "{data.field_slug}" is not found inside {type(form_schema).__name__}'
            raise AdminAPIException(APIError(message=msg), status_code=500)

        results = await field.autocomplete(
            data,
            user,
            extra=self.get_extra_autocomplete(data),
            parent_category=parent_category,
            parent_pk=parent_pk if parent_pk is not None else data.parent_pk,
            debug=debug,
        )

        total_count_fn = getattr(field, 'autocomplete_total_count', None)
        if total_count_fn is None:
            total_count = len(results)
        else:
            total_count = await total_count_fn(
                data,
                user,
                extra=self.get_extra_autocomplete(data),
                parent_category=parent_category,
                parent_pk=parent_pk if parent_pk is not None else data.parent_pk,
            )

        return AutocompleteResult(results=results, total_count=total_count)

    # pylint: disable=too-many-arguments
    @abc.abstractmethod
    async def get_list(
            self,
            list_data: ListData,
            user: UserABC,
            language_context: LanguageContext,
            debug: bool,
            parent_category: BaseCategory | None = None,
            parent_pk: Any | None = None,
    ) -> TableListResult:
        raise NotImplementedError()

#     async def retrieve(
#             self, pk: Any, user: UserABC,
#             language_context: LanguageContext, debug: bool,
#     ) -> RetrieveResult:
#        raise NotImplementedError()

#    async def create(
#            self, data: dict, user: UserABC,
#            language_context: LanguageContext, debug: bool,
#    ) -> CreateResult:
#        raise NotImplementedError()

#    async def update(
#            self, pk: Any, data: dict, user: UserABC,
#            language_context: LanguageContext, debug: bool,
#    ) -> UpdateResult:
#        raise NotImplementedError()
