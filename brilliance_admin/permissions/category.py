from brilliance_admin.permissions.settings import PermissionsData, PermissionValue

from brilliance_admin.schema.category import BaseCategory, CategoryGroup
from brilliance_admin.schema.table.category_table import CategoryTable
from brilliance_admin.schema.table.fields.base import BooleanField, ChoiceField
from brilliance_admin.schema.table.fields_schema import FieldsSchema, FormField, FormSet
from brilliance_admin.schema.table.table_action import TableAction
from brilliance_admin.translations import TranslateText as _
from brilliance_admin.utils import humanize_field_name


class PermissionsSettingsCategory(CategoryTable):
    slug = 'permissions-settings'
    title = _('permissions.title')
    icon = 'mdi-shield-account'

    async def get_list(self, *args, **kwargs):
        raise NotImplementedError('Permissions settings storage is forbidden')

    def post_schema_generation(self, admin_schema):
        self.table_schema = self.generate_rules_schema(admin_schema.categories)
        super().post_schema_generation(admin_schema)

    def generate_rules_schema(self, categories: list[BaseCategory]) -> FieldsSchema:
        fields = {
            'is_superuser': BooleanField(
                label=_('permissions.is_superuser'),
                help_text=_('permissions.is_superuser_help'),
                default=False,
            ),
        }
        formsets = [FormField('is_superuser')]
        for category in categories:
            formsets.extend(self._collect_rules(category, '', fields))
        return FieldsSchema(formset=FormSet(fields=formsets), **fields)

    def _collect_rules(self, category: BaseCategory, parent_path: str, fields: dict) -> list[FormSet]:
        if isinstance(category, PermissionsSettingsCategory):
            return []

        path = f'{parent_path}.{category.slug}' if parent_path else category.slug
        if isinstance(category, CategoryGroup):
            formsets = []
            for subcategory in category.subcategories:
                formsets.extend(self._collect_rules(subcategory, path, fields))
            return formsets

        formset = FormSet(
            title=category.title or humanize_field_name(category.slug),
            description=category.description,
            icon=category.icon,
            fields=[self._add_rule(fields, path, TableAction.LIST)],
        )

        if isinstance(category, CategoryTable):
            if category.has_retrieve:
                formset.fields.append(self._add_rule(fields, path, TableAction.RETRIEVE))
            if category.has_create:
                formset.fields.append(self._add_rule(fields, path, TableAction.CREATE))
            if category.has_update:
                formset.fields.append(self._add_rule(fields, path, TableAction.UPDATE))
            for action_name, action in category.get_actions().items():
                formset.fields.append(self._add_rule(
                    fields,
                    path,
                    TableAction.ADMIN_ACTION,
                    action_name,
                    label=action.action_info['title'],
                ))

        for subcategory in getattr(category, 'subcategories', []):
            formset.fields.extend(self._collect_rules(subcategory, path, fields))

        return [formset]

    def _add_rule(
            self, fields: dict, path: str, action_type: TableAction, action_name: str | None = None, label=None,
    ) -> FormField:
        key = f'{path}.{action_type.value}'
        if action_name is not None:
            key = f'{key}.{action_name}'
        if key in fields:
            raise ValueError(f'Permission rule "{key}" is already registered')

        fields[key] = ChoiceField(
            btn_toggle=True,
            label=label if label is not None else _(f'permissions.actions.{action_type.value}'),
            choices=PermissionValue,
            default=PermissionValue.INHERIT.value,
        )
        return FormField(key, col_span=4)

    async def get_data(self, record, data: PermissionsData, extra: dict) -> None:
        permissions = extra['admin_schema'].permissions_manager.get_user_permissions(
            record, for_schema_generation=True,
        )
        stored_data = permissions.get_permissions_data()
        data.is_superuser = stored_data.is_superuser
        rules = {rule.name: rule for rule in data.iter_rules()}
        for rule in stored_data.iter_rules():
            rules[rule.name].set_value(rule.value)

    async def save_data(self, record, data: PermissionsData, extra: dict) -> None:
        await extra['admin_schema'].permissions_manager.save_permissions(data, extra)
