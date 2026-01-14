from datetime import datetime

import pytest

from brilliance_admin import auth, schema, sqlalchemy
from brilliance_admin.schema import admin_schema
from example.sections.models import Currency, CurrencyFactory, MerchantFactory, Terminal, TerminalFactory


@pytest.mark.asyncio
async def test_list_filter(sqlite_sessionmaker, language_context):
    category = sqlalchemy.SQLAlchemyAdmin(
        model=Terminal,
        db_async_session=sqlite_sessionmaker,
        table_schema=sqlalchemy.SQLAlchemyFieldsSchema(
            model=Terminal,
            fields=['id'],
        ),
        table_filters=sqlalchemy.SQLAlchemyFieldsSchema(
            model=Terminal,
            fields=['id', 'title', 'created_at'],
            created_at=schema.DateTimeField(range=True),
        ),
    )
    user = auth.UserABC(username="test")

    merchant = await MerchantFactory(title="Test merch")
    currency = await CurrencyFactory()
    terminal_1 = await TerminalFactory(title='Test terminal', merchant=merchant, currency=currency)
    terminal_2 = await TerminalFactory(title='Test terminal second', merchant=merchant, currency=currency)
    await TerminalFactory(title='other', merchant=merchant, currency=currency)

    list_result: dict = await category.get_list(
        list_data=schema.ListData(filters={'id': terminal_1.id}),
        user=user,
        language_context=language_context,
        admin_schema=admin_schema,
    )
    assert list_result == schema.TableListResult(
        data=[{'id': terminal_1.id}], total_count=1
    ), 'поиск по id'

    list_result: dict = await category.get_list(
        list_data=schema.ListData(filters={'title': 'Test terminal second'}),
        user=user,
        language_context=language_context,
        admin_schema=admin_schema,
    )
    assert list_result == schema.TableListResult(
        data=[{'id': terminal_2.id}], total_count=1
    ), 'Полная строка'

    list_result: dict = await category.get_list(
        list_data=schema.ListData(filters={'title': 'Test%'}),
        user=user,
        language_context=language_context,
        admin_schema=admin_schema,
    )
    assert list_result == schema.TableListResult(
        data=[{'id': terminal_2.id}, {'id': terminal_1.id}], total_count=2
    ), 'Частичное вхождение'

    terminal_old = await TerminalFactory(
        title='Old terminal',
        merchant=merchant,
        currency=currency,
        created_at=datetime(2023, 6, 1, 12, 0, 0),
    )
    list_result: dict = await category.get_list(
        list_data=schema.ListData(filters={'created_at': {'from': '2022-12-04T18:55:00', 'to': '2023-12-17T18:55:00'}}),
        user=user,
        language_context=language_context,
        admin_schema=admin_schema,
    )
    assert list_result == schema.TableListResult(
        data=[{'id': terminal_old.id}], total_count=1
    ), 'Фильтр по периоду'


@pytest.mark.asyncio
async def test_list_search(sqlite_sessionmaker, language_context):
    category = sqlalchemy.SQLAlchemyAdmin(
        search_fields=['title'],
        model=Terminal,
        db_async_session=sqlite_sessionmaker,
        table_schema=sqlalchemy.SQLAlchemyFieldsSchema(
            model=Terminal,
            fields=['id'],
        ),
    )
    user = auth.UserABC(username="test")

    merchant = await MerchantFactory(title="Test merch")
    currency = await CurrencyFactory()
    terminal_1 = await TerminalFactory(title='Test terminal', merchant=merchant, currency=currency)
    terminal_2 = await TerminalFactory(title='Test terminal second', merchant=merchant, currency=currency)
    terminal_3 = await TerminalFactory(title='other', merchant=merchant, currency=currency)
    await TerminalFactory(title='other', merchant=merchant, currency=currency)

    list_result: dict = await category.get_list(
        list_data=schema.ListData(search='Test%'),
        user=user,
        language_context=language_context,
        admin_schema=admin_schema,
    )
    assert list_result == schema.TableListResult(
        data=[{'id': terminal_2.id}, {'id': terminal_1.id}], total_count=2,
    ), 'Поиск по title'


