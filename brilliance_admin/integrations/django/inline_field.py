from asgiref.sync import sync_to_async

from brilliance_admin.schema.table.fields.base import InlineField


class DjangoInlineField(InlineField):
    def remove_reverse_fk_field(self, owner_model):
        # pylint: disable=import-outside-toplevel
        from brilliance_admin.integrations.django.fields_schema import DjangoFieldsSchema

        if not isinstance(self.table_schema, DjangoFieldsSchema):
            msg = (
                f'{type(self).__name__}.table_schema {self.table_schema} '
                'must be subclass of DjangoFieldsSchema'
            )
            raise AttributeError(msg)

        excluded_fields = []
        for field_slug in list(self.table_schema.get_fields().keys()):
            model_field = self.table_schema.model._meta.get_field(field_slug)
            related_model = getattr(model_field, 'related_model', None)
            if related_model is owner_model:
                excluded_fields.append(field_slug)

        for field_slug in excluded_fields:
            self.table_schema.get_fields().pop(field_slug, None)

        if self.table_schema.fields:
            self.table_schema.fields = [slug for slug in self.table_schema.fields if slug not in excluded_fields]

        if self.table_schema.list_display:
            self.table_schema.list_display = [
                slug for slug in self.table_schema.list_display if slug not in excluded_fields
            ]

        if self.table_schema.formset:
            self.table_schema.formset.exclude_fields(set(excluded_fields))
            self.table_schema.validate_formset()

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

    def _save_inline_record_sync(self, parent_record, line_data, fk_field_name, existing_record=None):
        # pylint: disable=import-outside-toplevel
        from brilliance_admin.integrations.django.related_field import DjangoRelatedField

        if existing_record is None:
            record = self.table_schema.model()
        else:
            record = existing_record

        for field_slug, value in line_data.items():
            if field_slug == self.table_schema.model._meta.pk.name:
                continue

            field = self.table_schema.get_field(field_slug)
            if isinstance(field, DjangoRelatedField):
                model_field = self.table_schema.model._meta.get_field(field_slug)
                setattr(record, model_field.attname, value)
                continue

            setattr(record, field_slug, value)

        setattr(record, fk_field_name, parent_record)
        record.save()
        return record

    async def _save_inline_record(self, parent_record, line_data, fk_field_name, existing_record=None):
        return await sync_to_async(self._save_inline_record_sync, thread_sensitive=True)(
            parent_record,
            line_data,
            fk_field_name,
            existing_record,
        )

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
            await self._save_inline_record(parent_record, line_data, fk_field_name)

    def create_inline_sync(self, parent_record, field_slug, value, session):
        if value is None:
            return

        if not isinstance(value, list):
            msg = f'{type(self).__name__} value must be list, got {type(value).__name__}'
            raise TypeError(msg)

        fk_field_name = self._get_related_model(type(parent_record))

        for line_data in value:
            self._save_inline_record_sync(parent_record, line_data, fk_field_name)

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
                records_to_add.append(
                    await self._save_inline_record(parent_record, line_data, fk_field_name)
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

            await self._save_inline_record(parent_record, line_data, fk_field_name, line_record)

        for record in existing_records:
            if record.pk in seen_ids:
                continue
            await record.adelete()

        # Newly created rows are already linked by FK in create_from_deserialized.

    def update_inline_sync(self, parent_record, field_slug, value, session, user):
        if value is None:
            return

        if not isinstance(value, list):
            msg = f'{type(self).__name__} value must be list, got {type(value).__name__}'
            raise TypeError(msg)

        fk_field_name = self._get_related_model(type(parent_record))
        existing_records = list(getattr(parent_record, field_slug).all())
        existing_by_id = {record.pk: record for record in existing_records}
        seen_ids = set()
        pk_name = self.table_schema.model._meta.pk.name

        for line_data in value:
            line_data = dict(line_data)
            line_id = line_data.pop(pk_name, None)

            if line_id is None:
                self._save_inline_record_sync(parent_record, line_data, fk_field_name)
                continue

            seen_ids.add(line_id)
            line_record = existing_by_id.get(line_id)
            if line_record is None:
                msg = (
                    f'Inline record "{self.table_schema.model.__name__}" #{line_id} '
                    f'not found for field "{field_slug}"'
                )
                raise AttributeError(msg)

            self._save_inline_record_sync(parent_record, line_data, fk_field_name, line_record)

        for record in existing_records:
            if record.pk in seen_ids:
                continue
            record.delete()

        # Newly created rows are already linked by FK in create_from_deserialized.
