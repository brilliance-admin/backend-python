from asgiref.sync import sync_to_async
from brilliance_admin.utils import DeserializeAction

from brilliance_admin.schema.table.fields.base import InlineField


class DjangoInlineField(InlineField):
    def _get_related_model(self, owner_model):
        if self.table_schema is None or getattr(self.table_schema, 'model', None) is None:
            msg = f'{type(self).__name__}.table_schema.model is required'
            raise AttributeError(msg)

        for model_field in self.table_schema.model._meta.fields:
            related_model = getattr(model_field, 'related_model', None)
            if related_model is owner_model:
                return model_field.name

        msg = (
            f'{type(self).__name__} cannot find FK from '
            f'{self.table_schema.model.__name__} to {owner_model.__name__}'
        )
        raise AttributeError(msg)

    async def _save_inline_record(self, parent_record, line_data, fk_field_name, existing_record=None):
        if existing_record is None:
            record = self.table_schema.model()
        else:
            record = existing_record

        for field_slug, value in line_data.items():
            if field_slug == self.table_schema.model._meta.pk.name:
                continue
            setattr(record, field_slug, value)

        setattr(record, fk_field_name, parent_record)
        await record.asave()
        return record

    async def serialize(self, value, extra: dict, *args, **kwargs):
        if value is None:
            return

        record = extra.get('record')
        if record is None:
            msg = f'{type(self).__name__} requires extra["record"] for serialization'
            raise AttributeError(msg)

        if hasattr(value, 'all'):
            value = await sync_to_async(list, thread_sensitive=True)(value.all())

        if not isinstance(value, list):
            msg = f'{type(self).__name__} value must be list, got {type(value).__name__}'
            raise TypeError(msg)

        result = []
        for line_value in value:
            line_extra = {**extra, 'record': line_value}
            result.append(await self.table_schema.serialize(line_value, line_extra))

        return result

    async def create_inline(self, parent_record, field_slug, value, session):
        if value is None:
            return

        if not isinstance(value, list):
            msg = f'{type(self).__name__} value must be list, got {type(value).__name__}'
            raise TypeError(msg)

        fk_field_name = self._get_related_model(type(parent_record))

        for line_data in value:
            deserialized_line = await self.table_schema.deserialize_fields(
                line_data,
                DeserializeAction.CREATE,
                extra={'model': self.table_schema.model},
            )
            await self._save_inline_record(parent_record, deserialized_line, fk_field_name)

    async def update_inline(self, parent_record, field_slug, value, session, user):
        if value is None:
            return

        if not isinstance(value, list):
            msg = f'{type(self).__name__} value must be list, got {type(value).__name__}'
            raise TypeError(msg)

        fk_field_name = self._get_related_model(type(parent_record))
        existing_records = await sync_to_async(
            lambda: list(getattr(parent_record, field_slug).all()),
            thread_sensitive=True,
        )()
        existing_by_id = {record.pk: record for record in existing_records}
        seen_ids = set()
        records_to_add = []
        pk_name = self.table_schema.model._meta.pk.name

        for line_data in value:
            line_data = dict(line_data)
            line_id = line_data.pop(pk_name, None)

            if line_id is None:
                deserialized_line = await self.table_schema.deserialize_fields(
                    line_data,
                    DeserializeAction.CREATE,
                    extra={'model': self.table_schema.model},
                )
                records_to_add.append(
                    await self._save_inline_record(parent_record, deserialized_line, fk_field_name)
                )
                continue

            seen_ids.add(line_id)
            line_record = existing_by_id.get(line_id)
            if line_record is None:
                msg = (
                    f'Inline record "{self.table_schema.model.__name__}" #{line_id} '
                    f'not found for field "{field_slug}"'
                )
                raise AttributeError(msg)

            deserialized_line = await self.table_schema.deserialize_fields(
                line_data,
                DeserializeAction.UPDATE,
                extra={'model': self.table_schema.model},
            )
            await self._save_inline_record(parent_record, deserialized_line, fk_field_name, line_record)

        for record in existing_records:
            if record.pk in seen_ids:
                continue
            await record.adelete()

        # Newly created rows are already linked by FK in create_from_deserialized.
