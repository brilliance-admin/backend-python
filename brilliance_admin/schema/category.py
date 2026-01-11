import abc
from typing import Any, ClassVar, Dict, List

from pydantic import Field
from pydantic.dataclasses import dataclass
from pydantic_core import core_schema
from structlog import get_logger

from brilliance_admin.auth import UserABC
from brilliance_admin.translations import LanguageContext
from brilliance_admin.utils import DataclassBase, KwargsInitMixin, SupportsStr, humanize_field_name

logger = get_logger()


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

    categories: dict = Field(default_factory=dict)

    table_info: TableInfoSchemaData | None = None
    graph_info: GraphInfoSchemaData | None = None

    link: str | None = None

    def __repr__(self):
        return f'<CategorySchemaData type={self.type} "{self.title}">'


class BaseCategory(KwargsInitMixin, abc.ABC):
    slug: str
    title: SupportsStr | None = None
    description: SupportsStr | None = None

    # https://pictogrammers.com/library/mdi/
    icon: str | None = None

    _type_slug: ClassVar[str]

    def generate_schema(self, user: UserABC, language_context: LanguageContext) -> CategorySchemaData:
        type_slug = getattr(type(self), '_type_slug', None)
        if not type_slug:
            msg = f'{type(self).__name__}._type_slug must be set!'
            raise AttributeError(msg)

        result = CategorySchemaData(
            title=language_context.get_text(self.title) or humanize_field_name(self.slug),
            description=language_context.get_text(self.description),
            icon=self.icon,
            type=type_slug,
        )
        return result

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        if cls is BaseCategory:
            return

        if not issubclass(cls, BaseCategory):
            raise TypeError(f'{cls.__name__} must inherit from Category')

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: Any) -> core_schema.CoreSchema:
        def validate(v: Any) -> "BaseCategory":
            if isinstance(v, cls):
                return v
            raise TypeError(f"Expected {cls.__name__} instance, recieved: {type(v)} {v}")

        return core_schema.no_info_plain_validator_function(
            validate,
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda v: repr(v),
                info_arg=False,
                return_schema=core_schema.str_schema(),
            ),
        )


class CategoryLink(BaseCategory):
    _type_slug: str = 'link'

    link: str

    def generate_schema(self, user: UserABC, language_context: LanguageContext) -> CategorySchemaData:
        result = super().generate_schema(user, language_context)
        result.link = self.link
        return result


class CategoryGroup(BaseCategory):
    _type_slug: str = 'group'

    subcategories: list = Field(default_factory=list)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for category in self.subcategories:
            if not isinstance(category, BaseCategory):
                raise TypeError(f'Category "{category}" is not instance of BaseCategory subclass')

    def generate_schema(self, user: UserABC, language_context: LanguageContext) -> CategorySchemaData:
        result = super().generate_schema(user, language_context)

        for category in self.subcategories:

            if not category.slug:
                msg = f'Category {type(category).__name__}.slug is empty'
                raise AttributeError(msg)

            if category.slug in result.categories:
                exists = result.categories[category.slug]
                msg = f'Category {type(category).__name__}.slug "{self.slug}" already registered by "{exists.title}"'
                raise KeyError(msg)

            try:
                result.categories[category.slug] = category.generate_schema(user, language_context)
            except Exception as e:
                msg = f'Category "{category.slug}" {type(category)} generate_schema error: {e}'
                raise Exception(msg) from e

        return result

    def get_category(self, category_slug: str):
        for category in self.subcategories:
            if category.slug == category_slug:
                return category

        return None
