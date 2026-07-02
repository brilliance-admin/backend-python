from brilliance_admin.translations import TranslateText as _
from brilliance_admin.integrations.django.fields_schema import DjangoFieldsSchema
from brilliance_admin.schema.table.category_table import CategoryTable
from brilliance_admin.schema.table.schema_type import SchemaType
from brilliance_admin.schema.table.table_models import AutocompleteData


class DjangoAdminBase(CategoryTable):
    model = None
    slug = None
    ordering_fields = []
    search_fields = []
    table_schema: DjangoFieldsSchema = None

    def __init__(
        self,
        *args,
        model=None,
        table_schema=None,
        ordering_fields=None,
        default_ordering=None,
        search_fields=None,
        **kwargs,
    ):
        if model is not None:
            self.model = model

        if search_fields:
            self.search_fields = search_fields

        if self.search_fields:
            self.search_enabled = True
            self.search_help = _('sqlalchemy_search_help') % {'fields': ', '.join(self.search_fields)}

        if default_ordering:
            self.default_ordering = default_ordering

        if ordering_fields:
            self.ordering_fields = ordering_fields

        if self.model is None:
            raise AttributeError(f'{type(self).__name__}.model is required for Django')

        self.validate_fields()

        if table_schema is not None:
            self.table_schema = table_schema

        if self.table_schema is None:
            self.table_schema = DjangoFieldsSchema(model=self.model)

        if not isinstance(self.table_schema, DjangoFieldsSchema):
            raise AttributeError(
                f'{type(self).__name__}.table_schema {self.table_schema} must be DjangoFieldsSchema'
            )

        if self.slug is None:
            self.slug = self.model.__name__.lower()

        if self.pk_name is None:
            self.pk_name = self.model._meta.pk.name

        if self.default_ordering is None and self.pk_name:
            self.default_ordering = f'-{self.pk_name}'

        super().__init__(*args, **kwargs)

    def _get_form_schema(self, user, language_context, parent_category=None):
        exclude_fields = []

        if isinstance(parent_category, DjangoAdminBase):
            fk_field_name = self.get_parent_fk_field_name(parent_category)
            assert fk_field_name in self.table_schema.get_fields(), (
                'Subcategory schema must contain parent FK before exclusion'
            )
            exclude_fields.append(fk_field_name)

        return self.table_schema.generate_form_schema(
            user,
            language_context,
            schema_type=SchemaType.TABLE,
            exclude_fields=exclude_fields,
        )

    def generate_category_schema(self, user, language_context, parent_category=None):
        if self.title is None:
            meta = self.model._meta
            verbose_name = getattr(meta, 'verbose_name_plural', None) or getattr(meta, 'verbose_name', None)
            if verbose_name:
                from django.utils.encoding import force_str
                self.title = force_str(verbose_name)

        return super().generate_category_schema(user, language_context, parent_category)

    def validate_fields(self):
        model_fields = {field.name for field in self.model._meta.fields}
        model_fields |= {field.name for field in self.model._meta.many_to_many}

        for field in self.search_fields:
            self.validate_lookup_path(field, 'search')

        for field in self.ordering_fields:
            if field not in model_fields:
                raise AttributeError(
                    f'{type(self).__name__}: ordering field "{field}" not found in model {self.model.__name__}'
                )

    def validate_lookup_path(self, field_path, field_kind):
        model = self.model
        parts = field_path.split('__')

        for index, part in enumerate(parts):
            try:
                model_field = model._meta.get_field(part)
            except Exception as e:
                raise AttributeError(
                    f'{type(self).__name__}: {field_kind} field "{field_path}" not found in model {self.model.__name__}'
                ) from e

            if index == len(parts) - 1:
                return

            related_model = getattr(model_field, 'related_model', None)
            if related_model is None:
                raise AttributeError(
                    f'{type(self).__name__}: {field_kind} field "{field_path}" not found in model {self.model.__name__}'
                )

            model = related_model

    def get_parent_fk_field_name(self, parent_category):
        if parent_category is None:
            return None

        parent_model = getattr(parent_category, 'model', None)
        if parent_model is None:
            return None

        matched_fields = []
        for model_field in self.model._meta.fields:
            rel_model = getattr(model_field, 'related_model', None)
            if rel_model is parent_model:
                matched_fields.append(model_field.name)

        if not matched_fields:
            raise RuntimeError(
                f'{type(self).__name__}: no FK from {self.model.__name__} '
                f'to parent model {parent_model.__name__}'
            )

        if len(matched_fields) > 1:
            raise RuntimeError(
                f'{type(self).__name__}: multiple FKs from {self.model.__name__} '
                f'to parent model {parent_model.__name__}: {matched_fields}'
            )

        return matched_fields[0]

    def apply_parent_filter(self, queryset, parent_category=None, parent_pk=None):
        if parent_category is None or parent_pk is None:
            return queryset

        fk_field_name = self.get_parent_fk_field_name(parent_category)
        return queryset.filter(**{fk_field_name: parent_pk})

    def get_extra_autocomplete(self, data: AutocompleteData) -> dict:
        extra = super().get_extra_autocomplete(data)
        extra['model'] = self.model

        if data.inline_field_slug:
            inline_field = self.table_schema.get_field(data.inline_field_slug)
            form_schema = inline_field.table_schema
            extra['model'] = form_schema.model

        return extra
