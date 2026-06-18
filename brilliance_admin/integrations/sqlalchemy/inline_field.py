from brilliance_admin.exceptions import AdminAPIException, APIError, FieldError, ValidationError
from brilliance_admin.integrations.sqlalchemy.utils import get_pk, get_pk_field_name
from brilliance_admin.schema.table.fields.base import InlineField, TableField
from brilliance_admin.utils import DeserializeAction


class SQLAlchemyInlineField(InlineField):
    async def serialize(self, value, extra: dict, *args, **kwargs):
        if value is None:
            return

        if not isinstance(value, list):
            msg = f'{type(self).__name__} value must be list, got {type(value).__name__}'
            raise TypeError(msg)

        result = []
        for line_value in value:
            line_extra = {**extra, 'model': self.table_schema.model, 'record': line_value}
            result.append(await self.table_schema.serialize(line_value, line_extra))

        return result

    async def deserialize_field(self, value, action: DeserializeAction, extra: dict, *args, **kwargs):
        value = await TableField.deserialize_field(self, value, action, extra, *args, **kwargs)

        if value is None:
            return

        if not isinstance(value, list):
            raise FieldError(f'Некорректный тип данных: {type(value).__name__}; ожидается Array')

        if self.required and len(value) == 0:
            raise FieldError('Field is required', 'field_required')

        # pylint: disable=import-outside-toplevel
        from sqlalchemy import inspect

        pk_name = get_pk_field_name(self.table_schema.model)
        pk_col = inspect(self.table_schema.model).primary_key[0]
        pk_type = pk_col.type.python_type

        data = []
        errors = []
        has_any_error = False

        for line_value in value:
            line_action = action
            if action == DeserializeAction.UPDATE:
                line_action = (
                    DeserializeAction.UPDATE
                    if isinstance(line_value, dict) and line_value.get(pk_name) is not None
                    else DeserializeAction.CREATE
                )

            try:
                form_data = await self.table_schema.deserialize_fields(line_value, line_action, extra)

                if line_action == DeserializeAction.UPDATE and isinstance(line_value, dict) and pk_name in line_value:
                    try:
                        form_data[pk_name] = pk_type(line_value[pk_name])
                    except (ValueError, TypeError) as e:
                        msg = f'Inline field "{pk_name}" value "{line_value[pk_name]}" has invalid type'
                        raise FieldError(msg) from e

                data.append(form_data)
            except ValidationError as e:
                has_any_error = True
                errors.append(e.data)
            else:
                errors.append(None)

        if has_any_error:
            raise FieldError(errors, 'inline_nested')

        return data

    async def create_inline(self, parent_record, field_slug, value, session):
        if value is None:
            return

        if not isinstance(value, list):
            msg = f'{type(self).__name__} value must be list, got {type(value).__name__}'
            raise TypeError(msg)

        for line_data in value:
            line_record = await self.table_schema.create_from_deserialized(line_data, session)
            getattr(parent_record, field_slug).append(line_record)

    async def update_inline(self, parent_record, field_slug, value, session, user):
        if value is None:
            return

        if not isinstance(value, list):
            msg = f'{type(self).__name__} value must be list, got {type(value).__name__}'
            raise TypeError(msg)

        existing_records = list(getattr(parent_record, field_slug) or [])
        existing_by_id = {get_pk(record): record for record in existing_records}
        seen_ids = set()
        records_to_add = []

        for line_data in value:
            line_data = dict(line_data)
            pk_name = get_pk_field_name(self.table_schema.model)
            line_id = line_data.pop(pk_name, None)

            if line_id is None:
                line_record = await self.table_schema.create_from_deserialized(line_data, session)
                records_to_add.append(line_record)
                continue

            seen_ids.add(line_id)
            line_record = existing_by_id.get(line_id)
            if line_record is None:
                msg = (
                    f'Inline record "{self.table_schema.model.__name__}" #{line_id} '
                    f'not found for field "{field_slug}"'
                )
                raise AdminAPIException(APIError(message=msg, code='record_not_found'), status_code=400)

            await self.table_schema.update_from_deserialized(line_record, line_data, session, user)

        rel_records = getattr(parent_record, field_slug)
        for record in existing_records:
            if get_pk(record) in seen_ids:
                continue
            rel_records.remove(record)
            await session.delete(record)

        for record in records_to_add:
            rel_records.append(record)

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
