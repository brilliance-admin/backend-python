import abc

from pydantic_core import core_schema

from brilliance_admin.permissions.settings import PermissionsData
from brilliance_admin.schema.table.table_action import TableAction


class PermissionsContainer(abc.ABC):

    def __init__(self, user_or_group):
        self.user_or_group = user_or_group

    @abc.abstractmethod
    def get_permissions_data(self) -> PermissionsData:
        """Return stored permission settings for the editing form."""
        raise NotImplementedError()

    @abc.abstractmethod
    def has_action_permission(
            self,
            # None for a root category outside a CategoryGroup.
            group: str | None,
            category: str,
            action_type: TableAction,
            subcategory: str | None = None,
            action_name: str | None = None,
    ) -> bool:
        """Only for user"""
        raise NotImplementedError()


class PermissionsManager(abc.ABC):
    async def get_permissions(self, user_or_group, for_schema_generation: bool) -> PermissionsContainer:
        raise NotImplementedError()

    async def save_permissions(self, data: dict, extra: dict) -> None:
        """
        Save permission settings submitted through the editing form.

        data contains is_superuser and explicit permission values.

        extra is the saving context.
        extra['record'] is the object being edited.
        """
        raise NotImplementedError()

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        return core_schema.is_instance_schema(cls)
