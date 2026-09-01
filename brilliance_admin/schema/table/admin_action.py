import functools
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validate_call
from pydantic.dataclasses import dataclass

from brilliance_admin.auth import UserABC
from brilliance_admin.schema.table.fields_schema import FieldsSchema
from brilliance_admin.translations import DataclassBase
from brilliance_admin.utils import SupportsStr, humanize_field_name


class ActionData(BaseModel):
    pks: List[Any] = Field(default_factory=list)
    form_data: dict = Field(default_factory=dict)
    user: UserABC | None = Field(default=None, exclude=True)

    search: str | None = None
    filters: Dict[str, Any] = Field(default_factory=dict)

    send_to_all: bool = False

    group_slug: str | None = Field(default=None, exclude=True)
    category_slug: str | None = Field(default=None, exclude=True)
    subcategory_slug: str | None = Field(default=None, exclude=True)


@dataclass
class ActionMessage(DataclassBase):
    text: SupportsStr
    type: str = 'success'
    position: str = 'top-center'


@dataclass
class ActionFileResult(DataclassBase):
    content: bytes
    filename: str
    content_type: str


@dataclass
class ActionResult(DataclassBase):
    message: ActionMessage | SupportsStr | None = None
    persistent_message: SupportsStr | None = None
    download_file: ActionFileResult | None = None

    def __init__(
        self,
        message: ActionMessage | SupportsStr | None = None,
        persistent_message: SupportsStr | None = None,
        download_file: ActionFileResult | None = None,
    ):
        if isinstance(message, (str, SupportsStr)) and not isinstance(message, ActionMessage):
            self.message = ActionMessage(text=message)
        else:
            self.message = message
        self.persistent_message = persistent_message
        self.download_file = download_file


# pylint: disable=too-many-arguments
# pylint: disable=too-many-positional-arguments
@validate_call
def admin_action(
    title: SupportsStr | None = None,
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
            'title': title or humanize_field_name(func.__name__),
            'description': description,
            'confirmation_text': confirmation_text,

            'icon': icon,
            'base_color': base_color,
            'variant': variant,

            'allow_empty_selection': allow_empty_selection,
            'form_schema': form_schema,
        }

        @functools.wraps(func)
        async def wrapped(*args, **kwargs):
            return await func(*args, **kwargs)

        return wrapped

    return wrapper
