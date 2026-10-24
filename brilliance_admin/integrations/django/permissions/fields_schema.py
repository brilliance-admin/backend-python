from brilliance_admin.integrations.django.fields_schema import DjangoFieldsSchema


class DjangoPermissionsFieldsSchema(DjangoFieldsSchema):
    async def create(self, deserialized_data: dict, *, user, admin_schema):
        permissions = deserialized_data.pop('permissions_settings', None)
        record = await super().create(deserialized_data, user=user, admin_schema=admin_schema)
        if permissions:
            await admin_schema.permissions_manager.save_permissions(
                permissions[0],
                extra={'record': record, 'model': self.model, 'user': user, 'admin_schema': admin_schema},
            )
        return record

    async def update(self, record, deserialized_data: dict, *, user, admin_schema):
        permissions = deserialized_data.pop('permissions_settings', None)
        record = await super().update(record, deserialized_data, user=user, admin_schema=admin_schema)
        if permissions:
            await admin_schema.permissions_manager.save_permissions(
                permissions[0],
                extra={'record': record, 'model': self.model, 'user': user, 'admin_schema': admin_schema},
            )
        return record
