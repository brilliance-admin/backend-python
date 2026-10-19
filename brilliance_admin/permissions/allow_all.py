from brilliance_admin.auth import UserABC
from brilliance_admin.permissions.interfaces import PermissionsManager, UserPermissions
from brilliance_admin.schema.category import BaseCategory
from brilliance_admin.schema.table.table_action import TableAction


class AllowAllUserPermissions(UserPermissions):
    def has_action_permission(
            self,
            category: BaseCategory,
            action_type: TableAction,
            action_name: str,
    ) -> bool:
        return True


class AllowAllPermissionsManager(PermissionsManager):
    def get_user_permissions(self, user: UserABC, for_schema_generation: bool) -> UserPermissions:
        return AllowAllUserPermissions(user)
