from brilliance_admin.permissions.interfaces import PermissionsManager, UserPermissions
from brilliance_admin.permissions.settings import PermissionRule, PermissionsData, PermissionValue
from brilliance_admin.schema.category import BaseCategory, CategoryGroup
from brilliance_admin.schema.table.table_action import TableAction

from .models import PermissionsGroup, UserPermissionsSettings


class DjangoUserPermissions(UserPermissions):
    def __init__(self, user, settings, groups, category_paths):
        super().__init__(user)
        self.settings = settings
        self.category_paths = category_paths
        self.rules = {}
        self.default_value = PermissionValue.DENY

        for level in [*groups, settings]:
            is_superuser = user.is_superuser if level is settings else level.is_superuser
            if is_superuser:
                self.default_value = PermissionValue.ALLOW
                self.rules.clear()
                continue
            for name, value in level.rules.items():
                value = PermissionValue(value)
                if value != PermissionValue.INHERIT:
                    self.rules[name] = value

    def get_permissions_data(self) -> PermissionsData:
        rules = []
        for name, value in self.settings.rules.items():
            rule = PermissionRule(name)
            rule.set_value(value)
            rules.append(rule)
        return PermissionsData(rules, is_superuser=self.user.is_superuser)

    def has_action_permission(
        self, category: BaseCategory, action_type: TableAction, action_name: str | None = None,
    ) -> bool:
        if isinstance(category, CategoryGroup):
            return any(
                self.has_action_permission(child, action_type, action_name)
                for child in category.subcategories
            )

        key = f'{self.category_paths[id(category)]}.{action_type.value}'
        if action_name is not None:
            key = f'{key}.{action_name}'
        return self.rules.get(key, self.default_value) == PermissionValue.ALLOW


class DjangoPermissionsManager(PermissionsManager):
    def __init__(self, categories: list[BaseCategory]):
        self.category_paths = {}
        for category in categories:
            self._register_category(category, '')

    def _register_category(self, category: BaseCategory, parent_path: str):
        path = f'{parent_path}.{category.slug}' if parent_path else category.slug
        self.category_paths[id(category)] = path
        for child in getattr(category, 'subcategories', []):
            self._register_category(child, path)

    async def get_user_permissions(self, user, for_schema_generation: bool) -> DjangoUserPermissions:
        if isinstance(user, PermissionsGroup):
            return DjangoUserPermissions(user, user, [], self.category_paths)

        settings, _ = await UserPermissionsSettings.objects.aget_or_create(user=user)
        groups = [
            group async for group in PermissionsGroup.objects.filter(users=user).order_by('priority', 'pk')
        ]
        return DjangoUserPermissions(user, settings, groups, self.category_paths)

    async def save_permissions(self, data: PermissionsData, extra: dict) -> None:
        record = extra['record']
        rules = {
            rule.name: rule.value.value
            for rule in data.iter_rules()
            if rule.value != PermissionValue.INHERIT
        }
        if isinstance(record, PermissionsGroup):
            record.rules = rules
            record.is_superuser = data.is_superuser
            await record.asave(update_fields=['rules', 'is_superuser'])
        else:
            await UserPermissionsSettings.objects.aupdate_or_create(
                user=record,
                defaults={'rules': rules},
            )
            record.is_superuser = data.is_superuser
            await record.asave(update_fields=['is_superuser'])
