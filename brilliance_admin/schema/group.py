import abc
from typing import Dict, List

from pydantic.dataclasses import dataclass

from brilliance_admin.auth import UserABC
from brilliance_admin.schema.category import Category, CategorySchemaData
from brilliance_admin.translations import LanguageContext
from brilliance_admin.utils import DataclassBase, SupportsStr, get_logger

logger = get_logger()


@dataclass
class GroupSchemaData(DataclassBase):
    title: str | None
    description: str | None
    icon: str | None
    categories: Dict[str, CategorySchemaData]


@dataclass
class Group(abc.ABC):
    categories: List[Category]
    slug: str
    title: SupportsStr | None = None
    description: SupportsStr | None = None

    # https://pictogrammers.com/library/mdi/
    icon: str | None = None

    def __post_init__(self):
        for category in self.categories:
            if not issubclass(category.__class__, Category):
                raise TypeError(f'Category "{category}" is not instance of Category subclass')

    def generate_schema(self, user: UserABC, language_context: LanguageContext) -> GroupSchemaData:
        result = GroupSchemaData(
            title=language_context.get_text(self.title) or self.slug,
            description=language_context.get_text(self.description),
            icon=self.icon,
            categories={},
        )
        if not self.categories:
            logger.warning('Group "%s" %s.categories is empty!', self.slug, type(self).__name__)

        for category in self.categories:

            if not category.slug:
                msg = f'Category {type(category).__name__}.slug is empty'
                raise AttributeError(msg)

            if category.slug in result.categories:
                exists = result.categories[category.slug]
                msg = f'Category {type(category).__name__}.slug "{self.slug}" already registered by "{exists.title}"'
                raise KeyError(msg)

            result.categories[category.slug] = category.generate_schema(user, language_context)

        return result

    def get_category(self, category_slug: str) -> Category | None:
        for category in self.categories:
            if category.slug == category_slug:
                return category

        return None
