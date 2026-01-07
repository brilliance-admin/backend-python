import functools
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validate_call
from pydantic.dataclasses import dataclass

from brilliance_admin.schema.table.fields_schema import FieldsSchema
from brilliance_admin.translations import DataclassBase
from brilliance_admin.utils import SupportsStr


class ActionData(BaseModel):
    pks: List[Any] = Field(default_factory=list)
    form_data: dict = Field(default_factory=dict)

    search: str | None = None
    filters: Dict[str, Any] = Field(default_factory=dict)

    send_to_all: bool = False


@dataclass
class ActionMessage(DataclassBase):
    text: SupportsStr
    type: str = 'success'
    position: str = 'top-center'


@dataclass
class ActionResult(DataclassBase):
    message: ActionMessage | None = None
    persistent_message: SupportsStr | None = None


# pylint: disable=too-many-arguments
# pylint: disable=too-many-positional-arguments
@validate_call
def admin_action(
    title: SupportsStr,
    description: Optional[SupportsStr] = None,
    confirmation_text: Optional[SupportsStr] = None,

    # https://vuetifyjs.com/en/styles/colors/#material-colors
    base_color: Optional[str] = None,

    # https://pictogrammers.com/library/mdi/
    icon: Optional[str] = None,

    # elevated, flat, tonal, outlined, text, and plain.
    variant: Optional[str] = None,

    allow_empty_selection: bool = False,
    form_schema: Optional[FieldsSchema] = None,
):
    def wrapper(func):
        func.__action__ = True

        func.action_info = {
            'title': title,
            'description': description,
            'confirmation_text': confirmation_text,

            'icon': icon,
            'base_color': base_color,
            'variant': variant,

            'allow_empty_selection': allow_empty_selection,
            'form_schema': form_schema,
        }

        @functools.wraps(func)
        async def wrapped(*args):
            return await func(*args)

        return wrapped

    return wrapper
