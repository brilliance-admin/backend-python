from brilliance_admin.permissions.interfaces import PermissionsManager, PermissionsContainer
from brilliance_admin.permissions.settings import PermissionRule, PermissionsData, PermissionValue
from brilliance_admin.schema.table.table_action import TableAction

from .models import PermissionsGroup, UserPermissionsSettings


class DjangoPermissionsContainer(PermissionsContainer):
    settings: UserPermissionsSettings | PermissionsGroup | None
    groups: list[PermissionsGroup]

    @classmethod
    async def load(cls, user_or_group) -> 'DjangoPermissionsContainer':
        container = cls(user_or_group)
        if isinstance(user_or_group, PermissionsGroup):
            container.settings = user_or_group
            container.groups = []
        else:
            container.settings = await UserPermissionsSettings.objects.filter(user=user_or_group).afirst()
            container.groups = [
                group
                async for group in PermissionsGroup.objects.filter(users=user_or_group).order_by('priority', 'pk')
            ]
        return container

    def get_permissions_data(self) -> PermissionsData:
        rules = []
        if self.settings is not None:
            for name, value in self.settings.rules.items():
                rule = PermissionRule(name)
                rule.set_value(value)
                rules.append(rule)
        return PermissionsData(rules, is_superuser=self.user_or_group.is_superuser)

    # Only for users
    def has_action_permission(
        self,
        group: str | None,
        category: str,
        action_type: TableAction,
        subcategory: str | None = None,
        action_name: str | None = None,
    ) -> bool:
        if isinstance(self.user_or_group, PermissionsGroup):
            raise TypeError('Action permissions can only be checked for a user')

        key = f'{group}.{category}' if group is not None else category
        if subcategory is not None:
            key = f'{key}.{subcategory}'

        key = f'{key}.{action_type.value}'
        if action_name is not None:
            key = f'{key}.{action_name}'

        result = PermissionValue.DENY
        for group in self.groups:
            if group.is_superuser:
                result = PermissionValue.ALLOW
            value = PermissionValue(group.rules.get(key, PermissionValue.INHERIT))
            if value != PermissionValue.INHERIT:
                result = value

        if self.user_or_group.is_superuser:
            result = PermissionValue.ALLOW
        if self.settings is not None:
            value = PermissionValue(self.settings.rules.get(key, PermissionValue.INHERIT))
            if value != PermissionValue.INHERIT:
                result = value

        return result == PermissionValue.ALLOW


class DjangoPermissionsManager(PermissionsManager):
    async def get_permissions(self, user_or_group, for_schema_generation: bool) -> DjangoPermissionsContainer:
        return await DjangoPermissionsContainer.load(user_or_group)

    async def save_permissions(self, data: dict, extra: dict) -> None:
        record = extra['record']
        is_superuser = data['is_superuser']
        rules = {
            name: value
            for name, value in data.items()
            if name != 'is_superuser'
        }
        if isinstance(record, PermissionsGroup):
            record.rules = rules
            record.is_superuser = is_superuser
            await record.asave(update_fields=['rules', 'is_superuser'])
        else:
            await UserPermissionsSettings.objects.aupdate_or_create(
                user=record,
                defaults={'rules': rules},
            )
            record.is_superuser = is_superuser
            await record.asave(update_fields=['is_superuser'])
