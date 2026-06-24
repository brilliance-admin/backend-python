from unittest import mock

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from brilliance_admin import auth, schema, sqlalchemy
from brilliance_admin.exceptions import AdminAPIException
from brilliance_admin.schema.table.admin_action import ActionData
from brilliance_admin.translations import TranslateText as _
from brilliance_admin.utils import DeserializeAction
from example.sections.models import (
    Currency, CurrencyFactory, Fee, FeeAccrualType, FeeFactory, FeeFixType, FeeOperationType, FeeSourceType,
    FeeTypeFactory, Merchant, MerchantFactory, Terminal, TerminalFactory, TerminalStatuses)
from tests.sqlalchemy.test_sqlalcmeny_schema import FIELDS


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
    fee_type = await FeeTypeFactory()

    create_data = {
        'manager_id': 0,
        'merchant_id': merchant.id,
        'currency_id': currency.id,
        'status': {'value': 'error', 'title': 'Error'},
        'description': 'test',
        'title': 'test',
        'created_at': '2026-01-20T20:33:40.055184Z',
        'registered_delay': 60,
        'fees': [
            {
                'title': 'Terminal fee',
                'accrual_type': {'value': 'above', 'title': 'Above (from user)'},
                'percent_part': True,
                'percent': '1.500',
                'fix_part': True,
                'fix_type': {'value': 'additional', 'title': 'Additional'},
                'fix_amount': 100,
                'active': True,
                'source': {'value': 'payplanet', 'title': 'Payplanet fee'},
                'operation_type': {'value': 'refund', 'title': 'Refund'},
                'fee_type_id': {'key': fee_type.id, 'title': fee_type.title},
            },
        ],
    }
    create_result: schema.CreateResult = await category.create(
        data=create_data,
        user=user,
        language_context=language_context,
        debug=True,
    )

    assert create_result.pk == 1

    async with postgres_sessionmaker() as session:
        terminal = (await session.execute(
            select(Terminal)
            .options(selectinload(Terminal.fees).selectinload(Fee.fee_type))
            .where(Terminal.id == create_result.pk)
        )).scalar_one()

    assert terminal.manager_id == create_data['manager_id']
    assert terminal.merchant_id == merchant.id
    assert terminal.currency_id == currency.id
    assert terminal.status == create_data['status']['value']
    assert terminal.description == create_data['description']
    assert terminal.title == create_data['title']
    assert terminal.registered_delay == create_data['registered_delay']
    assert terminal.created_at.isoformat() == '2026-01-20T20:33:40.055184+00:00'

    assert len(terminal.fees) == 1
    fee = terminal.fees[0]
    assert fee.title == 'Terminal fee'
    assert fee.accrual_type == 'above'
    assert fee.percent_part is True
    assert str(fee.percent) == '1.500'
    assert fee.fix_part is True
    assert fee.fix_type == 'additional'
    assert fee.fix_amount == 100
    assert fee.active is True
    assert fee.source == 'payplanet'
    assert fee.operation_type == 'refund'
    assert fee.fee_type_id == fee_type.id
    assert fee.terminal_id == terminal.id


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
        'code': 'related_not_found',
        'field_errors': None,
        'message': 'Ошибка при обновлении связей поля merchant_id: запись Merchant с ключем pk=100 не найдена. Возможно запись более недоступна.',
    }
    context = {'language_context': language_context}
    assert e.value.get_error().model_dump(context=context) == expected


@pytest.mark.asyncio
async def test_create_bad_inline_fk_rollbacks_all(postgres_sessionmaker, language_context):
    """
    Проверяет, что ошибка в related поле новой inline-строки на CREATE
    откатывает и родителя, и все дочерние записи.
    """
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
        'registered_delay': 60,
        'fees': [
            {
                'title': 'Broken fee',
                'accrual_type': {'value': 'above', 'title': 'Above (from user)'},
                'percent_part': True,
                'percent': '1.500',
                'fix_part': True,
                'fix_type': {'value': 'additional', 'title': 'Additional'},
                'fix_amount': 100,
                'active': True,
                'source': {'value': 'payplanet', 'title': 'Payplanet fee'},
                'operation_type': {'value': 'refund', 'title': 'Refund'},
                'fee_type_id': {'key': 999999, 'title': 'missing'},
            },
        ],
    }

    with pytest.raises(AdminAPIException) as e:
        await category.create(
            data=create_data,
            user=user,
            language_context=language_context,
            debug=True,
        )

    context = {'language_context': language_context}
    assert e.value.get_error().model_dump(context=context) == {
        'code': 'related_not_found',
        'field_errors': None,
        'message': 'Ошибка при обновлении связей поля fee_type_id: запись FeeType с ключем pk=999999 не найдена. Возможно запись более недоступна.',
    }

    async with postgres_sessionmaker() as session:
        terminals = (await session.execute(select(Terminal))).scalars().all()
        fees = (await session.execute(select(Fee))).scalars().all()

    assert terminals == []
    assert fees == []


