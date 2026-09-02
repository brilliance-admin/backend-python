from contextlib import asynccontextmanager
from copy import deepcopy

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from example.config import settings


ASYNC_ENGINE = create_async_engine(
    settings.get_connection_string(),
    future=True,
    echo=False,
)


@event.listens_for(ASYNC_ENGINE.sync_engine, "connect")
def _enable_fk_async(dbapi_connection, _):
    if ASYNC_ENGINE.sync_engine.dialect.name != 'sqlite':
        return

    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


async_sessionmaker_ = async_sessionmaker(
    ASYNC_ENGINE,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def recreate_tables_async():
    from example.sections.models import ModelBase

    async with ASYNC_ENGINE.begin() as conn:
        if ASYNC_ENGINE.sync_engine.dialect.name == 'postgresql':
            await conn.execute(text("DROP SCHEMA public CASCADE"))
            await conn.execute(text("CREATE SCHEMA public"))
        else:
            await conn.run_sync(ModelBase.metadata.drop_all)
        await conn.run_sync(ModelBase.metadata.create_all)


@asynccontextmanager
async def lifespan(app):
    await recreate_tables_async()

    from example.sections import models

    for country_index, (country_name, cities) in enumerate(models.COUNTRY_CITY_DATA.items(), start=1):
        country = await models.CountryFactory.create_async(
            id=country_index,
            name=country_name,
            code=models.COUNTRY_CODES[country_name],
        )
        for city_index, city_name in enumerate(cities, start=1):
            await models.CityFactory.create_async(
                id=(country_index - 1) * 5 + city_index,
                country_id=country.id,
                name=city_name,
            )

    await models.FeeTypeFactory.create_batch_async(5)
    await models.CurrencyFactory.create_batch_async(5)
    await models.TerminalFactory.create_batch_async(35)
    for _ in range(27):
        country_id = models.random.randint(1, len(models.COUNTRY_CITY_DATA))
        await models.UserFactory.create_async(
            country_id=country_id,
            city_id=(country_id - 1) * 5 + models.random.randint(1, 5),
        )
    await models.UserSessionFactory.create_batch_async(50)
    await models.PrivacyPolicyVersionFactory.create_batch_async(50)
    await models.MerchantFactory.create_batch_async(9)
    await models.MerchantFactory.create_async(provider_settings=deepcopy(models.BIG_JSON))

    yield
