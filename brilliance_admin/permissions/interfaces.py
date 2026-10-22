import abc

from pydantic_core import core_schema

from brilliance_admin.auth import UserABC
from brilliance_admin.permissions.settings import PermissionsData
from brilliance_admin.schema.category import BaseCategory
from brilliance_admin.schema.table.table_action import TableAction


class UserPermissions(abc.ABC):
    user: UserABC

    def __init__(self, user: UserABC):
        self.user = user

    @abc.abstractmethod
    def get_permissions_data(self) -> PermissionsData:
        """Return stored permission settings for the editing form."""
        raise NotImplementedError()

    @abc.abstractmethod
    def has_action_permission(
            self,
            category: BaseCategory,
            action_type: TableAction,
            action_name: str | None = None,
    ) -> bool:
        raise NotImplementedError()


class PermissionsManager(abc.ABC):
    async def get_user_permissions(self, user: UserABC, for_schema_generation: bool) -> UserPermissions:
        raise NotImplementedError()

    async def save_permissions(self, data: PermissionsData, extra: dict) -> None:
        """
        Save permission settings submitted through the editing form.

        data contains all available rules with deserialized form values
        and the submitted is_superuser flag.

        data.is_superuser allows all actions except those explicitly denied at this level.
        Higher priority permission settings may override these permissions.

        extra is the form deserialization context.
        extra['record'] is the object being edited.
        """
        raise NotImplementedError()

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        return core_schema.is_instance_schema(cls)
