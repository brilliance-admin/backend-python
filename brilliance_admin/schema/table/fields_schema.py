import asyncio
from typing import Any, ClassVar, Dict, List

from pydantic_core import core_schema

from brilliance_admin.auth import UserABC
from brilliance_admin.exceptions import AdminAPIException, APIError, FieldError
from brilliance_admin.schema.category import FieldSchemaData, FieldsSchemaData
from brilliance_admin.schema.table.fields.base import TableField
from brilliance_admin.schema.table.fields.function_field import FunctionField
from brilliance_admin.translations import LanguageContext
from brilliance_admin.utils import DeserializeAction

NOT_FUND_EXCEPTION = '''Field slug "{field_slug}" not found inside generated fields inside {class_name}
Available options: {available_fields}
'''


class DeserializeError(Exception):
    pass


class FieldsSchema:
    # Список полей
    fields: List[str] | None = None

    # Список колонок, которые будут отображаться в таблице
    list_display: List[str] | None = None

    # Для передачи параметра read_only = True внутрь поля
    readonly_fields: ClassVar[List | None] = None

    # Generated fields
    _generated_fields: dict = None

    def __init__(self, *args, table_schema=None, list_display=None, readonly_fields=None, fields=None, **kwargs):
        if fields:
            self.fields = fields

        if self.fields and not isinstance(self.fields, list):
            msg = f'{type(self).__name__}.fields must be a list instance; found: {self.fields}'
            raise AttributeError(msg)

        if table_schema:
            self.table_schema = table_schema

        if list_display:
            self.list_display = list_display

        if readonly_fields:
            self.readonly_fields = readonly_fields

        generated_fields = self.generate_fields(kwargs)

        available_fields = list(generated_fields.keys())
        if self.fields is None:
            self.fields = available_fields

        self._generated_fields = {}
        for field_slug in self.fields:
            if not isinstance(field_slug, str):
                msg = f'{type(self).__name__} field "{field_slug}" must be string'
                raise AttributeError(msg)

            if field_slug not in generated_fields:
                msg = NOT_FUND_EXCEPTION.format(
                    field_slug=field_slug,
                    available_fields=available_fields,
                    class_name=type(self).__name__,
                )
                raise AttributeError(msg)

            self._generated_fields[field_slug] = generated_fields[field_slug]

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
                msg = f'Schema {type(self).__name__} attribute "{attribute_name}" {type(attribute).__name__} presented, but not listed inside fields list: {self.fields}'
                raise AttributeError(msg)

        if self.readonly_fields:
            for field_slug in self.readonly_fields:
                field = self.get_field(field_slug)
                if not field:
                    msg = f'{type(self).__name__} field "{field_slug}" from readonly_fields is not found inside fields; available options: {self.fields}'
                    raise AttributeError(msg)

                field.read_only = True

        # Fill list_display
        if self.list_display is None:
            self.list_display = self.fields

        for field_slug in self.list_display:
            if field_slug not in self.fields:
                msg = f'Field "{field_slug}" inside {type(self).__name__}.list_display, but not presented as field; available options: {self.fields}'
                raise AttributeError(msg)

    def generate_fields(self, kwargs) -> dict:
        generated_fields = {}

        # Fields from kwargs
        for k, v in kwargs.items():
            if issubclass(type(v), TableField) and not hasattr(self, k):
                generated_fields[k] = v

        # Autogenerate fields from instance attributes
        for attribute_name in dir(self):
            if '__' in attribute_name:
                continue

            attribute = getattr(self, attribute_name)
            if issubclass(type(attribute), TableField):
                generated_fields[attribute_name] = attribute

        # Generation FunctionField
        for attribute_name in dir(self):
            if '__' in attribute_name:
                continue

            attribute = getattr(self, attribute_name)
            if getattr(attribute, '__function_field__', False):
                field = FunctionField(fn=attribute, **attribute.__kwargs__)
                field.read_only = True
                generated_fields[attribute_name] = field

        return generated_fields

    def get_field(self, field_slug) -> TableField | None:
        return self.get_fields().get(field_slug)

    def get_fields(self) -> Dict[str, TableField]:
        return self._generated_fields

    def generate_schema(self, user: UserABC, language_context: LanguageContext) -> FieldsSchemaData:
        fields_schema = FieldsSchemaData(
            list_display=self.list_display,
        )

        context = {'language_context': language_context}
        for field_slug, field in self.get_fields().items():
            field_schema: FieldSchemaData = field.generate_schema(user, field_slug, language_context)
            fields_schema.fields[field_slug] = field_schema.to_dict(keep_none=False, context=context)

        return fields_schema

    async def serialize(self, data: Any, extra: dict) -> dict:
        result = {}
        for field_slug, field in self.get_fields().items():
            value = data.get(field_slug)

            try:
                result[field_slug] = await field.serialize(value, extra)
            except FieldError as e:
                e.field_slug = field_slug
                raise e

        return result

    async def deserialize(self, data: dict, action: DeserializeAction, extra) -> dict:
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
                deserialized_value = await field.deserialize(value, action, extra)

                validate_method = getattr(self, f'validate_{field_slug}', None)
                if callable(validate_method):
                    if not asyncio.iscoroutinefunction(validate_method):
                        msg = f'Validate method {type(self).__name__}.{field_slug} must be async'
                        raise AttributeError(msg)
                    deserialized_value = await validate_method(value)

                field.set_deserialized_value(result, field_slug, deserialized_value, action, extra)
            except FieldError as e:
                errors[field_slug] = e

        if errors:
            raise AdminAPIException(
                APIError(
                    message='Validation error',
                    code='validation_error',
                    field_errors=errors,
                ),
                status_code=400,
            )
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
