import pytest

from brilliance_admin import auth, schema
from example.sections.merchant import MerchantAdmin
from example.sections.models import CurrencyFactory, MerchantFactory, TerminalFactory
from example.sections.terminal import TerminalAdmin


@pytest.mark.asyncio
async def test_subcategory_list(
        postgres_sessionmaker, language_context):
    """
    Проверяет, что список сабкатегории merchant -> terminal
    возвращает только терминалы выбранного merchant по parent_pk.
    """
    merchant_category = MerchantAdmin(
        db_async_session=postgres_sessionmaker,
        subcategories=[
            TerminalAdmin(db_async_session=postgres_sessionmaker),
        ],
    )
    terminals_subcategory = merchant_category.get_subcategory('terminal')
    assert terminals_subcategory
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