@pytest.mark.asyncio
async def test_filter_related_one(sqlite_sessionmaker, language_context):
    category = sqlalchemy.SQLAlchemyAdmin(
        model=Currency,
        db_async_session=sqlite_sessionmaker,
        table_schema=sqlalchemy.SQLAlchemyFieldsSchema(
            model=Currency,
            fields=['id'],
        ),
        table_filters=sqlalchemy.SQLAlchemyFieldsSchema(
            model=Currency,
            fields=['terminals'],
        ),
    )
    user = auth.UserABC(username="test")

    currency_rub = await CurrencyFactory(title='RUB')

    merchant = await MerchantFactory()
    terminal_1 = await TerminalFactory(merchant=merchant, currency=currency_rub)
    terminal_2 = await TerminalFactory(merchant=merchant, currency=currency_rub)

    currency_usd = await CurrencyFactory(title='USD')
    terminal_3 = await TerminalFactory(merchant=merchant, currency=currency_usd)

    list_result: dict = await category.get_list(
        list_data=schema.ListData(filters={
            'terminals': [{'key': terminal_1.id, 'title': 'test'}, {'key': terminal_2.id, 'title': 'test'}],
        }),
        user=user,
        language_context=language_context,
        admin_schema=admin_schema,
    )
    assert list_result == schema.TableListResult(
        data=[{'id': currency_rub.id}], total_count=1
    ), 'Фильтр по many related'


@pytest.mark.asyncio
async def test_filter_related_many(sqlite_sessionmaker, language_context):
    category = sqlalchemy.SQLAlchemyAdmin(
        model=Terminal,
        db_async_session=sqlite_sessionmaker,
        table_schema=sqlalchemy.SQLAlchemyFieldsSchema(
            model=Terminal,
            fields=['id'],
        ),
        table_filters=sqlalchemy.SQLAlchemyFieldsSchema(
            model=Terminal,
            fields=['merchant_id'],
        ),
    )
    user = auth.UserABC(username="test")

    currency = await CurrencyFactory()

    merchant_1 = await MerchantFactory()
    terminal_1 = await TerminalFactory(merchant=merchant_1, currency=currency)

    merchant_2 = await MerchantFactory()
    terminal_2 = await TerminalFactory(merchant=merchant_2, currency=currency)

    list_result: dict = await category.get_list(
        list_data=schema.ListData(filters={
            'merchant_id': {'key': merchant_2.id, 'title': 'test'}
        }),
        user=user,
        language_context=language_context,
        admin_schema=admin_schema,
    )
    assert list_result == schema.TableListResult(data=[{'id': terminal_2.id}], total_count=1), 'Фильтр по related'


@pytest.mark.asyncio
async def test_list_bad_search_field(sqlite_sessionmaker):
    with pytest.raises(AttributeError) as e:
        sqlalchemy.SQLAlchemyAdmin(
            search_fields=['no_field'],
            model=Terminal,
            db_async_session=sqlite_sessionmaker,
        )

    assert str(e.value) == 'SQLAlchemyAdmin: search field "no_field" not found in model Terminal'


@pytest.mark.asyncio
async def test_ordering(sqlite_sessionmaker, language_context):
    category = sqlalchemy.SQLAlchemyAdmin(
        model=Terminal,
        db_async_session=sqlite_sessionmaker,
        ordering_fields=['id'],
        table_schema=sqlalchemy.SQLAlchemyFieldsSchema(
            model=Terminal,
            fields=['id'],
        ),
    )
    user = auth.UserABC(username="test")

    currency = await CurrencyFactory()
    merchant = await MerchantFactory()

    terminal_1 = await TerminalFactory(merchant=merchant, currency=currency)
    terminal_2 = await TerminalFactory(merchant=merchant, currency=currency)

    list_result: dict = await category.get_list(
        list_data=schema.ListData(ordering='id'),
        user=user,
        language_context=language_context,
        admin_schema=admin_schema,
    )
    assert list_result == schema.TableListResult(
        data=[{'id': terminal_1.id}, {'id': terminal_2.id, }], total_count=2
    ), 'сортировка по возрастанию'

    list_result: dict = await category.get_list(
        list_data=schema.ListData(ordering='-id'),
        user=user,
        language_context=language_context,
        admin_schema=admin_schema,
    )
    assert list_result == schema.TableListResult(
        data=[{'id': terminal_2.id}, {'id': terminal_1.id, }], total_count=2
    ), 'сортировка по убыванию'
