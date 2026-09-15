from dataclasses import field
from typing import Any

from pydantic.dataclasses import dataclass

from brilliance_admin.schema.category import CategoryGroup
from brilliance_admin.schema.table.category_table import CategoryTable
import json

from brilliance_admin.schema.table.fields.base import InlineField, RelatedField, StringField
from brilliance_admin.schema.table.fields_schema import FieldsSchema
from brilliance_admin.schema.table.table_models import AutocompleteResult, Record
from brilliance_admin.translations import TranslateText as _


HISTORY_LOGS_EXTRA_KWARGS = {
    'action_time': {'label': _('history.fields.action_time')},
    'user': {'label': _('history.fields.user')},
    'log_type': {'label': _('history.fields.log_type')},
    'action_slug': {'label': _('history.fields.action_slug')},
    'category_path': {'label': _('history.fields.category_path')},
}

HISTORY_LOGS_FILTER_FIELDS = [
    'category_path',
    'action_slug',
    'action_time',
    'user',
]

HISTORY_LOGS_FILTER_EXTRA_KWARGS = {
    **HISTORY_LOGS_EXTRA_KWARGS,
    'action_slug': {
        **HISTORY_LOGS_EXTRA_KWARGS['action_slug'],
        'help_text': _('history.fields.action_slug_help'),
    },
    'action_time': {
        **HISTORY_LOGS_EXTRA_KWARGS['action_time'],
        'range': True,
    },
}


class HistoryChangeDataSchema(FieldsSchema):
    fields = ['field', 'from', 'to']

    field = StringField(label=_('history.fields.field'), read_only=True)
    to = StringField(label=_('history.fields.to'), read_only=True)

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            **{
                'from': StringField(label=_('history.fields.from'), read_only=True),
                **kwargs,
            },
        )


@dataclass
class HistoryChangeDataField(InlineField):
    many: bool = True
    table_view: bool = True
    read_only: bool = True
    table_schema: Any = field(default_factory=HistoryChangeDataSchema)

    @staticmethod
    def serialize_value(value):
        if value is None or isinstance(value, str):
            return value
        return json.dumps(value, ensure_ascii=False)

    async def serialize(self, value, extra: dict, *args, **kwargs):
        if value is None:
            return []
        if not isinstance(value, dict):
            raise TypeError(f'{type(self).__name__} value must be dict, got {type(value).__name__}')

        result = []
        for field_slug, change in value.items():
            if isinstance(change, dict) and set(change) == {'from', 'to'}:
                before, after = change['from'], change['to']
            else:
                before, after = None, change

            result.append({
                'field': field_slug,
                'from': self.serialize_value(before),
                'to': self.serialize_value(after),
            })
        return result


@dataclass
class HistoryCategoryField(RelatedField):
    choices: list[dict] = field(default_factory=list)

    async def autocomplete(self, data, user, extra, **kwargs) -> AutocompleteResult:
        search = (data.search_string or '').casefold()
        records = [
            Record(key=item['value'], title=item['title'])
            for item in self.choices
            if search in item['title'].casefold()
        ]
        total_count = len(records)
        records = records[:data.limit]

        return AutocompleteResult(
            records=records,
            current_count=len(records),
            total_count=total_count,
        )


class HistoryActionField(RelatedField):
    async def autocomplete(self, data, user, extra, **kwargs) -> AutocompleteResult:
        category_path = data.form_data.get('category_path')
        if isinstance(category_path, dict):
            category_path = category_path.get('key')
        if not isinstance(category_path, str):
            return AutocompleteResult()

        path = category_path.split('/')
        if len(path) not in {2, 3}:
            return AutocompleteResult()

        group = extra['admin_schema'].get_group(path[0])
        category = group.get_category(path[1]) if group else None
        if len(path) == 3 and category is not None:
            category = category.get_subcategory(path[2])
        if not isinstance(category, CategoryTable):
            return AutocompleteResult()

        search = (data.search_string or '').casefold()
        language_context = extra['language_context']
        records = []
        for action_slug, action in category.get_actions().items():
            title = language_context.get_text(action.action_info['title']) or action_slug
            if search in title.casefold():
                records.append(Record(key=action_slug, title=title))
        total_count = len(records)
        records = records[:data.limit]

        return AutocompleteResult(
            records=records,
            current_count=len(records),
            total_count=total_count,
        )


class HistoryLogsAdmin(CategoryTable):
    slug = 'history-logs'
    title = _('history.title')
    icon = 'mdi-history'

    list_display = [
        'id',
        'category_path',
        'action_time',
        'user',
        'object_id',
        'log_type',
        'action_slug',
    ]
    ordering_fields = ['action_time', 'log_type', 'category_path']
    default_ordering = '-action_time'

    has_create = False
    has_update = False
    has_delete = False

    def generate_category_schema(self, user, language_context, admin_schema, parent_category=None):
        result = super().generate_category_schema(
            user,
            language_context,
            admin_schema,
            parent_category,
        )

        choices = []
        for group in admin_schema.categories:
            if not isinstance(group, CategoryGroup):
                continue

            for category in group.subcategories:
                if not isinstance(category, CategoryTable):
                    continue

                choices.append({
                    'value': f'{group.slug}/{category.slug}',
                    'title': (
                        f'{language_context.get_text(group.title) or group.slug} / '
                        f'{language_context.get_text(category.title) or category.slug}'
                    ),
                })
                for subcategory in category.subcategories:
                    if not isinstance(subcategory, CategoryTable):
                        continue

                    choices.append({
                        'value': f'{group.slug}/{category.slug}/{subcategory.slug}',
                        'title': (
                            f'{language_context.get_text(group.title) or group.slug} / '
                            f'{language_context.get_text(category.title) or category.slug} / '
                            f'{language_context.get_text(subcategory.title) or subcategory.slug}'
                        ),
                    })
        category_field = self.table_filters.get_field('category_path')
        category_field.choices = choices
        return result