@pytest.mark.asyncio
async def test_create_inline_empty_dict_validation_error(postgres_sessionmaker, language_context):
    """
    Проверяет, что пустая новая inline-строка на CREATE падает на валидации
    до обращения к ограничениям базы данных.
    """
    category = get_category(postgres_sessionmaker)
    user = auth.UserABC(username="test")
    merchant = await MerchantFactory()
    currency = await CurrencyFactory()

    with pytest.raises(AdminAPIException) as e:
        await category.create(
            data={
                'manager_id': 0,
                'merchant_id': merchant.id,
                'currency_id': currency.id,
                'status': {'value': 'error', 'title': 'Error'},
                'description': 'test',
                'title': 'test',
                'registered_delay': 60,
                'fees': [{}],
            },
            user=user,
            language_context=language_context,
            debug=True,
        )

    context = {'language_context': language_context}
    assert e.value.get_error().model_dump(context=context) == {
        'code': 'validation_error',
        'field_errors': {
            'fees': {
                'code': 'inline_nested',
                'field_slug': None,
                'message': [
                    {
                        'title': {
                            'code': 'field_required',
                            'field_slug': None,
                            'message': 'Field is required',
                        },
                        'fee_type_id': {
                            'code': 'field_required',
                            'field_slug': None,
                            'message': 'Field is required',
                        },
                        'fix_amount': {
                            'code': None,
                            'field_slug': None,
                            'message': 'Значение должно быть не меньше 1',
                        },
                    },
                ],
            },
        },
        'message': None,
    }


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
async def test_delete(postgres_sessionmaker, language_context):
    category = get_category(postgres_sessionmaker)
    user = auth.UserABC(username="test")
    terminal = await TerminalFactory(
        merchant=await MerchantFactory(title="Test merch"),
        currency=await CurrencyFactory(),
    )

    result = await category.delete(
        user=user,
        language_context=language_context,
        debug=True,
        action_data=ActionData(
            pks=[terminal.id],
            send_to_all=False,
            form_data={},
            filters={},
            search=None,
        ),
    )

    assert result.message == _('deleted_successfully')

    async with postgres_sessionmaker() as session:
        deleted_terminal = await session.get(Terminal, terminal.id)

    assert deleted_terminal is None


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
async def test_update_inline_existing_and_create_new(postgres_sessionmaker, language_context):
    category = get_category(postgres_sessionmaker)
    user = auth.UserABC(username="test")
    merchant = await MerchantFactory(title="Test merch")
    currency = await CurrencyFactory()
    existing_fee_type = await FeeTypeFactory(title='existing')
    new_fee_type = await FeeTypeFactory(title='new')
    terminal = await TerminalFactory(
        merchant=merchant,
        currency=currency,
        description='old description',
    )
    existing_fee = await FeeFactory(
        terminal=terminal,
        fee_type=existing_fee_type,
        title='Old fee',
        accrual_type=FeeAccrualType.BELLOW.value,
        percent_part=True,
        percent='1.000',
        fix_part=False,
        fix_type=FeeFixType.MINIMAL.value,
        fix_amount=10,
        active=True,
        source=FeeSourceType.PAYPLANET.value,
        operation_type=FeeOperationType.BY_SETTINGS.value,
    )
    deleted_fee = await FeeFactory(
        terminal=terminal,
        fee_type=existing_fee_type,
        title='Deleted fee',
        accrual_type=FeeAccrualType.BELLOW.value,
        percent_part=True,
        percent='4.000',
        fix_part=False,
        fix_type=FeeFixType.MINIMAL.value,
        fix_amount=40,
        active=True,
        source=FeeSourceType.PAYPLANET.value,
        operation_type=FeeOperationType.BY_SETTINGS.value,
    )

    update_data = {
        'description': 'new description',
        'fees': [
            {
                'id': existing_fee.id,
                'title': 'Updated fee',
                'accrual_type': {'value': 'above', 'title': 'Above (from user)'},
                'percent_part': True,
                'percent': '2.500',
                'fix_part': True,
                'fix_type': {'value': 'additional', 'title': 'Additional'},
                'fix_amount': 25,
                'active': False,
                'source': {'value': 'payplanet', 'title': 'Payplanet fee'},
                'operation_type': {'value': 'refund', 'title': 'Refund'},
                'fee_type_id': {'key': existing_fee_type.id, 'title': existing_fee_type.title},
            },
            {
                'title': 'New fee',
                'accrual_type': {'value': 'above', 'title': 'Above (from user)'},
                'percent_part': True,
                'percent': '3.500',
                'fix_part': True,
                'fix_type': {'value': 'additional', 'title': 'Additional'},
                'fix_amount': 50,
                'active': True,
                'source': {'value': 'payplanet', 'title': 'Payplanet fee'},
                'operation_type': {'value': 'refund', 'title': 'Refund'},
                'fee_type_id': {'key': new_fee_type.id, 'title': new_fee_type.title},
            },
        ],
    }

    update_result = await category.update(
        pk=terminal.id,
        data=update_data,
        user=user,
        language_context=language_context,
        debug=True,
    )
    assert update_result == schema.UpdateResult(pk=terminal.id)

    async with postgres_sessionmaker() as session:
        updated_terminal = (await session.execute(
            select(Terminal)
            .options(selectinload(Terminal.fees).selectinload(Fee.fee_type))
            .where(Terminal.id == terminal.id)
        )).scalar_one()

    assert updated_terminal.description == 'new description'
    assert len(updated_terminal.fees) == 2

    updated_existing_fee = next(fee for fee in updated_terminal.fees if fee.id == existing_fee.id)
    new_fee = next(fee for fee in updated_terminal.fees if fee.id != existing_fee.id)

    assert updated_existing_fee.title == 'Updated fee'
    assert str(updated_existing_fee.percent) == '2.500'
    assert updated_existing_fee.fix_amount == 25
    assert updated_existing_fee.active is False
    assert updated_existing_fee.operation_type == FeeOperationType.REFUND.value
    assert updated_existing_fee.fee_type_id == existing_fee_type.id

    assert new_fee.title == 'New fee'
    assert str(new_fee.percent) == '3.500'
    assert new_fee.fix_amount == 50
    assert new_fee.active is True
    assert new_fee.operation_type == FeeOperationType.REFUND.value
    assert new_fee.fee_type_id == new_fee_type.id

    assert all(fee.id != deleted_fee.id for fee in updated_terminal.fees)


