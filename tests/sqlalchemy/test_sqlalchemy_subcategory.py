import pytest
from sqlalchemy import select

from brilliance_admin import auth, schema
from brilliance_admin.exceptions import AdminAPIException
from example.main import admin_schema
from example.sections.merchant import MerchantAdmin
from example.sections.models import CurrencyFactory, Fee, FeeFactory, FeeTypeFactory, MerchantFactory, TerminalFactory
from example.sections.terminal import FeeAdmin, TerminalAdmin
from example.sections.user_session import UserSessionAdmin
from example.sections.users import UserAdmin


def get_merchant_terminals_subcategory(postgres_sessionmaker):
    merchant_category = MerchantAdmin(
        db_async_session=postgres_sessionmaker,
        subcategories=[
            TerminalAdmin(db_async_session=postgres_sessionmaker),
        ],
    )
    terminals_subcategory = merchant_category.get_subcategory('terminal')
    assert terminals_subcategory
    return merchant_category, terminals_subcategory


def get_terminal_fees_subcategory(postgres_sessionmaker):
    terminal_category = TerminalAdmin(
        db_async_session=postgres_sessionmaker,
        subcategories=[
            FeeAdmin(db_async_session=postgres_sessionmaker),
        ],
    )
    fees_subcategory = terminal_category.get_subcategory('fee')
    assert fees_subcategory
    return terminal_category, fees_subcategory


@pytest.mark.asyncio
async def test_subcategory_list(
        postgres_sessionmaker, language_context):
    """
    Проверяет, что список сабкатегории merchant -> terminal
    возвращает только терминалы выбранного merchant по parent_pk.
    """
    merchant_category, terminals_subcategory = get_merchant_terminals_subcategory(postgres_sessionmaker)
    user = auth.UserABC(username='test')

    merchant_1 = await MerchantFactory(title='merchant 1')
    merchant_2 = await MerchantFactory(title='merchant 2')

    currency = await CurrencyFactory()

    terminal_1 = await TerminalFactory(title='merchant 1 terminal 1', merchant=merchant_1, currency=currency)
    terminal_2 = await TerminalFactory(title='merchant 1 terminal 2', merchant=merchant_1, currency=currency)
    await TerminalFactory(title='merchant 2 terminal 1', merchant=merchant_2, currency=currency)
    await TerminalFactory(title='merchant 2 terminal 2', merchant=merchant_2, currency=currency)

    list_result = await terminals_subcategory.get_list(
        schema.ListData(page=1, limit=25),
        user,
        language_context,
        debug=True,
        parent_category=merchant_category,
        parent_pk=merchant_1.id,
    )

    assert [row['id'] for row in list_result.data] == [terminal_2.id, terminal_1.id]
    assert [row['merchant_id']['key'] for row in list_result.data] == [merchant_1.id, merchant_1.id]


@pytest.mark.asyncio
async def test_subcategory_retrieve(
        postgres_sessionmaker, language_context):
    """
    Проверяет, что retrieve сабкатегории terminal -> fee
    возвращает только комиссию выбранного terminal по parent_pk.
    """
    terminal_category, fees_subcategory = get_terminal_fees_subcategory(postgres_sessionmaker)
    user = auth.UserABC(username='test')

    merchant = await MerchantFactory(title='merchant')
    currency = await CurrencyFactory()
    fee_type = await FeeTypeFactory(title='payplanet')

    terminal_1 = await TerminalFactory(title='terminal 1', merchant=merchant, currency=currency)
    terminal_2 = await TerminalFactory(title='terminal 2', merchant=merchant, currency=currency)

    fee_1 = await FeeFactory(title='fee 1', terminal=terminal_1, fee_type=fee_type, fix_amount=1)
    fee_2 = await FeeFactory(title='fee 2', terminal=terminal_2, fee_type=fee_type, fix_amount=1)

    retrieve_result = await fees_subcategory.retrieve(
        pk=fee_1.id,
        user=user,
        language_context=language_context,
        debug=True,
        parent_category=terminal_category,
        parent_pk=terminal_1.id,
    )

    assert retrieve_result.data['id'] == fee_1.id
    assert retrieve_result.data['title'] == 'fee 1'
    assert retrieve_result.data['terminal_id'] == {
        'key': terminal_1.id,
        'title': terminal_1.title,
    }

    with pytest.raises(AdminAPIException) as exc_info:
        await fees_subcategory.retrieve(
            pk=fee_2.id,
            user=user,
            language_context=language_context,
            debug=True,
            parent_category=terminal_category,
            parent_pk=terminal_1.id,
        )

    context = {'language_context': language_context}
    assert exc_info.value.get_error().model_dump(context=context) == {
        'code': 'record_not_found',
        'field_errors': None,
        'message': f'Запись по ключу id={fee_2.id} не найдена.',
    }


