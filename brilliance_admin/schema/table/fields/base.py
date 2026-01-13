import abc
import datetime
from enum import Enum
from typing import Any, ClassVar

from pydantic.dataclasses import dataclass

from brilliance_admin.exceptions import FieldError
from brilliance_admin.schema.category import FieldSchemaData
from brilliance_admin.translations import LanguageContext
from brilliance_admin.translations import TranslateText as _
from brilliance_admin.utils import DeserializeAction, SupportsStr, humanize_field_name


@dataclass
class TableField(abc.ABC, FieldSchemaData):
    _type: ClassVar[str]

    label: SupportsStr | None = None
    help_text: SupportsStr | None = None

    def generate_schema(self, user, field_slug, language_context: LanguageContext) -> FieldSchemaData:
        schema = FieldSchemaData(
            type=self._type,
            label=language_context.get_text(self.label) or humanize_field_name(field_slug),
            help_text=language_context.get_text(self.help_text),
            header=self.header,
            read_only=self.read_only,
            default=self.default,
            required=self.required,
        )

        return schema

    async def serialize(self, value, extra: dict, *args, **kwargs) -> Any:
        return value

    async def deserialize(self, value, action: DeserializeAction, extra: dict, *args, **kwargs) -> Any:
        if self.required and value is None:
            raise FieldError('Field is required', 'field_required')

        return value

    async def autocomplete(self, model, data, user):
        raise NotImplementedError('autocomplete is not implemented')

    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-positional-arguments
    def set_deserialized_value(self, result: dict, field_slug, deserialized_value, action, extra):
        result[field_slug] = deserialized_value


@dataclass
class IntegerField(TableField):
    _type = 'integer'

    choices: Any | None = None

    max_value: int | None = None
    min_value: int | None = None

    inputmode: str | None = None
    precision: int | None = None
    scale: int | None = None

    def generate_schema(self, user, field_slug, language_context: LanguageContext) -> FieldSchemaData:
        schema = super().generate_schema(user, field_slug, language_context)

        if self.max_value is not None:
            schema.max_value = self.max_value

        if self.min_value is not None:
            schema.min_value = self.min_value

        schema.inputmode = self.inputmode
        schema.precision = self.precision
        schema.scale = self.scale

        return schema

    async def deserialize(self, value, action: DeserializeAction, extra: dict, *args, **kwargs) -> Any:
        value = await super().deserialize(value, action, extra, *args, **kwargs)
        if value and not isinstance(value, int):
            raise FieldError(_('errors.bad_type_error') % {'type': type(value), 'expected': 'init'})

        return value


@dataclass
class StringField(TableField):
    _type = 'string'

    multilined: bool | None = None
    ckeditor: bool | None = None
    tinymce: bool | None = None

    min_length: int | None = None
    max_length: int | None = None

    choices: Any | None = None

    def generate_schema(self, user, field_slug, language_context: LanguageContext) -> FieldSchemaData:
        schema = super().generate_schema(user, field_slug, language_context)

        schema.multilined = self.multilined
        schema.ckeditor = self.ckeditor
        schema.tinymce = self.tinymce

        if self.min_length is not None:
            schema.min_length = self.min_length

        if self.max_length is not None:
            schema.max_length = self.max_length

        return schema

    async def deserialize(self, value, action: DeserializeAction, extra: dict, *args, **kwargs) -> Any:
        value = await super().deserialize(value, action, extra, *args, **kwargs)
        if value and not isinstance(value, str):
            raise FieldError(_('errors.bad_type_error') % {'type': type(value), 'expected': 'string'})

        return value


@dataclass
class BooleanField(TableField):
    _type = 'boolean'


