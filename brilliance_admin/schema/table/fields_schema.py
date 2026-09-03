import inspect
import json
from copy import deepcopy
from typing import Any, ClassVar, Dict, List

from pydantic import Field
from pydantic.dataclasses import dataclass
from pydantic_core import core_schema

from brilliance_admin.auth import UserABC
from brilliance_admin.exceptions import APIError, AdminAPIException, AsyncUnsafeTitleLoad, FieldError, ValidationError
from brilliance_admin.schema.category import FieldSchemaData, FieldsSchemaData
from brilliance_admin.schema.table.fields.base import TableField
from brilliance_admin.schema.table.fields.function_field import FunctionField
from brilliance_admin.schema.table.schema_type import SchemaType
from brilliance_admin.translations import DataclassBase, LanguageContext
from brilliance_admin.utils import DeserializeAction, SupportsStr

NOT_FUND_EXCEPTION = '''{class_name}: field "{field_slug}" not found inside generated fields
Available options: {available_fields}
'''
EXTRA_KWARGS_NOT_FUND = '''{class_name}.extra_kwargs field "{field_slug}" not found inside generated fields
Available options: {available_fields}
'''
LIST_DISPLAY_NOT_FUND = '''Field "{field_slug}" inside {class_name}.list_display, but not presented as field;
Available options: {available_fields}'''

FORMSET_MISSING_FIELDS = '''{class_name}.formset is invalid: missing fields.
Missing fields: {missing_fields};
Available fields: {available_fields}'''

FORMSET_EXTRA_FIELDS = '''{class_name}.formset is invalid: fields not found.
Unknown fields: {extra_fields};
Available fields: {available_fields}'''

FIELD_NOT_IN_FIELDS_LIST = (
    'Schema {class_name} attribute "{attribute_name}" {type_name}'
    ' presented, but not listed inside fields list: {fields}'
)
READONLY_FIELD_NOT_FOUND = (
    '{class_name} field "{field_slug}" from readonly_fields'
    ' is not found inside fields; available options: {fields}'
)


class DeserializeError(Exception):
    pass


@dataclass
class FormField(DataclassBase):
    title: SupportsStr | None = None
    col_span: int | None = None

    def __init__(self, *args, title=None, col_span=None, **kwargs):
        if args:
            title = args[0]

        self.title = title
        self.col_span = col_span


@dataclass
class FormSet(DataclassBase):
    title: SupportsStr | None = None
    description: SupportsStr | None = None
    fields: list = Field(default_factory=list)
    col_span: int | None = None

    def exclude_fields(self, exclude_fields: set[str]):
        next_fields = []

        for field in self.fields:
            if isinstance(field, FormSet):
                field.exclude_fields(exclude_fields)
                if field.fields:
                    next_fields.append(field)
                continue

            if isinstance(field, FormField):
                if field.title not in exclude_fields:
                    next_fields.append(field)
                continue

            if field not in exclude_fields:
                next_fields.append(field)

        self.fields = next_fields


