from brilliance_admin.auth import UserABC
from brilliance_admin.permissions.interfaces import PermissionsManager, UserPermissions
from brilliance_admin.permissions.settings import PermissionsData
from brilliance_admin.schema.category import BaseCategory
from brilliance_admin.schema.table.table_action import TableAction


class AllowAllUserPermissions(UserPermissions):
    def get_permissions_data(self) -> PermissionsData:
        return PermissionsData([], is_superuser=True)

    def has_action_permission(
            self,
            category: BaseCategory,
            action_type: TableAction,
            action_name: str | None = None,
    ) -> bool:
        return True


class AllowAllPermissionsManager(PermissionsManager):
    async def get_user_permissions(self, user: UserABC, for_schema_generation: bool) -> UserPermissions:
        return AllowAllUserPermissions(user)

    async def save_permissions(self, data: PermissionsData, extra: dict) -> None:
        print('Permissions settings:', extra['record'], data)
