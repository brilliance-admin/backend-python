import pytest
from sqlalchemy import select

from brilliance_admin import sqlalchemy
from brilliance_admin.auth import UserABC
from brilliance_admin.exceptions import AdminAPIException
from brilliance_admin.schema.table.admin_action import ActionData
from example.sections.models import (
    CurrencyFactory, Fee, FeeFactory, FeeTypeFactory, Merchant, MerchantFactory, TerminalFactory,
)
from tests.sqlalchemy.test_sqlalchemy_subcategory import get_terminal_fees_subcategory


class RestrictedMerchantAdmin(sqlalchemy.SQLAlchemyAdmin):
    model = Merchant
    table_schema = sqlalchemy.SQLAlchemyFieldsSchema(model=Merchant, fields=['id', 'title'])

    def get_queryset(self, *, action, action_slug=None):
        return super().get_queryset(action=action, action_slug=action_slug).where(Merchant.title != 'hidden')


@pytest.mark.asyncio
async def test_delete_visible_record(postgres_sessionmaker):
    category = RestrictedMerchantAdmin(db_async_session=postgres_sessionmaker)
    visible = await MerchantFactory(title='visible')
    hidden = await MerchantFactory(title='hidden')
    pks = [visible.id]
    await category.delete(action_data=ActionData(pks=pks))
    async with postgres_sessionmaker() as session:
        visible_record = await session.get(Merchant, visible.id)
        hidden_record = await session.get(Merchant, hidden.id)
    assert visible_record is None
    assert hidden_record is not None


@pytest.mark.asyncio
async def test_delete_hidden_record_is_rejected(postgres_sessionmaker):
    category = RestrictedMerchantAdmin(db_async_session=postgres_sessionmaker)
    visible = await MerchantFactory(title='visible')
    hidden = await MerchantFactory(title='hidden')
    pks = [hidden.id]
    with pytest.raises(AdminAPIException) as exc_info:
        await category.delete(action_data=ActionData(pks=pks))
    assert exc_info.value.status_code == 404
    async with postgres_sessionmaker() as session:
        visible_record = await session.get(Merchant, visible.id)
        hidden_record = await session.get(Merchant, hidden.id)
    assert visible_record is not None
    assert hidden_record is not None


@pytest.mark.asyncio
async def test_delete_mixed_access_is_rejected_without_partial_deletion(postgres_sessionmaker):
    category = RestrictedMerchantAdmin(db_async_session=postgres_sessionmaker)
    visible = await MerchantFactory(title='visible')
    hidden = await MerchantFactory(title='hidden')
    pks = [visible.id, hidden.id]
    with pytest.raises(AdminAPIException) as exc_info:
        await category.delete(action_data=ActionData(pks=pks))
    assert exc_info.value.status_code == 404
    async with postgres_sessionmaker() as session:
        visible_record = await session.get(Merchant, visible.id)
        hidden_record = await session.get(Merchant, hidden.id)
    assert visible_record is not None
    assert hidden_record is not None


@pytest.mark.asyncio
async def test_delete_missing_record_is_rejected_without_partial_deletion(postgres_sessionmaker):
    category = RestrictedMerchantAdmin(db_async_session=postgres_sessionmaker)
    visible = await MerchantFactory(title='visible')
    hidden = await MerchantFactory(title='hidden')
    pks = [visible.id, max(visible.id, hidden.id) + 1]
    with pytest.raises(AdminAPIException) as exc_info:
        await category.delete(action_data=ActionData(pks=pks))
    assert exc_info.value.status_code == 404
    async with postgres_sessionmaker() as session:
        visible_record = await session.get(Merchant, visible.id)
        hidden_record = await session.get(Merchant, hidden.id)
    assert visible_record is not None
    assert hidden_record is not None


@pytest.mark.asyncio
async def test_subcategory_delete_own_record(postgres_sessionmaker, language_context):
    parent_category, category = get_terminal_fees_subcategory(postgres_sessionmaker)
    merchant = await MerchantFactory()
    currency = await CurrencyFactory()
    parent = await TerminalFactory(merchant=merchant, currency=currency)
    other_parent = await TerminalFactory(merchant=merchant, currency=currency)
    fee_type = await FeeTypeFactory()
    own = await FeeFactory(terminal=parent, fee_type=fee_type)
    other = await FeeFactory(terminal=other_parent, fee_type=fee_type)
    pks = [own.id]
    kwargs = {
        'request': None,
        'action': 'delete',
        'action_data': ActionData(pks=pks),
        'language_context': language_context,
        'user': UserABC(username='test'),
        'debug': True,
        'parent_category': parent_category,
        'parent_pk': parent.id,
    }
    await category._perform_action(**kwargs)
    async with postgres_sessionmaker() as session:
        remaining_ids = set((await session.scalars(select(Fee.id).where(Fee.id.in_([own.id, other.id])))).all())
    expected_ids = {other.id}
    assert remaining_ids == expected_ids


