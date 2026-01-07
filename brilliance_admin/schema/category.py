import abc
from typing import Any, ClassVar, Dict, List

from pydantic import Field
from pydantic.dataclasses import dataclass
from pydantic_core import core_schema

from brilliance_admin.auth import UserABC
from brilliance_admin.translations import LanguageManager, TranslateText
from brilliance_admin.utils import DataclassBase


# pylint: disable=too-many-instance-attributes
@dataclass
class FieldSchemaData(DataclassBase):
    type: str = None

    label: str | None = None
    help_text: str | None = None

    # Table header parameters
    header: dict = Field(default_factory=dict)

    read_only: bool = False
    default: Any | None = None
    required: bool = False

    max_length: int | None = None
    min_length: int | None = None

    choices: List[dict] | None = None

    tag_colors: dict | None = None
    variant: str | None = None
    size: str | None = None

    preview_max_height: int | None = None
    preview_max_width: int | None = None

    # StringField
    multilined: bool | None = None
    ckeditor: bool | None = None
    tinymce: bool | None = None

    # ArrayField
    array_type: str | None = None

    # SQLAlchemyRelatedField
    many: bool | None = None
    rel_name: str | None = None
    dual_list: bool | None = None

    # IntegerField
    inputmode: str | None = None
    precision: int | None = None
    scale: int | None = None

    # DateTimeField
    range: bool | None = None
    include_date: bool | None = None
    include_time: bool | None = None


@dataclass
class FieldsSchemaData(DataclassBase):
    fields: Dict[str, dict] = Field(default_factory=dict)
    list_display: List[str] = Field(default_factory=list)


# pylint: disable=too-many-instance-attributes
@dataclass
class TableInfoSchemaData(DataclassBase):
    table_schema: FieldsSchemaData

    search_enabled: bool = Field(default=False)
    search_help: str | None = Field(default=None)

    pk_name: str | None = Field(default=None)
    can_retrieve: bool = Field(default=False)

    can_create: bool = Field(default=False)
    can_update: bool = Field(default=False)

    table_filters: FieldsSchemaData | None = Field(default=None)

    ordering_fields: List[str] = Field(default_factory=list)
    default_ordering: str | None = None

    actions: Dict[str, dict] | None = Field(default_factory=dict)

    def __repr__(self):
        return f'<TableInfoSchemaData id={id(self)}>'


@dataclass
class GraphInfoSchemaData(DataclassBase):
    search_enabled: bool
    search_help: str | None

    table_filters: FieldsSchemaData | None = None


@dataclass
class CategorySchemaData(DataclassBase):
    title: str | None
    description: str | None
    icon: str | None
    type: str

    table_info: TableInfoSchemaData | None = None
    graph_info: GraphInfoSchemaData | None = None

    def __repr__(self):
        return f'<CategorySchemaData type={self.type} "{self.title}">'


class Category(abc.ABC):
    slug: ClassVar[str]
    title: ClassVar[str | TranslateText | None] = None
    description: ClassVar[str | TranslateText | None] = None

    # https://pictogrammers.com/library/mdi/
    icon: ClassVar[str | None] = None

    _type_slug: ClassVar[str]

    def generate_schema(self, user: UserABC, language_manager: LanguageManager) -> CategorySchemaData:
        return CategorySchemaData(
            title=language_manager.get_text(self.title) or self.slug,
            description=language_manager.get_text(self.description),
            icon=self.icon,
            type=self._type_slug,
        )

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: Any) -> core_schema.CoreSchema:
        def validate(v: Any) -> "Category":
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