@dataclass
class DateTimeField(TableField):
    _type = 'datetime'

    format: str = '%Y-%m-%dT%H:%M:%S'
    range: bool | None = None
    include_date: bool | None = True
    include_time: bool | None = True

    def generate_schema(self, user, field_slug, language_context: LanguageContext) -> FieldSchemaData:
        schema = super().generate_schema(user, field_slug, language_context)

        schema.range = self.range
        schema.include_date = self.include_date
        schema.include_time = self.include_time

        return schema

    async def deserialize(self, value, action: DeserializeAction, extra: dict, *args, **kwargs) -> Any:
        value = await super().deserialize(value, action, extra, *args, **kwargs)

        if not value:
            return

        if value and not isinstance(value, (str, dict)):
            raise FieldError(_('errors.bad_type_error') % {'type': type(value), 'expected': 'datetime'})

        if isinstance(value, str):
            return datetime.datetime.strptime(value, self.format)

        if isinstance(value, dict):
            if not value.get('from') or not value.get('to'):
                msg = f'{type(self).__name__} value must be dict with from,to values: {value}'
                raise FieldError(msg)

            return {
                'from': datetime.datetime.strptime(value.get('from'), self.format),
                'to': datetime.datetime.strptime(value.get('to'), self.format),
            }

        raise FieldError(_('errors.bad_type_error') % {'type': type(value), 'expected': 'datetime'})


@dataclass
class JSONField(TableField):
    _type = 'json'

    async def deserialize(self, value, action: DeserializeAction, extra: dict, *args, **kwargs) -> Any:
        value = await super().deserialize(value, action, extra, *args, **kwargs)

        if value is None:
            return

        if not isinstance(value, (dict, list)):
            raise FieldError(_('errors.bad_type_error') % {'type': type(value), 'expected': 'JSON'})

        return value


@dataclass
class ArrayField(TableField):
    _type = 'array'

    array_type: str | None

    def generate_schema(self, user, field_slug, language_context: LanguageContext) -> FieldSchemaData:
        schema = super().generate_schema(user, field_slug, language_context)

        schema.array_type = self.array_type

        return schema

    async def deserialize(self, value, action: DeserializeAction, extra: dict, *args, **kwargs) -> Any:
        value = await super().deserialize(value, action, extra, *args, **kwargs)

        if value is None:
            return

        if not isinstance(value, list):
            raise FieldError(_('errors.bad_type_error') % {'type': type(value), 'expected': 'Array'})

        return value


@dataclass
class FileField(TableField):
    _type = 'file'


@dataclass
class ImageField(TableField):
    _type = 'image'

    preview_max_height: int = 100
    preview_max_width: int = 100

    def generate_schema(self, user, field_slug, language_context: LanguageContext) -> FieldSchemaData:
        schema = super().generate_schema(user, field_slug, language_context)

        if self.preview_max_height is not None:
            schema.preview_max_height = self.preview_max_height

        if self.preview_max_width is not None:
            schema.preview_max_width = self.preview_max_width

        return schema

    async def serialize(self, value, extra: dict, *args, **kwargs) -> Any:
        return {'url': value}


@dataclass
class ChoiceField(TableField):
    _type = 'choice'

    # Tag color available:
    # https://vuetifyjs.com/en/styles/colors/#classes
    choices: Any | None = None

    # https://vuetifyjs.com/en/components/chips/#color-and-variants
    variant: str = 'elevated'
    size: str = 'default'

    def __post_init__(self):
        self.choices = self.generate_choices()

    def generate_choices(self):
        if not self.choices:
            return None

        if issubclass(self.choices, Enum):
            return [
                {'value': c.value, 'title': c.label, 'tag_color': getattr(c, 'tag_color', None)}
                for c in self.choices
            ]

        msg = f'Field choices is not suppored: {self.choices}'
        raise NotImplementedError(msg)

    def find_choice(self, value):
        if not self.choices:
            return None

        return next((c for c in self.choices if c.get('value') == value), None)

    def generate_schema(self, user, field_slug, language_context: LanguageContext) -> FieldSchemaData:
        schema = super().generate_schema(user, field_slug, language_context)

        schema.choices = self.choices

        schema.size = self.size
        schema.variant = self.variant

        return schema

    async def serialize(self, value, extra: dict, *args, **kwargs) -> Any:
        if not value:
            return

        choice = self.find_choice(value)
        return {
            'value': value,
            'title': choice.get('title') or value if choice else value.capitalize(),
        }
