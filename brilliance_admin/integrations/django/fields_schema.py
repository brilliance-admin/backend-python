import json

from asgiref.sync import sync_to_async
from django.db import IntegrityError, connections, transaction
from django.test.utils import CaptureQueriesContext

from brilliance_admin import schema
from brilliance_admin.exceptions import APIError, AdminAPIException, ValidationError
from brilliance_admin.schema.table.fields_schema import FORMSET_EXTRA_FIELDS, FORMSET_MISSING_FIELDS
from brilliance_admin.schema.table.fields.base import InlineField
from brilliance_admin.integrations.django.inline_field import DjangoInlineField
from brilliance_admin.integrations.django.related_field import DjangoRelatedField
from brilliance_admin.utils import DeserializeAction
from brilliance_admin.utils import humanize_field_name

INLINE_FIELD_NOT_SUPPORTED = (
    '{class_name}: field "{field_slug}" is InlineField, but DjangoFieldsSchema supports only DjangoInlineField'
)


class DjangoFieldsSchema(schema.FieldsSchema):
    model = None
    _has_explicit_fields = False

    def __init__(self, *args, model=None, **kwargs):
        if model is not None:
            self.model = model
        self._has_explicit_fields = kwargs.get('fields') is not None
        super().__init__(*args, **kwargs)

        for field in self.get_fields().values():
            if isinstance(field, DjangoInlineField):
                field.remove_reverse_fk_field(self.model)

    def generate_fields(self, kwargs) -> dict:
        generated_fields = super().generate_fields(kwargs)

        if self.model is None:
            return generated_fields

        result = {}
        pk_field = self.model._meta.pk
        pk_slug = pk_field.name

        if pk_slug in generated_fields:
            result[pk_slug] = generated_fields[pk_slug]
        else:
            result[pk_slug] = self.generate_model_field(pk_field)

        for field_slug, field in self.generate_related_fields():
            if field_slug in generated_fields:
                result[field_slug] = generated_fields[field_slug]
                continue

            if field_slug not in result:
                result[field_slug] = field

        for field_slug, field in generated_fields.items():
            if field_slug not in result:
                result[field_slug] = field

        for model_field in self.model._meta.fields:
            field_slug = model_field.name
            if field_slug in result:
                continue

            result[field_slug] = self.generate_model_field(model_field)

        for model_field in self.model._meta.many_to_many:
            field_slug = model_field.name
            if field_slug in result:
                continue

            result[field_slug] = self.generate_many_to_many_field(model_field)

        if self.fields is not None:
            for field_slug in self.fields:
                if field_slug in result:
                    continue

                reverse_field = self.generate_reverse_related_field(field_slug)
                if reverse_field is not None:
                    result[field_slug] = reverse_field

        return result

    def validate_fields(self, *args, **kwargs):
        super().validate_fields(*args, **kwargs)

        if self.list_display:
            self.list_display = [
                slug
                for slug in self.list_display
                if not isinstance(self.get_field(slug), InlineField)
            ]

        for field_slug, field in self.get_fields().items():
            if isinstance(field, InlineField) and not isinstance(field, DjangoInlineField):
                raise AttributeError(
                    INLINE_FIELD_NOT_SUPPORTED.format(
                        class_name=type(self).__name__,
                        field_slug=field_slug,
                    )
                )

    def _is_deferred_inline_fk_field(self, field_slug):
        from django.db import models

        if self.model is None:
            return False

        if self._has_explicit_fields:
            return False

        model_field = self.model._meta.get_field(field_slug)
        return isinstance(model_field, (models.ForeignKey, models.OneToOneField))

    def validate_formset(self):
        if not self.formset:
            return

        formset_fields = self._collect_formset_fields(self.formset)
        available_fields = set(self.get_fields().keys())
        required_fields = {
            field_slug
            for field_slug, field in self.get_fields().items()
        }
        missing_fields = sorted(required_fields - formset_fields)
        extra_fields = sorted(formset_fields - available_fields)

        if missing_fields:
            deferred_missing_fields = [
                field_slug
                for field_slug in missing_fields
                if self._is_deferred_inline_fk_field(field_slug)
            ]
            if len(deferred_missing_fields) == len(missing_fields):
                missing_fields = []

        if missing_fields:
            msg = FORMSET_MISSING_FIELDS.format(
                class_name=type(self).__name__,
                missing_fields=json.dumps(missing_fields, ensure_ascii=False, indent=4),
                available_fields=json.dumps(list(available_fields), ensure_ascii=False, indent=4),
            )
            raise AttributeError(msg)

        if extra_fields:
            msg = FORMSET_EXTRA_FIELDS.format(
                class_name=type(self).__name__,
                extra_fields=json.dumps(extra_fields, ensure_ascii=False, indent=4),
                available_fields=json.dumps(list(available_fields), ensure_ascii=False, indent=4),
            )
            raise AttributeError(msg)

    async def serialize(self, record, extra: dict, field_slugs: list[str] | None = None, *args, **kwargs) -> dict:
        record_data = {}
        slugs = field_slugs or list(self.get_fields().keys())

        for slug in slugs:
            field = self.get_field(slug)
            if field is None:
                msg = f'{type(self).__name__}: field "{slug}" not found for serialization'
                raise AttributeError(msg)
            if field._type == 'related' and not field.many:
                record_data[slug] = getattr(record, f'{slug}_id', None)
                continue
            record_data[slug] = getattr(record, slug, None)

        return await super().serialize(record_data, extra, field_slugs=slugs, *args, **kwargs)

    def generate_related_fields(self):
        from django.db import models

        for model_field in self.model._meta.fields:
            if not isinstance(model_field, (models.ForeignKey, models.OneToOneField)):
                continue

            field_slug = model_field.name
            label = self.get_model_field_label(model_field)

            yield field_slug, DjangoRelatedField(
                label=label,
                read_only=False,
                required=self.is_required_field(model_field),
                rel_name=field_slug.removesuffix('_id'),
                many=False,
                dual_list=False,
            )

    def generate_many_to_many_field(self, model_field):
        return DjangoRelatedField(
            label=self.get_model_field_label(model_field),
            read_only=False,
            required=False,
            rel_name=model_field.name,
            many=True,
            dual_list=True,
        )

    def generate_reverse_related_field(self, field_slug):
        for model_field in self.model._meta.related_objects:
            if model_field.get_accessor_name() != field_slug:
                continue

            return DjangoRelatedField(
                label=humanize_field_name(field_slug),
                read_only=False,
                required=False,
                rel_name=field_slug,
                many=True,
                dual_list=True,
            )

        return None

    @staticmethod
    def get_allowed_extensions(model_field):
        from django.core.validators import FileExtensionValidator

        for validator in model_field.validators:
            if isinstance(validator, FileExtensionValidator):
                return list(validator.allowed_extensions)

        return None

    def generate_model_field(self, model_field):
        from django.db import models
        from django.db.models import NOT_PROVIDED
        from django.contrib.postgres.fields import ArrayField as PostgresArrayField
        from django.utils.encoding import force_str

        help_text = getattr(model_field, "help_text", None)
        default = getattr(model_field, "default", NOT_PROVIDED)

        field_data = {
            "label": self.get_model_field_label(model_field),
            "help_text": force_str(help_text) if help_text else None,
            "read_only": bool(model_field.primary_key or getattr(model_field, "auto_now_add", False)),
            "required": self.is_required_field(model_field),
        }

        if model_field.choices:
            field = schema.ChoiceField(**field_data)
            field.choices = self.normalize_choices(model_field.choices)
            return field

        if isinstance(model_field, (models.AutoField, models.BigAutoField, models.IntegerField)):
            return schema.IntegerField(**field_data)

        if isinstance(model_field, models.DecimalField):
            field_data["inputmode"] = "decimal"
            field_data["precision"] = model_field.max_digits
            field_data["scale"] = model_field.decimal_places
            return schema.DecimalField(**field_data)

        if isinstance(model_field, models.FloatField):
            field_data["inputmode"] = "decimal"
            return schema.DecimalField(**field_data)

        if isinstance(model_field, models.UUIDField):
            field_data["max_length"] = 32
            return schema.StringField(**field_data)

        if isinstance(model_field, (models.CharField, models.TextField)):
            if getattr(model_field, "max_length", None):
                field_data["max_length"] = model_field.max_length
            return schema.StringField(**field_data)

        if isinstance(model_field, PostgresArrayField):
            base_field = model_field.base_field
            if isinstance(base_field, (models.CharField, models.TextField)):
                field_data["array_type"] = "string"
                return schema.ArrayField(**field_data)

            if isinstance(base_field, (models.AutoField, models.BigAutoField, models.IntegerField)):
                field_data["array_type"] = "integer"
                return schema.ArrayField(**field_data)

            if isinstance(base_field, models.JSONField):
                field_data["array_type"] = "json"
                return schema.ArrayField(**field_data)

            base_field_type = type(base_field).__name__ if base_field is not None else "None"
            base_internal_type = base_field.get_internal_type() if base_field is not None else "None"
            msg = (
                f'Django autogenerate ORM field {self.model.__name__}.{model_field.name} '
                f'is not supported for type: ArrayField({base_internal_type})'
                f' [base_field={base_field_type}]'
            )
            raise AttributeError(msg)

        if isinstance(model_field, models.BooleanField):
            field_data["required"] = False
            if default is not NOT_PROVIDED and not callable(default):
                field_data["default"] = default
            return schema.BooleanField(**field_data)

        if isinstance(model_field, models.DateTimeField):
            return schema.DateTimeField(**field_data)

        if isinstance(model_field, models.DateField):
            field_data["include_date"] = True
            field_data["include_time"] = False
            return schema.DateTimeField(**field_data)

        if isinstance(model_field, models.TimeField):
            field_data["include_date"] = False
            field_data["include_time"] = True
            return schema.DateTimeField(**field_data)

        if isinstance(model_field, models.DurationField):
            return schema.DurationField(**field_data)

        if isinstance(model_field, models.JSONField):
            return schema.JSONField(**field_data)

        if isinstance(model_field, models.ImageField):
            field = schema.ImageField(**field_data)
            field.allowed_extensions = self.get_allowed_extensions(model_field)
            return field

        if isinstance(model_field, models.FileField):
            field = schema.FileField(**field_data)
            field.allowed_extensions = self.get_allowed_extensions(model_field)
            return field

        msg = (
            f'Django autogenerate ORM field {self.model.__name__}.{model_field.name} '
            f'is not supported for type: {type(model_field).__name__}'
        )
        raise AttributeError(msg)

    @staticmethod
    def is_required_field(model_field):
        return (
            not model_field.primary_key
            and not getattr(model_field, "blank", False)
            and not getattr(model_field, "null", False)
            and not getattr(model_field, "auto_now_add", False)
            and not getattr(model_field, "has_default", lambda: False)()
        )

    @staticmethod
    def normalize_choices(choices):
        normalized = []
        for value, title in choices:
            from django.utils.encoding import force_str
            if not isinstance(value, (str, int, float, bool)) and value is not None:
                value = force_str(value)
            normalized.append({
                'value': value,
                'title': force_str(title),
                'tag_color': None,
            })
        return normalized

    @staticmethod
    def get_model_field_label(model_field):
        verbose_name = getattr(model_field, "verbose_name", None)
        if verbose_name is not None:

            default_verbose_name = model_field.name.replace("_", " ")
            if str(verbose_name) == default_verbose_name:
                return humanize_field_name(model_field.name)

            from django.utils.encoding import force_str
            return force_str(verbose_name)

        return humanize_field_name(model_field.name)

    @staticmethod
    def should_skip_none_on_create(model_field):
        return (
            getattr(model_field, 'has_default', lambda: False)()
            or getattr(model_field, 'auto_now_add', False)
            or getattr(model_field, 'null', False)
            or getattr(model_field, 'blank', False)
        )

    def validate_incoming_data(self, data):
        for field_slug in data.keys():
            field = self.get_field(field_slug)
            if not field:
                available = list(self.get_fields().keys())
                msg = f'Field "{field_slug}" not found in schema. Available: {available}'
                raise AdminAPIException(
                    APIError(message=msg, code='field_not_found_in_schema'),
                    status_code=400,
                )

    @staticmethod
    def get_debug_info_from_context(ctx):
        return schema.DebugInfo(
            db_query_count=len(ctx),
            queries=[
                schema.DebugQuery(
                    sql=query['sql'],
                    time_ms=float(query['time']) * 1000 if query.get('time') else None,
                )
                for query in ctx.captured_queries
            ],
        )

    def get_connection(self):
        return connections[self.model.objects.db]

    async def create(self, user, data, debug: bool = False):
        self.validate_incoming_data(data)

        try:
            deserialized_data = await self.deserialize_fields(
                data,
                DeserializeAction.CREATE,
                extra={'model': self.model},
            )
        except ValidationError as e:
            raise AdminAPIException(
                APIError(
                    code='validation_error',
                    field_errors=e.data,
                ),
                status_code=400,
            ) from e

        try:
            if debug:
                return await self.create_from_deserialized_with_debug(deserialized_data)
            return await self.create_from_deserialized(deserialized_data)
        except IntegrityError as e:
            raise AdminAPIException(
                APIError(
                    message=str(e),
                    code='integrity_error',
                ),
                status_code=400,
            ) from e

    async def create_from_deserialized(self, deserialized_data):
        record = self.model()
        many_to_many_values = {}
        inline_values = {}

        for field_slug, value in deserialized_data.items():
            field = self.get_field(field_slug)

            if isinstance(field, DjangoInlineField):
                inline_values[field_slug] = value
                continue

            if isinstance(field, DjangoRelatedField):
                model_field = self.model._meta.get_field(field_slug)
                if value is None and self.should_skip_none_on_create(model_field):
                    continue

                if getattr(model_field, 'many_to_many', False):
                    many_to_many_values[field_slug] = value
                    continue

                setattr(record, model_field.attname, value)
                continue

            model_field = self.model._meta.get_field(field_slug)
            if value is None and self.should_skip_none_on_create(model_field):
                continue

            setattr(record, field_slug, value)

        await record.asave()

        for field_slug, value in many_to_many_values.items():
            relation = getattr(record, field_slug)
            await relation.aset([] if value is None else value)

        for field_slug, value in inline_values.items():
            field = self.get_field(field_slug)
            await field.create_inline(record, field_slug, value, None)

        return record

    async def create_from_deserialized_with_debug(self, deserialized_data):
        return await sync_to_async(
            self.create_from_deserialized_with_debug_sync,
            thread_sensitive=True,
        )(deserialized_data)

    def create_from_deserialized_with_debug_sync(self, deserialized_data):
        with CaptureQueriesContext(self.get_connection()) as ctx:
            record = self.create_from_deserialized_sync(deserialized_data)
        return record, self.get_debug_info_from_context(ctx)

    def create_from_deserialized_sync(self, deserialized_data):
        record = self.model()
        many_to_many_values = {}
        inline_values = {}

        with transaction.atomic():
            for field_slug, value in deserialized_data.items():
                field = self.get_field(field_slug)

                if isinstance(field, DjangoInlineField):
                    inline_values[field_slug] = value
                    continue

                if isinstance(field, DjangoRelatedField):
                    model_field = self.model._meta.get_field(field_slug)
                    if value is None and self.should_skip_none_on_create(model_field):
                        continue

                    if getattr(model_field, 'many_to_many', False):
                        many_to_many_values[field_slug] = value
                        continue

                    setattr(record, model_field.attname, value)
                    continue

                model_field = self.model._meta.get_field(field_slug)
                if value is None and self.should_skip_none_on_create(model_field):
                    continue

                setattr(record, field_slug, value)

            record.save()

            for field_slug, value in many_to_many_values.items():
                relation = getattr(record, field_slug)
                relation.set([] if value is None else value)

            for field_slug, value in inline_values.items():
                field = self.get_field(field_slug)
                field.create_inline_sync(record, field_slug, value, None)

        return record

    async def update(self, record, user, data, debug: bool = False):
        self.validate_incoming_data(data)

        try:
            deserialized_data = await self.deserialize_fields(
                data,
                DeserializeAction.UPDATE,
                extra={'model': self.model},
            )
            if debug:
                return await self.update_from_deserialized_with_debug(record, deserialized_data)
            return await self.update_from_deserialized(record, deserialized_data)
        except ValidationError as e:
            raise AdminAPIException(
                APIError(
                    code='validation_error',
                    field_errors=e.data,
                ),
                status_code=400,
            ) from e
        except IntegrityError as e:
            raise AdminAPIException(
                APIError(
                    message=str(e),
                    code='integrity_error',
                ),
                status_code=400,
            ) from e

    async def update_from_deserialized(self, record, deserialized_data):
        many_to_many_values = {}
        inline_values = {}

        for field_slug, value in deserialized_data.items():
            field = self.get_field(field_slug)

            if isinstance(field, DjangoInlineField):
                inline_values[field_slug] = value
                continue

            if isinstance(field, DjangoRelatedField):
                model_field = self.model._meta.get_field(field_slug)

                if getattr(model_field, 'many_to_many', False):
                    many_to_many_values[field_slug] = value
                    continue

                setattr(record, model_field.attname, value)
                continue

            setattr(record, field_slug, value)

        await record.asave()

        for field_slug, value in many_to_many_values.items():
            relation = getattr(record, field_slug)
            await relation.aset([] if value is None else value)

        for field_slug, value in inline_values.items():
            field = self.get_field(field_slug)
            await field.update_inline(record, field_slug, value, None, None)

        return record

    async def update_from_deserialized_with_debug(self, record, deserialized_data):
        return await sync_to_async(
            self.update_from_deserialized_with_debug_sync,
            thread_sensitive=True,
        )(record, deserialized_data)

    def update_from_deserialized_with_debug_sync(self, record, deserialized_data):
        with CaptureQueriesContext(self.get_connection()) as ctx:
            record = self.update_from_deserialized_sync(record, deserialized_data)
        return record, self.get_debug_info_from_context(ctx)

    def update_from_deserialized_sync(self, record, deserialized_data):
        many_to_many_values = {}
        inline_values = {}

        with transaction.atomic():
            for field_slug, value in deserialized_data.items():
                field = self.get_field(field_slug)

                if isinstance(field, DjangoInlineField):
                    inline_values[field_slug] = value
                    continue

                if isinstance(field, DjangoRelatedField):
                    model_field = self.model._meta.get_field(field_slug)

                    if getattr(model_field, 'many_to_many', False):
                        many_to_many_values[field_slug] = value
                        continue

                    setattr(record, model_field.attname, value)
                    continue

                setattr(record, field_slug, value)

            record.save()

            for field_slug, value in many_to_many_values.items():
                relation = getattr(record, field_slug)
                relation.set([] if value is None else value)

            for field_slug, value in inline_values.items():
                field = self.get_field(field_slug)
                field.update_inline_sync(record, field_slug, value, None, None)

        return record