@pytest.mark.asyncio
async def test_update_inline_retrieve_and_list_show_actual_state(postgres_sessionmaker, language_context):
    """
    Проверяет, что после сложного inline update retrieve и list
    возвращают актуальное состояние: updated есть, created есть, deleted нет.
    """
    category = get_category(postgres_sessionmaker)
    user = auth.UserABC(username="test")
    merchant = await MerchantFactory(title="Test merch")
    currency = await CurrencyFactory()
    existing_fee_type = await FeeTypeFactory(title='existing')
    new_fee_type = await FeeTypeFactory(title='new')
    terminal = await TerminalFactory(
        merchant=merchant,
        currency=currency,
        description='old description',
        title='Terminal title',
    )
    existing_fee = await FeeFactory(
        terminal=terminal,
        fee_type=existing_fee_type,
        title='Old fee',
        accrual_type=FeeAccrualType.BELLOW.value,
        percent_part=True,
        percent='1.000',
        fix_part=False,
        fix_type=FeeFixType.MINIMAL.value,
        fix_amount=10,
        active=True,
        source=FeeSourceType.PAYPLANET.value,
        operation_type=FeeOperationType.BY_SETTINGS.value,
    )
    deleted_fee = await FeeFactory(
        terminal=terminal,
        fee_type=existing_fee_type,
        title='Deleted fee',
        accrual_type=FeeAccrualType.BELLOW.value,
        percent_part=True,
        percent='4.000',
        fix_part=False,
        fix_type=FeeFixType.MINIMAL.value,
        fix_amount=40,
        active=True,
        source=FeeSourceType.PAYPLANET.value,
        operation_type=FeeOperationType.BY_SETTINGS.value,
    )

    await category.update(
        pk=terminal.id,
        data={
            'description': 'new description',
            'fees': [
                {
                    'id': existing_fee.id,
                    'title': 'Updated fee',
                    'accrual_type': {'value': 'above', 'title': 'Above (from user)'},
                    'percent_part': True,
                    'percent': '2.500',
                    'fix_part': True,
                    'fix_type': {'value': 'additional', 'title': 'Additional'},
                    'fix_amount': 25,
                    'active': False,
                    'source': {'value': 'payplanet', 'title': 'Payplanet fee'},
                    'operation_type': {'value': 'refund', 'title': 'Refund'},
                    'fee_type_id': {'key': existing_fee_type.id, 'title': existing_fee_type.title},
                },
                {
                    'title': 'New fee',
                    'accrual_type': {'value': 'above', 'title': 'Above (from user)'},
                    'percent_part': True,
                    'percent': '3.500',
                    'fix_part': True,
                    'fix_type': {'value': 'additional', 'title': 'Additional'},
                    'fix_amount': 50,
                    'active': True,
                    'source': {'value': 'payplanet', 'title': 'Payplanet fee'},
                    'operation_type': {'value': 'refund', 'title': 'Refund'},
                    'fee_type_id': {'key': new_fee_type.id, 'title': new_fee_type.title},
                },
            ],
        },
        user=user,
        language_context=language_context,
        debug=True,
    )

    retrieve_result = await category.retrieve(
        pk=terminal.id,
        user=user,
        language_context=language_context,
        debug=True,
    )
    list_result = await category.get_list(
        list_data=schema.ListData(filters={'id': terminal.id}),
        user=user,
        language_context=language_context,
        debug=True,
    )

    retrieved_fees = retrieve_result.data['fees']
    listed_fees = list_result.data[0]['fees']

    assert retrieve_result.data['description'] == 'new description'
    assert list_result.data[0]['description'] == 'new description'
    assert len(retrieved_fees) == 2
    assert len(listed_fees) == 2
    assert {fee['title'] for fee in retrieved_fees} == {'Updated fee', 'New fee'}
    assert {fee['title'] for fee in listed_fees} == {'Updated fee', 'New fee'}
    assert all(fee['id'] != deleted_fee.id for fee in retrieved_fees)
    assert all(fee['id'] != deleted_fee.id for fee in listed_fees)


