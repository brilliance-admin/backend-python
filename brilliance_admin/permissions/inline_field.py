from brilliance_admin.permissions.fields_schema import PermissionsFieldsSchema
from brilliance_admin.permissions.settings import PermissionValue
from brilliance_admin.exceptions import FieldError
from brilliance_admin.schema.table.fields.base import InlineField
from brilliance_admin.schema.table.schema_type import SchemaType
from brilliance_admin.translations import TranslateText as _


class PermissionsSettingsInlineField(InlineField):
    def __init__(self):
        super().__init__(label=_('permissions.title'), many=False)

    def generate_field_schema(
        self, user, field_slug, fields_schema, admin_schema, language_context,
        schema_type: SchemaType = SchemaType.TABLE, **kwargs,
    ):
        self.table_schema = PermissionsFieldsSchema(admin_schema.categories)
        return super().generate_field_schema(
            user, field_slug, fields_schema, admin_schema, language_context, schema_type, **kwargs,
        )

    async def serialize(self, value, extra: dict, *args, **kwargs):
        admin_schema = extra['admin_schema']
        self.table_schema = PermissionsFieldsSchema(admin_schema.categories)
        user_permissions = await admin_schema.permissions_manager.get_permissions(
            extra['record'], for_schema_generation=True,
        )
        permissions = user_permissions.get_permissions_data()
        record = {
            rule.name: rule.value.value
            for rule in permissions.iter_rules()
            if rule.value != PermissionValue.INHERIT
        }
        record['is_superuser'] = permissions.is_superuser
        return [record]

    async def deserialize_field(self, value, action, extra: dict, *args, **kwargs):
        self.table_schema = PermissionsFieldsSchema(extra['admin_schema'].categories)

        data = await super().deserialize_field(value, action, extra, *args, **kwargs)
        if data is not None and len(data) > 1:
            raise FieldError('Permissions settings must contain at most one record')

        if data:
            return [{
                name: rule_value
                for name, rule_value in data[0].items()
                if rule_value != PermissionValue.INHERIT
            }]

        return data
