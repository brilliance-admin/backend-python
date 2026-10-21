from brilliance_admin.permissions.category import PermissionsSettingsCategory
from brilliance_admin.permissions.settings import PermissionRule, PermissionsData
from brilliance_admin.exceptions import FieldError, SkipField
from brilliance_admin.schema.table.fields.base import InlineField
from brilliance_admin.translations import TranslateText as _


class PermissionsSettingsInlineField(InlineField):
    def __init__(self, category: PermissionsSettingsCategory):
        super().__init__(label=_('permissions.title'), many=False)
        self.permissions_category = category

    def generate_field_schema(self, *args, **kwargs):
        self.table_schema = self.permissions_category.table_schema
        return super().generate_field_schema(*args, **kwargs)

    async def serialize(self, value, extra: dict, *args, **kwargs):
        permissions = PermissionsData([
            PermissionRule(name) for name in self.permissions_category.table_schema.get_fields()
            if name != 'is_superuser'
        ])
        await self.permissions_category.get_data(extra['record'], permissions, extra)
        record = {
            rule.name: rule.value
            for rule in permissions.iter_rules()
        }
        record['is_superuser'] = permissions.is_superuser
        return [await self.permissions_category.table_schema.serialize(record, extra)]

    async def deserialize_field(self, value, action, extra: dict, *args, **kwargs):
        self.table_schema = self.permissions_category.table_schema

        data = await super().deserialize_field(value, action, extra, *args, **kwargs)
        if data is not None and len(data) > 1:
            raise FieldError('Permissions settings must contain at most one record')

        if data:
            permissions = PermissionsData([
                PermissionRule(name) for name in self.permissions_category.table_schema.get_fields()
                if name != 'is_superuser'
            ], is_superuser=data[0]['is_superuser'])
            for rule in permissions.iter_rules():
                if rule.name in data[0]:
                    rule.set_value(data[0][rule.name])
            await self.permissions_category.save_data(extra['record'], permissions, extra)

        raise SkipField()
