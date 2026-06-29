from django.db import models

from brilliance_admin import schema
from brilliance_admin.exceptions import APIError, AdminAPIException, ValidationError
from brilliance_admin.integrations.django.inline_field import DjangoInlineField
from brilliance_admin.integrations.django.related_field import DjangoRelatedField
from brilliance_admin.utils import DeserializeAction
from brilliance_admin.utils import humanize_field_name


class DjangoFieldsSchema(schema.FieldsSchema):
    model = None

    def __init__(self, *args, model=None, **kwargs):
        if model is not None:
            self.model = model
        super().__init__(*args, **kwargs)

    def generate_fields(self, kwargs) -> dict:
        generated_fields = super().generate_fields(kwargs)

        if self.model is None:
            return generated_fields

        for field_slug, field in self.generate_related_fields():
            generated_fields = {field_slug: field, **generated_fields}

        for model_field in self.model._meta.fields:
            field_slug = model_field.name
            if field_slug in generated_fields:
                continue

            generated_fields[field_slug] = self.generate_model_field(model_field)

        for model_field in self.model._meta.many_to_many:
            field_slug = model_field.name
            if field_slug in generated_fields:
                continue

            generated_fields[field_slug] = self.generate_many_to_many_field(model_field)

        return generated_fields

    async def serialize(self, record, extra: dict, *args, **kwargs) -> dict:
        record_data = {}

        for slug, field in self.get_fields().items():
            if field._type == 'related' and not field.many:
                record_data[slug] = getattr(record, f'{slug}_id', None)
                continue
            record_data[slug] = getattr(record, slug, None)

        return await super().serialize(record_data, extra, *args, **kwargs)

    def generate_related_fields(self):
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

    def generate_model_field(self, model_field):
        field_data = {
            "label": self.get_model_field_label(model_field),
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

        if isinstance(model_field, models.Field) and model_field.get_internal_type() == "ArrayField":
            base_field = model_field.base_field
            if isinstance(base_field, (models.CharField, models.TextField)):
                field_data["array_type"] = "string"
                return schema.ArrayField(**field_data)

            if isinstance(base_field, (models.AutoField, models.BigAutoField, models.IntegerField)):
                field_data["array_type"] = "integer"
                return schema.ArrayField(**field_data)

        if isinstance(model_field, models.BooleanField):
            field_data["required"] = False
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

        if isinstance(model_field, models.JSONField):
            return schema.JSONField(**field_data)

        if isinstance(model_field, models.ImageField):
            return schema.ImageField(**field_data)

        if isinstance(model_field, models.FileField):
            return schema.FileField(**field_data)

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

    async def create(self, user, data):
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

        return await self.create_from_deserialized(deserialized_data)

    async def create_from_deserialized(self, deserialized_data):
        record = self.model()
        many_to_many_values = {}

        for field_slug, value in deserialized_data.items():
            field = self.get_field(field_slug)

            if isinstance(field, DjangoInlineField):
                continue

            if isinstance(field, DjangoRelatedField):
                model_field = self.model._meta.get_field(field_slug)

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

        return record

    async def update(self, record, user, data):
        self.validate_incoming_data(data)

        try:
            deserialized_data = await self.deserialize_fields(
                data,
                DeserializeAction.UPDATE,
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

        return await self.update_from_deserialized(record, deserialized_data)

    async def update_from_deserialized(self, record, deserialized_data):
        many_to_many_values = {}

        for field_slug, value in deserialized_data.items():
            field = self.get_field(field_slug)

            if isinstance(field, DjangoInlineField):
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

        return record