@pytest.mark.asyncio
async def test_update_inline_deserialize_keeps_pk(postgres_sessionmaker):
    """
    Проверяет, что inline deserialize на UPDATE не теряет pk существующей строки.
    Иначе update-path ошибочно воспринимает запись как новую CREATE.
    """
    category = get_category(postgres_sessionmaker)
    fee_type = await FeeTypeFactory(title='existing')
    existing_fee = await FeeFactory(fee_type=fee_type)

    result = await category.table_schema.get_field('fees').deserialize_field(
        [
            {
                'id': existing_fee.id,
                'title': 'Updated fee',
                'accrual_type': {'value': 'above', 'title': 'Above (from user)'},
                'percent_part': True,
                'percent': '2.500',
                'fix_part': True,
                'fix_type': {'value': 'additional', 'title': 'Additional'},
                'fix_amount': 25,
                'active': False,
                'source': {'value': 'payplanet', 'title': 'Payplanet fee'},
                'operation_type': {'value': 'refund', 'title': 'Refund'},
                'fee_type_id': {'key': fee_type.id, 'title': fee_type.title},
            },
        ],
        DeserializeAction.UPDATE,
        {'model': Terminal},
    )

    assert result[0]['id'] == existing_fee.id


@pytest.mark.asyncio
async def test_update_inline_empty_dict_validation_error(postgres_sessionmaker, language_context):
    category = get_category(postgres_sessionmaker)
    user = auth.UserABC(username="test")
    terminal = await TerminalFactory(
        merchant=await MerchantFactory(title="Test merch"),
        currency=await CurrencyFactory(),
    )

    with pytest.raises(AdminAPIException) as e:
        await category.update(
            pk=terminal.id,
            data={'fees': [{}]},
            user=user,
            language_context=language_context,
            debug=True,
        )

    context = {'language_context': language_context}
    assert e.value.get_error().model_dump(context=context) == {
        'code': 'validation_error',
        'field_errors': {
            'fees': {
                'code': 'inline_nested',
                'field_slug': None,
                'message': [
                    {
                        'title': {
                            'code': 'field_required',
                            'field_slug': None,
                            'message': 'Field is required',
                        },
                        'fee_type_id': {
                            'code': 'field_required',
                            'field_slug': None,
                            'message': 'Field is required',
                        },
                        'fix_amount': {
                            'code': None,
                            'field_slug': None,
                            'message': 'Значение должно быть не меньше 1',
                        },
                    },
                ],
            },
        },
        'message': None,
    }


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
