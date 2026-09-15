import pytest

from brilliance_admin import schema
from brilliance_admin.auth import AdminAuthentication, UserABC
from brilliance_admin.schema.table.history_logs_category import HistoryCategoryField, HistoryLogsAdmin


class TestAuth(AdminAuthentication):
    async def authenticate(self, headers):
        return UserABC(username='test')


@pytest.mark.asyncio
async def test_history_category_autocomplete_serializes_total_count():
    field = HistoryCategoryField()
    field.choices = [
        {'value': f'group/category-{index}', 'title': f'Category {index}'}
        for index in range(12)
    ]

    result = await field.autocomplete(
        schema.AutocompleteData(),
        UserABC(username='test'),
        {},
    )

    assert result.total_count == '12'


def test_history_logs_category_skips_root_links(language_context):
    class TestDashboard(schema.CategoryDashboard):
        slug = 'dashboard'
        title = 'Dashboard'

    class TestCategory(schema.CategoryTable):
        slug = 'payments'
        title = 'Payments'
        table_schema = schema.FieldsSchema(value=schema.StringField())

        async def get_list(self, *args, **kwargs):
            raise NotImplementedError

    class TestLogsAdmin(HistoryLogsAdmin):
        title = 'History logs'
        list_display = ['category_path']
        table_schema = schema.FieldsSchema(category_path=schema.StringField())
        table_filters = schema.FieldsSchema(category_path=HistoryCategoryField())

        async def get_list(self, *args, **kwargs):
            raise NotImplementedError

    logs = TestLogsAdmin()
    admin_schema = schema.AdminSchema(
        auth=TestAuth(),
        categories=[
            schema.CategoryLink(slug='docs', title='Docs', link='https://example.com'),
            schema.CategoryGroup(
                slug='main',
                title='Main',
                subcategories=[TestDashboard(), TestCategory()],
            ),
            schema.CategoryGroup(
                slug='history',
                title='History',
                subcategories=[logs],
            ),
        ],
    )

    result = logs.generate_category_schema(
        UserABC(username='test'),
        language_context,
        admin_schema,
    )

    assert logs.table_filters.get_field('category_path').choices == [
        {'value': 'main/payments', 'title': 'Main / Payments'},
        {'value': 'history/history-logs', 'title': 'History / History logs'},
    ]