@pytest.mark.asyncio
async def test_subcategory_delete_other_parent_record_is_rejected(postgres_sessionmaker, language_context):
    parent_category, category = get_terminal_fees_subcategory(postgres_sessionmaker)
    merchant = await MerchantFactory()
    currency = await CurrencyFactory()
    parent = await TerminalFactory(merchant=merchant, currency=currency)
    other_parent = await TerminalFactory(merchant=merchant, currency=currency)
    fee_type = await FeeTypeFactory()
    own = await FeeFactory(terminal=parent, fee_type=fee_type)
    other = await FeeFactory(terminal=other_parent, fee_type=fee_type)
    pks = [other.id]
    kwargs = {
        'request': None,
        'action': 'delete',
        'action_data': ActionData(pks=pks),
        'language_context': language_context,
        'user': UserABC(username='test'),
        'debug': True,
        'parent_category': parent_category,
        'parent_pk': parent.id,
    }
    with pytest.raises(AdminAPIException) as exc_info:
        await category._perform_action(**kwargs)
    assert exc_info.value.status_code == 404
    async with postgres_sessionmaker() as session:
        remaining_ids = set((await session.scalars(select(Fee.id).where(Fee.id.in_([own.id, other.id])))).all())
    expected_ids = {own.id, other.id}
    assert remaining_ids == expected_ids


@pytest.mark.asyncio
async def test_subcategory_delete_mixed_parents_is_rejected_without_partial_deletion(
    postgres_sessionmaker, language_context
):
    parent_category, category = get_terminal_fees_subcategory(postgres_sessionmaker)
    merchant = await MerchantFactory()
    currency = await CurrencyFactory()
    parent = await TerminalFactory(merchant=merchant, currency=currency)
    other_parent = await TerminalFactory(merchant=merchant, currency=currency)
    fee_type = await FeeTypeFactory()
    own = await FeeFactory(terminal=parent, fee_type=fee_type)
    other = await FeeFactory(terminal=other_parent, fee_type=fee_type)
    pks = [own.id, other.id]
    kwargs = {
        'request': None,
        'action': 'delete',
        'action_data': ActionData(pks=pks),
        'language_context': language_context,
        'user': UserABC(username='test'),
        'debug': True,
        'parent_category': parent_category,
        'parent_pk': parent.id,
    }
    with pytest.raises(AdminAPIException) as exc_info:
        await category._perform_action(**kwargs)
    assert exc_info.value.status_code == 404
    async with postgres_sessionmaker() as session:
        remaining_ids = set((await session.scalars(select(Fee.id).where(Fee.id.in_([own.id, other.id])))).all())
    expected_ids = {own.id, other.id}
    assert remaining_ids == expected_ids


@pytest.mark.asyncio
async def test_subcategory_delete_without_parent_pk_is_rejected(postgres_sessionmaker, language_context):
    parent_category, category = get_terminal_fees_subcategory(postgres_sessionmaker)
    merchant = await MerchantFactory()
    currency = await CurrencyFactory()
    parent = await TerminalFactory(merchant=merchant, currency=currency)
    other_parent = await TerminalFactory(merchant=merchant, currency=currency)
    fee_type = await FeeTypeFactory()
    own = await FeeFactory(terminal=parent, fee_type=fee_type)
    other = await FeeFactory(terminal=other_parent, fee_type=fee_type)
    pks = [own.id]
    kwargs = {
        'request': None,
        'action': 'delete',
        'action_data': ActionData(pks=pks),
        'language_context': language_context,
        'user': UserABC(username='test'),
        'debug': True,
        'parent_category': parent_category,
        'parent_pk': None,
    }
    with pytest.raises(AdminAPIException) as exc_info:
        await category._perform_action(**kwargs)
    assert exc_info.value.status_code == 400
    async with postgres_sessionmaker() as session:
        remaining_ids = set((await session.scalars(select(Fee.id).where(Fee.id.in_([own.id, other.id])))).all())
    expected_ids = {own.id, other.id}
    assert remaining_ids == expected_ids
