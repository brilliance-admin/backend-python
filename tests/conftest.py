import pytest
from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

from brilliance_admin.translations import LanguageContext, LanguageManager
from example.sections.models import ModelBase


@pytest.fixture(scope="session")
async def postgres_container():
    with PostgresContainer(
        image="postgres:alpine",
        username="test_user",
        password="test_password",
        dbname="test_db",
    ) as postgres:
        yield postgres


@pytest.fixture(scope="session")
async def async_engine(postgres_container):
    url = postgres_container.get_connection_url().replace("psycopg2", "asyncpg")

    engine = create_async_engine(
        url,
        echo=True,
        poolclass=NullPool,
        pool_pre_ping=True,
        future=True,
    )

    async with engine.begin() as conn:
        await conn.run_sync(ModelBase.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(ModelBase.metadata.drop_all)

    await engine.dispose(close=True)


@pytest.fixture(scope="function")
async def async_session(async_engine):
    async with async_engine.connect() as conn:
        async with conn.begin() as trans:
            session_factory = async_sessionmaker(
                bind=conn,
                expire_on_commit=False,
                autoflush=False,
                class_=AsyncSession,
            )
            async with session_factory() as session:
                yield session
                await trans.rollback()


@pytest.fixture
async def sqlite_sessionmaker():
    from example.database import ASYNC_ENGINE, async_sessionmaker_, recreate_tables_async
    await recreate_tables_async()
    try:
        yield async_sessionmaker_
    finally:
        await ASYNC_ENGINE.dispose()


@pytest.fixture
async def language_context():
    language_manager = LanguageManager(
        locales_dir='example/locales',
        languages={
            'ru': 'Russian',
            'en': 'English',
        },
    )
    lc = LanguageContext('ru', language_manager)
    yield lc
