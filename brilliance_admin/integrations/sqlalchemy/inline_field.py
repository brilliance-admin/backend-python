from brilliance_admin.schema.table.fields.base import InlineField


class SQLAlchemyInlineField(InlineField):
    def remove_reverse_fk_field(self, owner_model):
        # pylint: disable=import-outside-toplevel
        from brilliance_admin.integrations.sqlalchemy.fields_schema import SQLAlchemyFieldsSchema
        from brilliance_admin.integrations.sqlalchemy.related_field import SQLAlchemyRelatedField

        if not isinstance(self.table_schema, SQLAlchemyFieldsSchema):
            msg = (
                f'{type(self).__name__}.table_schema {self.table_schema}'
                ' must be subclass of SQLAlchemyFieldsSchema'
            )
            raise AttributeError(msg)

        excluded_fields = []

        for field_slug, field in self.table_schema.get_fields().items():
            if not isinstance(field, SQLAlchemyRelatedField):
                continue

            if field.target_model is owner_model:
                excluded_fields.append(field_slug)

        for field_slug in excluded_fields:
            self.table_schema.get_fields().pop(field_slug, None)

        if self.table_schema.fields:
            self.table_schema.fields = [slug for slug in self.table_schema.fields if slug not in excluded_fields]

        if self.table_schema.list_display:
            self.table_schema.list_display = [
                slug for slug in self.table_schema.list_display if slug not in excluded_fields
            ]