@pytest.mark.asyncio
async def test_subcategory_create(
        postgres_sessionmaker, language_context):
    """
    Проверяет, что create сабкатегории terminal -> fee
    проставляет родительский terminal из parent_pk.
    """
    terminal_category, fees_subcategory = get_terminal_fees_subcategory(postgres_sessionmaker)
    user = auth.UserABC(username='test')

    terminal = await TerminalFactory(
        title='terminal for create',
        merchant=await MerchantFactory(title='merchant'),
        currency=await CurrencyFactory(),
    )
    fee_type = await FeeTypeFactory(title='provider')

    create_result = await fees_subcategory.create(
        data={
            'title': 'created fee',
            'accrual_type': {'value': 'above', 'title': 'Above (from user)'},
            'percent_part': True,
            'percent': '1.500',
            'fix_part': True,
            'fix_type': {'value': 'additional', 'title': 'Additional'},
            'fix_amount': 10,
            'active': True,
            'source': {'value': 'payplanet', 'title': 'Payplanet fee'},
            'operation_type': {'value': 'refund', 'title': 'Refund'},
            'fee_type_id': {'key': fee_type.id, 'title': fee_type.title},
        },
        user=user,
        language_context=language_context,
        debug=True,
        parent_category=terminal_category,
        parent_pk=terminal.id,
    )

    async with postgres_sessionmaker() as session:
        fee = await session.scalar(select(Fee).where(Fee.id == create_result.pk))

    assert fee
    assert fee.title == 'created fee'
    assert fee.terminal_id == terminal.id
    assert fee.fee_type_id == fee_type.id
    assert str(fee.percent) == '1.500'
    assert fee.fix_amount == 10
    assert fee.operation_type == 'refund'


@pytest.mark.asyncio
async def test_subcategory_update(
        postgres_sessionmaker, language_context):
    """
    Проверяет, что update сабкатегории terminal -> fee
    обновляет только комиссию выбранного terminal по parent_pk.
    """
    terminal_category, fees_subcategory = get_terminal_fees_subcategory(postgres_sessionmaker)
    user = auth.UserABC(username='test')

    merchant = await MerchantFactory(title='merchant')
    currency = await CurrencyFactory()
    fee_type = await FeeTypeFactory(title='other')

    terminal_1 = await TerminalFactory(title='terminal 1', merchant=merchant, currency=currency)
    terminal_2 = await TerminalFactory(title='terminal 2', merchant=merchant, currency=currency)

    fee_1 = await FeeFactory(title='fee 1', terminal=terminal_1, fee_type=fee_type, fix_amount=1)
    fee_2 = await FeeFactory(title='fee 2', terminal=terminal_2, fee_type=fee_type, fix_amount=1)

    update_result = await fees_subcategory.update(
        pk=fee_1.id,
        data={
            'title': 'updated fee',
            'fix_amount': 15,
        },
        user=user,
        language_context=language_context,
        debug=True,
        parent_category=terminal_category,
        parent_pk=terminal_1.id,
    )

    assert update_result.pk == fee_1.id

    async with postgres_sessionmaker() as session:
        updated_fee = await session.scalar(select(Fee).where(Fee.id == fee_1.id))

    assert updated_fee
    assert updated_fee.title == 'updated fee'
    assert updated_fee.fix_amount == 15
    assert updated_fee.terminal_id == terminal_1.id

    with pytest.raises(AdminAPIException) as exc_info:
        await fees_subcategory.update(
            pk=fee_2.id,
            data={
                'title': 'must fail',
            },
            user=user,
            language_context=language_context,
            debug=True,
            parent_category=terminal_category,
            parent_pk=terminal_1.id,
        )

    context = {'language_context': language_context}
    assert exc_info.value.get_error().model_dump(context=context) == {
        'code': 'record_not_found',
        'field_errors': None,
        'message': f'Запись по ключу id={fee_2.id} не найдена.',
    }


def test_subcategory_schema_removes_reverse_fk(postgres_sessionmaker, language_context):
    """
    Проверяет, что при генерации schema сабкатегории reverse FK в родителя
    не попадает в table_schema.fields, а через обычный CategoryGroup
    схема продолжает строиться без попытки резать по model.
    """
    user_category = UserAdmin(
        db_async_session=postgres_sessionmaker,
        subcategories=[
            UserSessionAdmin(db_async_session=postgres_sessionmaker),
        ],
    )
    user = auth.UserABC(username='test')
    user_session_category = user_category.get_subcategory('usersession')
    assert user_session_category is not None
    assert user_session_category.get_parent_fk_field_name(user_category) == 'user_id', (
        'UserSessionAdmin must resolve user_id as the FK to UserAdmin parent'
    )

    user_schema = user_category.generate_category_schema(user, language_context, admin_schema)
    subcategory_schema = user_schema.table_info.subcategories['usersession']
    subcategory_fields = subcategory_schema['table_info']['table_schema']['fields']

    assert 'user_id' not in subcategory_fields, (
        'user_id must be removed from UserSessionAdmin schema when it is generated '
        'as a subcategory of UserAdmin'
    )

    direct_subcategory_schema = user_category.get_subcategory('usersession').generate_category_schema(
        user,
        language_context,
        admin_schema,
    )
    direct_subcategory_fields = direct_subcategory_schema.table_info.table_schema.fields

    assert 'user_id' in direct_subcategory_fields, (
        'user_id must exist in direct UserSessionAdmin schema; '
        'otherwise the test does not prove reverse FK removal in subcategory context'
    )

    group_schema = schema.CategoryGroup(
        slug='users',
        title='Users',
        subcategories=[user_category],
    ).generate_category_schema(user, language_context, admin_schema)

    assert 'user' in group_schema.categories
