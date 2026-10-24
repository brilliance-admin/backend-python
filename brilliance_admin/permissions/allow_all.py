from brilliance_admin.permissions.interfaces import PermissionsManager, PermissionsContainer
from brilliance_admin.permissions.settings import PermissionsData
from brilliance_admin.schema.table.table_action import TableAction


class AllowAll(PermissionsContainer):
    def get_permissions_data(self) -> PermissionsData:
        return PermissionsData([], is_superuser=True)

    def has_action_permission(
            self,
            group: str | None,
            category: str,
            action_type: TableAction,
            subcategory: str | None = None,
            action_name: str | None = None,
    ) -> bool:
        return True


class AllowAllPermissionsManager(PermissionsManager):
    async def get_permissions(self, user_or_group, for_schema_generation: bool) -> PermissionsContainer:
        return AllowAll(user_or_group)

    async def save_permissions(self, data: dict, extra: dict) -> None:
        print('Permissions settings:', extra['record'], data)
