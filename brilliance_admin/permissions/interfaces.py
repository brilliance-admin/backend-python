import abc

from pydantic_core import core_schema

from brilliance_admin.auth import UserABC
from brilliance_admin.schema.category import BaseCategory
from brilliance_admin.schema.table.table_action import TableAction


class UserPermissions(abc.ABC):
    user: UserABC

    def __init__(self, user: UserABC):
        self.user = user

    @abc.abstractmethod
    def has_action_permission(
            self,
            category: BaseCategory,
            action_type: TableAction,
            action_name: str,
    ) -> bool:
        raise NotImplementedError()


class PermissionsManager(abc.ABC):
    def get_user_permissions(self, user: UserABC, for_schema_generation: bool) -> UserPermissions:
        raise NotImplementedError()

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        return core_schema.is_instance_schema(cls)
