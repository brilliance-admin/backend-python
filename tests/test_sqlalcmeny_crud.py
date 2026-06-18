from unittest import mock

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from brilliance_admin import auth, schema, sqlalchemy
from brilliance_admin.exceptions import AdminAPIException
from brilliance_admin.translations import TranslateText as _
from example.sections.models import (
    Currency, CurrencyFactory, Fee, FeeAccrualType, FeeFactory, FeeFixType, FeeOperationType, FeeSourceType,
    FeeTypeFactory, Merchant, MerchantFactory, Terminal, TerminalFactory, TerminalStatuses)
from tests.test_sqlalcmeny_schema import FIELDS


class FeeFieldsSchema(sqlalchemy.SQLAlchemyFieldsSchema):
    model = Fee
    extra_kwargs = {
        'fix_amount': {'min_value': 1},
    }


def get_category(postgres_sessionmaker):
    category = sqlalchemy.SQLAlchemyAdmin(
        model=Terminal,
        db_async_session=postgres_sessionmaker,
        table_schema=sqlalchemy.SQLAlchemyFieldsSchema(
            model=Terminal,
            fields=FIELDS,
            fees=sqlalchemy.SQLAlchemyInlineField(
                label=_('fees'),
                help_text=_('fees_help_text'),
                many=True,
                table_schema=FeeFieldsSchema(),
            ),
        ),
    )
    return category


@pytest.mark.asyncio
async def test_create(postgres_sessionmaker, language_context):
    category = get_category(postgres_sessionmaker)
    user = auth.UserABC(username="test")
    merchant = await MerchantFactory()
    currency = await CurrencyFactory()

    create_data = {
        'manager_id': 0,
        'merchant_id': merchant.id,
        'currency_id': currency.id,
        'status': {'value': 'error', 'title': 'Error'},
        'description': 'test',
        'title': 'test',
        'created_at': '2026-01-20T20:33:40.055184Z',
        'registered_delay': 60,
    }
    create_result: schema.CreateResult = await category.create(
        data=create_data,
        user=user,
        language_context=language_context,
        debug=True,
    )

    assert create_result.pk == 1


@pytest.mark.asyncio
async def test_create_bad_fk(postgres_sessionmaker, language_context):
    category = get_category(postgres_sessionmaker)
    user = auth.UserABC(username="test")
    merchant = await MerchantFactory()
    currency = await CurrencyFactory()

    create_data = {
        'manager_id': 1,
        'merchant_id': 100,
        'currency_id': currency.id,
        'status': {'value': 'error', 'title': 'Error'},
        'description': 'test',
        'title': 'test',
        'registered_delay': 60,
    }
    with pytest.raises(AdminAPIException) as e:
        schema.CreateResult = await category.create(
            data=create_data,
            user=user,
            language_context=language_context,
            debug=True,
        )
    expected = {
        'code': 'db_integrity_error',
        'field_errors': None,
        'message': 'Ошибка целостности базы данных: terminal.merchant_id',
    }
    context = {'language_context': language_context}
    assert e.value.get_error().model_dump(context=context) == expected


@pytest.mark.asyncio
async def test_retrieve(postgres_sessionmaker, language_context):
    category = get_category(postgres_sessionmaker)
    user = auth.UserABC(username="test")
    merchant = await MerchantFactory()
    currency = await CurrencyFactory()
    fee_type = await FeeTypeFactory()
    terminal = await TerminalFactory(
        title="test",
        description='test',
        status=TerminalStatuses.PROCESS.value,
        is_h2h=False,
        registered_delay=None,
        merchant=merchant,
        currency=currency,
    )
    await FeeFactory(
        terminal=terminal,
        fee_type=fee_type,
        title='Terminal fee',
        accrual_type=FeeAccrualType.ABOVE.value,
        percent_part=True,
        percent='1.500',
        fix_part=True,
        fix_type=FeeFixType.ADDITIONAL.value,
        fix_amount=100,
        active=True,
        source=FeeSourceType.PAYPLANET.value,
        operation_type=FeeOperationType.REFUND.value,
    )

    retrieve_result = await category.retrieve(
        pk=terminal.id,
        user=user,
        language_context=language_context,
        debug=True,
    )
    expected_data = {
        'manager_id': mock.ANY,
        'created_at': mock.ANY,
        'description': 'test',
        'currency_id': {
            'key': currency.id,
            'title': mock.ANY,
        },
        'status': {
            'title': _('statuses.process'),
            'value': 'process',
        },
        'title': 'test',
        'id': terminal.id,
        'is_h2h': False,
        'merchant_id': {'key': merchant.id, 'title': mock.ANY},
        'registered_delay': None,
        'secret_key': mock.ANY,
        'fees': [
            {
                'id': mock.ANY,
                'title': 'Terminal fee',
                'accrual_type': {
                    'title': 'Above (from user)',
                    'value': 'above',
                },
                'percent_part': True,
                'percent': mock.ANY,
                'fix_part': True,
                'fix_type': {
                    'title': 'Additional',
                    'value': 'additional',
                },
                'fix_amount': 100,
                'active': True,
                'source': {
                    'title': 'Payplanet fee',
                    'value': 'payplanet',
                },
                'operation_type': {
                    'title': 'Refund',
                    'value': 'refund',
                },
                'fee_type_id': {
                    'key': fee_type.id,
                    'title': fee_type.title,
                },
            },
        ],
    }
    assert retrieve_result.data == expected_data