# pylint: disable=too-many-instance-attributes
class FieldsSchema:
    # List of field slugs included in the schema.
    # Defines the complete set of fields and their order.
    # If not specified, auto-populated with all discovered TableField attributes.
    fields: List[str] | None = None

    # List of field slugs displayed as columns in the list page table.
    # Each slug must be present in fields.
    # If not specified, matches fields.
    list_display: List[str] | None = None

    # List of field slugs that will be marked as read_only = True.
    # These fields are displayed but excluded from deserialization
    # during create and update operations.
    readonly_fields: ClassVar[List | None] = None

    # List of field slugs to exclude from the schema.
    # Fields in this list will not be added even if they appear in fields.
    exclude_fields: List[str] | None = None

    # Dictionary for overriding attributes on already generated fields.
    # Key is the field slug, value is a dict of {attribute_name: value}.
    # Applied after field generation, allowing to change
    # read_only, label, required and other parameters without creating a custom field.
    #
    # Example:
    #   extra_kwargs = {
    #       'title': {'required': True, 'max_length': 100},
    #       'status': {'read_only': True},
    #   }
    extra_kwargs: Dict[str, dict] | None = None

    # Controls fields grid
    # All fields from fields must be listed
    formset: Any = None

    # Generated fields
    _generated_fields: dict = None

    # pylint: disable=too-many-branches
    # pylint: disable=too-many-locals
    def __init__(
            self,
            *args,
            table_schema=None,
            list_display=None,
            readonly_fields=None,
            fields=None,
            exclude_fields=None,
            extra_kwargs=None,
            formset=None,
            **kwargs,
    ):

        if fields:
            self.fields = fields

        if self.fields and not isinstance(self.fields, list):
            msg = f'{type(self).__name__}.fields must be a list instance; found: {self.fields}'
            raise AttributeError(msg)

        if table_schema:
            self.table_schema = table_schema

        if list_display:
            self.list_display = list_display

        if exclude_fields:
            self.exclude_fields = exclude_fields

        if extra_kwargs:
            self.extra_kwargs = extra_kwargs

        if readonly_fields:
            self.readonly_fields = readonly_fields

        if formset:
            if not isinstance(formset, FormSet):
                msg = f'{type(self).__name__}.formset must be a FormSet instance; found: {type(formset).__name__}'
                raise AttributeError(msg)
            self.formset = formset

        generated_fields = self.generate_fields(kwargs)

        available_fields = list(generated_fields.keys())
        if self.fields is None:
            self.fields = available_fields

        self._generated_fields = {}
        for field_slug in self.fields:
            if not isinstance(field_slug, str):
                msg = f'{type(self).__name__} field "{field_slug}" must be string'
                raise AttributeError(msg)

            if self.exclude_fields and field_slug in self.exclude_fields:
                continue

            if field_slug not in generated_fields:
                msg = NOT_FUND_EXCEPTION.format(
                    field_slug=field_slug,
                    available_fields=available_fields,
                    class_name=type(self).__name__,
                )
                raise AttributeError(msg)

            self._generated_fields[field_slug] = generated_fields[field_slug]

        for field_slug, kwargs_info in (self.extra_kwargs or {}).items():
            field = self._generated_fields.get(field_slug)
            if field is None:
                msg = EXTRA_KWARGS_NOT_FUND.format(
                    field_slug=field_slug,
                    available_fields=available_fields,
                    class_name=type(self).__name__,
                )
                raise AttributeError(msg)

            for attr_name, value in kwargs_info.items():
                setattr(field, attr_name, value)

        self.validate_fields(*args, **kwargs)

    def validate_fields(self, *args, **kwargs):
        if not self.fields:
            msg = f'Schema {type(self).__name__}.fields is empty'
            raise AttributeError(msg)

        # Check for fields not listed in self.fields
        for attribute_name in dir(self):
            if '__' in attribute_name:
                continue

            attribute = getattr(self, attribute_name)
            if issubclass(attribute.__class__, TableField) and attribute_name not in self.fields:
                msg = FIELD_NOT_IN_FIELDS_LIST.format(
                    class_name=type(self).__name__,
                    attribute_name=attribute_name,
                    type_name=type(attribute).__name__,
                    fields=self.fields,
                )
                raise AttributeError(msg)

        if self.readonly_fields:
            for field_slug in self.readonly_fields:
                field = self.get_field(field_slug)
                if not field:
                    msg = READONLY_FIELD_NOT_FOUND.format(
                        class_name=type(self).__name__,
                        field_slug=field_slug,
                        fields=self.fields,
                    )
                    raise AttributeError(msg)

                field.read_only = True

        # Fill list_display
        if self.list_display is None:
            self.list_display = self.fields

        for field_slug in self.list_display:
            if field_slug not in self.fields:
                msg = LIST_DISPLAY_NOT_FUND.format(
                    field_slug=field_slug,
                    available_fields=self.fields,
                    class_name=type(self).__name__,
                )
                raise AttributeError(msg)

        self.validate_formset()

    def validate_formset(self):
        if not self.formset:
            return

        formset_fields = self._collect_formset_fields(self.formset)
        available_fields = set(self.get_fields().keys())
        required_fields = {
            field_slug
            for field_slug, field in self.get_fields().items()
        }
        missing_fields = sorted(required_fields - formset_fields)
        extra_fields = sorted(formset_fields - available_fields)

        if missing_fields:
            msg = FORMSET_MISSING_FIELDS.format(
                class_name=type(self).__name__,
                missing_fields=json.dumps(missing_fields, ensure_ascii=False, indent=4),
                available_fields=json.dumps(list(available_fields), ensure_ascii=False, indent=4),
            )
            raise AttributeError(msg)

        if extra_fields:
            msg = FORMSET_EXTRA_FIELDS.format(
                class_name=type(self).__name__,
                extra_fields=json.dumps(extra_fields, ensure_ascii=False, indent=4),
                available_fields=json.dumps(list(available_fields), ensure_ascii=False, indent=4),
            )
            raise AttributeError(msg)

    def _collect_formset_fields(self, formset) -> set[str]:
        result = set()

        if formset is None:
            return result

        if isinstance(formset, str):
            result.add(formset)
            return result

        fields = getattr(formset, 'fields', None)

        if fields is None:
            return result

        for item in fields:
            if isinstance(item, str):
                result.add(item)
                continue

            if getattr(item, 'fields', None):
                result |= self._collect_formset_fields(item)
                continue

            slug = getattr(item, 'field', None) or getattr(item, 'slug', None) or getattr(item, 'title', None)
            if slug:
                result.add(slug)

        return result

    def generate_fields(self, kwargs) -> dict:
        generated_fields = {}

        # Fields from kwargs
        for k, v in kwargs.items():
            if issubclass(type(v), TableField) and not hasattr(self, k):
                generated_fields[k] = v

        # Autogenerate fields from instance attributes
        for attribute_name, attribute in type(self).__dict__.items():
            if '__' in attribute_name:
                continue

            attribute = getattr(self, attribute_name)
            if getattr(attribute, '__function_field__', False):
                field = FunctionField(fn=attribute, **attribute.__kwargs__)
                field.read_only = True
                generated_fields[attribute_name] = field
                continue

            attribute = getattr(self, attribute_name)
            if issubclass(type(attribute), TableField):
                generated_fields[attribute_name] = attribute
                continue

        return generated_fields

    def get_field(self, field_slug) -> TableField | None:
        return self.get_fields().get(field_slug)

    def get_fields(self) -> Dict[str, TableField]:
        return self._generated_fields

    def generate_form_schema(
            self,
            user: UserABC,
            language_context: LanguageContext,
            schema_type: SchemaType = SchemaType.TABLE,
            exclude_fields=None,
            admin_schema=None,
    ) -> FieldsSchemaData:
        exclude_fields = exclude_fields or []
        removed_fields = set()
        schema_list_display = [
            field_slug
            for field_slug in self.list_display
            if field_slug not in exclude_fields
        ]
        fields_schema_data = FieldsSchemaData(
            list_display=schema_list_display,
            formset=deepcopy(self.formset),
        )

        context = {'language_context': language_context}
        for field_slug, field in self.get_fields().items():
            if exclude_fields and field_slug in exclude_fields:
                removed_fields.add(field_slug)
                continue
            field_schema: FieldSchemaData = field.generate_field_schema(
                user,
                field_slug,
                fields_schema=self,
                admin_schema=admin_schema,
                language_context=language_context,
                schema_type=schema_type,
            )
            fields_schema_data.fields[field_slug] = field_schema.to_dict(keep_none=False, context=context)

        if removed_fields and fields_schema_data.formset:
            fields_schema_data.formset.exclude_fields(removed_fields)

        return fields_schema_data

    async def serialize(self, data: Any, extra: dict, field_slugs: list[str] | None = None) -> dict:
        result = {}
        slugs = field_slugs or list(self.get_fields().keys())
        for field_slug in slugs:
            field = self.get_field(field_slug)
            if field is None:
                msg = f'{type(self).__name__}: field "{field_slug}" not found for serialization'
                raise AttributeError(msg)
            value = data.get(field_slug)

            try:
                result[field_slug] = await field.serialize(value, extra, field_slug=field_slug)
            except FieldError as e:
                e.field_slug = field_slug
                raise e
            except AsyncUnsafeTitleLoad as e:
                parent_record = e.parent_record
                message = (
                    f'Async unsafe title load: field="{field_slug}" rel_name="{e.rel_name}" '
                    f'parent_model="{type(parent_record).__name__ if parent_record is not None else None}" '
                    f'parent_pk={getattr(parent_record, "pk", None)} '
                    f'model="{type(e.record).__name__}" pk={getattr(e.record, "pk", None)}. '
                    f'{e.hint}'
                    f'{e.source}'
                )
                raise AdminAPIException(
                    APIError(message=message, code='async_unsafe_title_load'),
                    status_code=500,
                ) from e

        return result

    async def deserialize_fields(self, data: dict, action: DeserializeAction, extra) -> dict:
        result = {}
        errors = {}
        for field_slug, field in self.get_fields().items():

            if field.read_only and action != DeserializeAction.FILTERS:
                continue

            # Skip update if fields is not presented in data
            if action in [DeserializeAction.UPDATE, DeserializeAction.FILTERS] and field_slug not in data:
                continue

            value = data.get(field_slug)
            try:
                deserialized_value = await field.deserialize_field(value, action, extra)
                if field.validator is not None:
                    deserialized_value = field.validator(deserialized_value)
                    if inspect.isawaitable(deserialized_value):
                        deserialized_value = await deserialized_value

                validate_method = getattr(self, f'validate_{field_slug}', None)
                if validate_method is not None and callable(validate_method):
                    if not inspect.iscoroutinefunction(validate_method):
                        msg = f'Validate method {type(self).__name__}.{field_slug} must be async'
                        raise AttributeError(msg)
                    deserialized_value = await validate_method(value)  # pylint: disable=not-callable

                field.set_deserialized_value(result, field_slug, deserialized_value, action, extra)
            except FieldError as e:
                errors[field_slug] = e

        if errors:
            raise ValidationError(data=errors)
        return result

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: Any) -> core_schema.CoreSchema:
        def validate(v: Any) -> "FieldsSchema":
            if isinstance(v, cls):
                return v
            raise TypeError(f"Expected {cls.__name__} instance")

        return core_schema.no_info_plain_validator_function(
            validate,
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda v: repr(v),
                info_arg=False,
                return_schema=core_schema.str_schema(),
            ),
        )
