import functools
import inspect
from typing import Any

from pydantic.dataclasses import dataclass

from brilliance_admin.exceptions import AdminAPIException, APIError
from brilliance_admin.schema.table.fields.base import StringField, TableField
from brilliance_admin.schema.table.schema_type import SchemaType
from brilliance_admin.translations import LanguageContext
from brilliance_admin.utils import get_logger

logger = get_logger()


def function_field(**kwargs):
    '''
    The same as decaring:
    field = FunctionField(fn=attribute)

    but available directly and converted after to the FunctionField
    '''
    def wrapper(func):
        func.__function_field__ = True

        field_type = kwargs.pop('type', StringField)
        if isinstance(field_type, TableField):
            if kwargs:
                msg = (
                    f'function_field "{func.__name__}" kwargs cannot be used when type is a field instance: '
                    f'{list(kwargs.keys())}'
                )
                raise TypeError(msg)
            field = field_type
        elif inspect.isclass(field_type) and issubclass(field_type, TableField):
            field = field_type(**kwargs)
        else:
            msg = f'function_field type must be TableField subclass or instance, got {field_type}'
            raise TypeError(msg)

        func.__kwargs__ = {'field': field}

        @functools.wraps(func)
        async def wrapped(*args, **kwargs):
            return await func(*args, **kwargs)

        return wrapped

    return wrapper


@dataclass
class FunctionField(TableField):
    _type: str = 'function_field'
    read_only = True

    fn: Any = None
    field: TableField | None = None

    def __post_init__(self):
        if not inspect.iscoroutinefunction(self.fn):
            msg = f'{type(self).__name__}.fn {self.fn} must be coroutine function'
            raise AttributeError(msg)

        if self.field is None:
            self.field = StringField()

        self.field.read_only = True

    def generate_field_schema(
        self,
        user,
        field_slug,
        language_context: LanguageContext,
        schema_type: SchemaType = SchemaType.TABLE,
    ):
        return self.field.generate_field_schema(user, field_slug, language_context, schema_type)

    async def serialize(self, value, extra: dict, *args, **kwargs) -> Any:
        try:
            return await self.fn(**extra)
        except Exception as e:
            logger.exception(
                'Function field %s label=%s error from function="%s": %s',
                type(self).__name__,
                self.label,
                self.fn,
                e,
            )
            debug = extra.get('debug', False)
            msg = str(e) if debug else type(e).__name__
            raise AdminAPIException(
                APIError(message=f'Error: {msg}', code='function_field_error'), status_code=400,
            ) from e