@pytest.mark.asyncio
async def test_retrieve_currency(postgres_sessionmaker, language_context):
    category = sqlalchemy.SQLAlchemyAdmin(
        model=Currency,
        db_async_session=postgres_sessionmaker,
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
        debug=True,
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
async def test_create_bad_json(postgres_sessionmaker, language_context):
    category = sqlalchemy.SQLAlchemyAdmin(
        model=Merchant,
        db_async_session=postgres_sessionmaker,
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
            debug=True,
        )
    context = {'language_context': language_context}
    errors = {
        'code': 'validation_error',
        'field_errors': {
            'provider_settings': {
                'code': None,
                'field_slug': None,
                'message': "Некорректный тип данных: str; ожидается JSON",
            },
        },
        'message': None,
    }
    assert e.value.get_error().model_dump(context=context) == errors


@pytest.mark.asyncio
async def test_list(postgres_sessionmaker, language_context):
    category = get_category(postgres_sessionmaker)
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
        debug=True,
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
                'title': _('statuses.process'),
                'value': 'process',
            },
            'fees': mock.ANY,
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
async def test_update_related_one(postgres_sessionmaker, language_context):
    category = get_category(postgres_sessionmaker)
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
        debug=True,
    )
    assert update_result == schema.UpdateResult(pk=terminal.id)


@pytest.mark.asyncio
async def test_update_related_many(postgres_sessionmaker, language_context):
    category = sqlalchemy.SQLAlchemyAdmin(
        model=Currency,
        db_async_session=postgres_sessionmaker,
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
        debug=True,
    )
    assert update_result == schema.UpdateResult(pk=currency_rub.id)

    async with postgres_sessionmaker() as session:
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
async def test_update_bad_value_int16(postgres_sessionmaker, language_context):
    category = sqlalchemy.SQLAlchemyAdmin(
        model=Currency,
        db_async_session=postgres_sessionmaker,
        table_schema=sqlalchemy.SQLAlchemyFieldsSchema(
            model=Currency,
            fields=[
                'id',
                'num_code',
            ],
        ),
    )
    user = auth.UserABC(username="test")
    currency = await CurrencyFactory(title='RUB')

    update_data = {
        'num_code': 123123123,
    }
    with pytest.raises(AdminAPIException) as e:
        await category.update(
            pk=currency.id,
            data=update_data,
            user=user,
            language_context=language_context,
            debug=True,
        )
    context = {'language_context': language_context}
    assert e.value.get_error().model_dump(context=context) == {
        "code": "validation_error",
        "field_errors": {
            "num_code": {
                "code": None,
                "field_slug": None,
                "message": "Значение должно быть не больше 32767"
            }
        },
        "message": None,
    }


@pytest.mark.asyncio
async def test_autocomplete(postgres_sessionmaker, language_context):
    category = get_category(postgres_sessionmaker)
    category = sqlalchemy.SQLAlchemyAdmin(model=Terminal, db_async_session=postgres_sessionmaker)

    user = auth.UserABC(username="test")
    autocomplete_result = await category.autocomplete(
        data=schema.AutocompleteData(
            field_slug='merchant_id',
        ),
        user=user,
        language_context=language_context,
        debug=True,
    )
    assert autocomplete_result == schema.AutocompleteResult()
