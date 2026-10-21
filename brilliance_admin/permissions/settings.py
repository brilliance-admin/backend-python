from enum import Enum

from brilliance_admin.translations import TranslateText as _


class PermissionValue(str, Enum):
    INHERIT = 'inherit'
    ALLOW = 'allow'
    DENY = 'deny'

    @property
    def label(self):
        return {
            self.INHERIT: _('permissions.inherit'),
            self.ALLOW: _('permissions.allow'),
            self.DENY: _('permissions.deny'),
        }[self]

    @property
    def tag_color(self):
        return {
            self.INHERIT: 'grey',
            self.ALLOW: 'success',
            self.DENY: 'error',
        }[self]


class PermissionRule:
    def __init__(self, name: str):
        self.name = name
        self.value = PermissionValue.INHERIT

    def set_value(self, value: PermissionValue):
        self.value = PermissionValue(value)


class PermissionsData:
    def __init__(self, rules: list[PermissionRule], is_superuser: bool = False):
        self.rules = rules
        self.is_superuser = is_superuser

    def iter_rules(self):
        return iter(self.rules)
