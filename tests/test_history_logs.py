import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from brilliance_admin import schema
from brilliance_admin.auth import AdminAuthentication, UserABC
from brilliance_admin.integrations.sqlalchemy.history_changes.models import HistoryChange
from brilliance_admin.schema.table.history_change_provider import HistoryLogsProvider, LogType
from brilliance_admin.schema.table.history_logs_category import HistoryCategoryField, HistoryLogsAdmin
from brilliance_admin.translations import TranslateText
from example.main import admin_schema, app
from example.sections.models import (
    CurrencyFactory, Fee, FeeFactory, FeeTypeFactory, MerchantFactory, TerminalFactory,
)

client = TestClient(app)


class TestAuth(AdminAuthentication):
    async def authenticate(self, headers):
        return UserABC(username='test')


@pytest.mark.asyncio
async def test_subcategory_save_and_action_write_history(postgres_sessionmaker, mocker):
    merchant = await MerchantFactory()
    currency = await CurrencyFactory()
    terminal = await TerminalFactory(merchant=merchant, currency=currency)
    fee_type = await FeeTypeFactory()
    fee = await FeeFactory(terminal=terminal, fee_type=fee_type, title='111')

    category = admin_schema.get_group('payments').get_category('terminal').get_subcategory('fee')
    mocker.patch.object(category, 'db_async_session', postgres_sessionmaker)
    params = {'subcategory': 'fee', 'parent_pk': terminal.id}

    response = client.patch(
        app.url_path_for('table_update', group='payments', category='terminal', pk=str(fee.id)),
        params=params,
        json={'title': '222'},
    )
    assert response.status_code == 200, response.text

    async with postgres_sessionmaker() as session:
        updated = await session.get(Fee, fee.id)
        assert updated.title == '222'
        entry = (await session.execute(select(HistoryChange))).scalar_one()
        assert entry.category_path == 'payments/terminal/fee'
        assert entry.log_type == LogType.UPDATE.value
        assert entry.pk == str(fee.id)
        assert entry.user == 'test_admin'
        assert '111' in entry.data['title']['from']
        assert '222' in entry.data['title']['to']

    response = client.post(
        app.url_path_for('table_action', group='payments', category='terminal', action='delete'),
        params=params,
        json={'pks': [fee.id]},
    )
    assert response.status_code == 200, response.text

    async with postgres_sessionmaker() as session:
        assert await session.get(Fee, fee.id) is None
        entries = (await session.execute(select(HistoryChange).order_by(HistoryChange.id))).scalars().all()
        assert len(entries) == 2
        entry = entries[1]
        assert entry.category_path == 'payments/terminal/fee'
        assert entry.log_type == LogType.ADMIN_ACTION.value
        assert entry.action_slug == 'delete'
        assert entry.user == 'test_admin'
        assert entry.data['pks'] == [fee.id]


def test_history_diff_serializes_translated_value_without_language_context(language_context):
    before = {
        'options_chains': [{'option': {'key': 1, 'title': TranslateText('option.title')}}],
    }
    after = {
        'options_chains': [{'option': {'key': 2, 'title': TranslateText('option.title')}}],
    }

    HistoryLogsProvider.get_update_data(before, after, language_context)


def test_history_diff_marks_only_changed_parts_of_chains_payment_settings(language_context):
    before = [{
        'id': 5,
        'option': {'key': 1, 'title': 'Test'},
        'success_weight': 1,
        'fail_weight': 1,
        'terminal': False,
        'reverse': False,
        'active': True,
        'created_at': '2026-08-11T08:04:22.655685Z',
    }]
    after = [{
        'terminal': False,
        'reverse': False,
        'active': True,
        'id': 5,
        'option': {'key': 2, 'title': 'Test'},
        'success_weight': 1,
        'fail_weight': 1,
        'created_at': '2026-08-11T08:04:22.655685Z',
    }]
    assert HistoryLogsProvider.get_update_data(
        {'chains_payment_settings': before},
        {'chains_payment_settings': after},
        language_context,
    ) == {
        'chains_payment_settings': {
            'from': (
                '[{&quot;active&quot;: true, &quot;created_at&quot;: &quot;2026-08-11T08:04:22.655685Z&quot;, '
                '&quot;fail_weight&quot;: 1, &quot;id&quot;: 5, &quot;option&quot;: {&quot;key&quot;: '
                '<span class="history-diff-removed">1</span>, &quot;title&quot;: &quot;Test&quot;}, '
                '&quot;reverse&quot;: false, &quot;success_weight&quot;: 1, &quot;terminal&quot;: false}]'
            ),
            'to': (
                '[{&quot;active&quot;: true, &quot;created_at&quot;: &quot;2026-08-11T08:04:22.655685Z&quot;, '
                '&quot;fail_weight&quot;: 1, &quot;id&quot;: 5, &quot;option&quot;: {&quot;key&quot;: '
                '<span class="history-diff-added">2</span>, &quot;title&quot;: &quot;Test&quot;}, '
                '&quot;reverse&quot;: false, &quot;success_weight&quot;: 1, &quot;terminal&quot;: false}]'
            ),
            'html_diff': True,
        },
    }


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


@pytest.mark.asyncio
async def test_history_logs_category_skips_root_links(language_context):
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

    user = UserABC(username='test')
    permissions = await admin_schema.permissions_manager.get_permissions(user, for_schema_generation=True)
    result = logs.generate_category_schema(
        user,
        language_context,
        admin_schema,
        user_permissions=permissions,
    )

    assert logs.table_filters.get_field('category_path').choices == [
        {'value': 'main/payments', 'title': 'Main / Payments'},
        {'value': 'history/history-logs', 'title': 'History / History logs'},
    ]
