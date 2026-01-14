from unittest import mock

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from brilliance_admin import auth, schema, sqlalchemy
from brilliance_admin.exceptions import AdminAPIException
from brilliance_admin.schema import admin_schema
from brilliance_admin.translations import TranslateText
from example.sections.models import (
    Currency, CurrencyFactory, Merchant, MerchantFactory, Terminal, TerminalFactory, TerminalStatuses)
from tests.test_sqlalcmeny_schema import FIELDS


def get_category(sqlite_sessionmaker):
    category = sqlalchemy.SQLAlchemyAdmin(
        model=Terminal,
        db_async_session=sqlite_sessionmaker,
        table_schema=sqlalchemy.SQLAlchemyFieldsSchema(
            model=Terminal,
            fields=FIELDS,
        ),
    )
    return category


@pytest.mark.asyncio
async def test_create(sqlite_sessionmaker, language_context):
    category = get_category(sqlite_sessionmaker)
    user = auth.UserABC(username="test")
    merchant = await MerchantFactory()
    currency = await CurrencyFactory()

    create_data = {
        'manager_id': 0,
        'merchant_id': merchant.id,
        'currency_id': currency.id,
        'status': 'test',
        'description': 'test',
        'title': 'test',
    }
    create_result: schema.CreateResult = await category.create(
        data=create_data,
        user=user,
        language_context=language_context,
        admin_schema=admin_schema,
    )

    assert create_result.pk == 1


@pytest.mark.asyncio
async def test_create_bad_fk(sqlite_sessionmaker, language_context):
    category = get_category(sqlite_sessionmaker)
    user = auth.UserABC(username="test")
    merchant = await MerchantFactory()
    currency = await CurrencyFactory()

    create_data = {
        'manager_id': 1,
        'merchant_id': 100,
        'currency_id': currency.id,
        'status': 'test',
        'description': 'test',
        'title': 'test',
    }
    with pytest.raises(AdminAPIException) as e:
        schema.CreateResult = await category.create(
            data=create_data,
            user=user,
            language_context=language_context,
            admin_schema=admin_schema,
        )
    assert e.value.get_error().message == 'NOT NULL constraint failed: terminal.merchant_id'


@pytest.mark.asyncio
async def test_retrieve(sqlite_sessionmaker, language_context):
    category = get_category(sqlite_sessionmaker)
    user = auth.UserABC(username="test")
    merchant = await MerchantFactory()
    currency = await CurrencyFactory()
    terminal = await TerminalFactory(
        title="test",
        description='test',
        status=TerminalStatuses.PROCESS.value,
        is_h2h=False,
        registered_delay=None,
        merchant=merchant,
        currency=currency,
    )

    retrieve_result = await category.retrieve(
        pk=terminal.id,
        user=user,
        language_context=language_context,
        admin_schema=admin_schema,
    )
    expected_data = {
        'manager_id': mock.ANY,
        'created_at': mock.ANY,
        'description': 'test',
        'currency_id': {
            'key': currency.id,
            'title': mock.ANY,
        },
        'fee_id': None,
        'status': {
            'title': TranslateText('statuses.process'),
            'value': 'process',
        },
        'title': 'test',
        'id': terminal.id,
        'is_h2h': False,
        'merchant_id': {'key': merchant.id, 'title': mock.ANY},
        'registered_delay': None,
        'secret_key': mock.ANY,
    }
    assert retrieve_result.data == expected_data


@pytest.mark.asyncio
async def test_retrieve_currency(sqlite_sessionmaker, language_context):
    category = sqlalchemy.SQLAlchemyAdmin(
        model=Currency,
        db_async_session=sqlite_sessionmaker,
        table_schema=sqlalchemy.SQLAlchemyFieldsSchema(
            model=Currency,
            fields=[
                'id',
                'terminals',
            ],
        ),
    )
    terminals_field = category.table_schema.get_field('terminals')
    assert terminals_field._type == "related"
    assert terminals_field.rel_name == "terminals"
    assert terminals_field.many is True

    user = auth.UserABC(username="test")
    merchant = await MerchantFactory()
    currency = await CurrencyFactory()
    terminal_1 = await TerminalFactory(
        merchant=merchant,
        currency=currency,
        title='First',
    )
    terminal_2 = await TerminalFactory(
        merchant=merchant,
        currency=currency,
        title='Second',
    )

    retrieve_result = await category.retrieve(
        pk=currency.id,
        user=user,
        language_context=language_context,
        admin_schema=admin_schema,
    )
    expected_data = {
        'id': currency.id,
        'terminals': [
            {'key': terminal_1.id, 'title': 'First'},
            {'key': terminal_2.id, 'title': 'Second'},
        ],
    }
    assert retrieve_result.data == expected_data, retrieve_result.data


@pytest.mark.asyncio
async def test_create_bad_json(sqlite_sessionmaker, language_context):
    category = sqlalchemy.SQLAlchemyAdmin(
        model=Merchant,
        db_async_session=sqlite_sessionmaker,
        table_schema=sqlalchemy.SQLAlchemyFieldsSchema(
            model=Merchant,
            fields=[
                'title',
                'provider_settings',
            ],
        ),
    )
    user = auth.UserABC(username="test")
    create_data = {
        'title': 'test',
        'provider_settings': 'not json',
    }
    with pytest.raises(AdminAPIException) as e:
        await category.create(
            data=create_data,
            user=user,
            language_context=language_context,
            admin_schema=admin_schema,
        )
    context = {'language_context': language_context}
    errors = {
        'code': 'validation_error',
        'field_errors': {
            'provider_settings': {
                'code': None,
                'field_slug': None,
                'message': "Некорректный тип данных: <class 'str'>; ожидается JSON",
            },
        },
        'message': 'Validation error',
    }
    assert e.value.get_error().model_dump(context=context) == errors


@pytest.mark.asyncio
async def test_list(sqlite_sessionmaker, language_context):
    category = get_category(sqlite_sessionmaker)
    user = auth.UserABC(username="test")
    await TerminalFactory(
        is_h2h=False,
        registered_delay=None,
        title='Test terminal',
        description="description",
        status=TerminalStatuses.PROCESS.value,
        merchant=await MerchantFactory(title="Test merch"),
        currency=await CurrencyFactory(),
    )

    list_result: dict = await category.get_list(
        list_data=schema.ListData(
            filters={
                'id': '',
            }
        ),
        user=user,
        language_context=language_context,
        admin_schema=admin_schema,
    )
    data = [
        {
            'manager_id': mock.ANY,
            'created_at': mock.ANY,
            'currency_id': {
                'key': 1,
                'title': mock.ANY,
            },
            'status': {
                'title': TranslateText('statuses.process'),
                'value': 'process',
            },
            'fee_id': None,
            'description': 'description',
            'id': 1,
            'is_h2h': False,
            'merchant_id': {
                'key': 1,
                'title': mock.ANY,
            },
            'registered_delay': None,
            'secret_key': mock.ANY,
            'title': 'Test terminal',
        },
    ]
    expected_create = schema.TableListResult(
        data=data,
        total_count=1,
    )
    assert list_result == expected_create


@pytest.mark.asyncio
async def test_update_related_one(sqlite_sessionmaker, language_context):
    category = get_category(sqlite_sessionmaker)
    user = auth.UserABC(username="test")
    terminal = await TerminalFactory(
        merchant=await MerchantFactory(title="Test merch"),
        currency=await CurrencyFactory(),
    )
    new_merchant = await MerchantFactory(title="New merch")

    update_data = {
        'merchant_id': {'key': new_merchant.id, 'title': '123'},
        'description': 'new description',
    }
    update_result = await category.update(
        pk=terminal.id,
        data=update_data,
        user=user,
        language_context=language_context,
        admin_schema=admin_schema,
    )
    assert update_result == schema.UpdateResult(pk=terminal.id)


@pytest.mark.asyncio
async def test_update_related_many(sqlite_sessionmaker, language_context):
    category = sqlalchemy.SQLAlchemyAdmin(
        model=Currency,
        db_async_session=sqlite_sessionmaker,
        table_schema=sqlalchemy.SQLAlchemyFieldsSchema(
            model=Currency,
            fields=[
                'id',
                'terminals',
            ],
        ),
    )
    user = auth.UserABC(username="test")

    currency_rub = await CurrencyFactory(title='RUB')
    currency_usd = await CurrencyFactory(title='USD')
    terminal_1 = await TerminalFactory(
        merchant=await MerchantFactory(title="Test merch"),
        currency=currency_usd,
    )
    terminal_2 = await TerminalFactory(
        merchant=await MerchantFactory(title="Test merch"),
        currency=currency_usd,
    )

    update_data = {
        'terminals': [
            {'key': terminal_1.id, 'title': 'test'},
            {'key': terminal_2.id, 'title': 'test'},
        ],
    }
    update_result = await category.update(
        pk=currency_rub.id,
        data=update_data,
        user=user,
        language_context=language_context,
        admin_schema=admin_schema,
    )
    assert update_result == schema.UpdateResult(pk=currency_rub.id)

    async with sqlite_sessionmaker() as session:
        updated_rub = (await session.execute(
            select(Currency)
            .options(selectinload(Currency.terminals))
            .where(Currency.id == currency_rub.id)
        )).scalar_one()

        updated_usd = (await session.execute(
            select(Currency)
            .options(selectinload(Currency.terminals))
            .where(Currency.id == currency_usd.id)
        )).scalar_one()

    assert sorted(t.id for t in updated_rub.terminals) == [terminal_1.id, terminal_2.id]
    assert sorted(t.id for t in updated_usd.terminals) == []


@pytest.mark.asyncio
async def test_autocomplete(sqlite_sessionmaker, language_context):
    category = get_category(sqlite_sessionmaker)
    category = sqlalchemy.SQLAlchemyAdmin(model=Terminal, db_async_session=sqlite_sessionmaker)

    user = auth.UserABC(username="test")
    autocomplete_result = await category.autocomplete(
        data=schema.AutocompleteData(
            field_slug='merchant_id',
        ),
        user=user,
        language_context=language_context,
        admin_schema=admin_schema,
    )
    assert autocomplete_result == schema.AutocompleteResult()
