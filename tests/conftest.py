# pylint: disable=protected-access
import pytest_asyncio
from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

from brilliance_admin.translations import LanguageContext, LanguageManager
from example.sections.models import ModelBase
from example.utils import SQLAlchemyFactoryBase


@pytest_asyncio.fixture(scope="session")
async def postgres_container():
    with PostgresContainer(
        image="postgres:alpine",
        username="test_user",
        password="test_password",
        dbname="test_db",
    ) as postgres:
        yield postgres


@pytest_asyncio.fixture(scope="session")
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


@pytest_asyncio.fixture(scope="function")
async def postgres_sessionmaker(async_engine):
    session_factory = async_sessionmaker(
        bind=async_engine,
        expire_on_commit=False,
        autoflush=False,
        class_=AsyncSession,
    )
    yield session_factory


@pytest_asyncio.fixture(autouse=True)
async def set_factory_session(postgres_sessionmaker):
    factories = SQLAlchemyFactoryBase.__subclasses__()
    original = {f: f._meta.sqlalchemy_session_factory for f in factories}
    for f in factories:
        f._meta.sqlalchemy_session_factory = postgres_sessionmaker
    yield
    for f, orig in original.items():
        f._meta.sqlalchemy_session_factory = orig


@pytest_asyncio.fixture(autouse=True)
async def cleanup_tables(async_engine):
    yield
    async with async_engine.begin() as conn:
        tables = ", ".join(
            f'"{t.name}"' for t in reversed(ModelBase.metadata.sorted_tables)
        )
        await conn.exec_driver_sql(f"TRUNCATE {tables} RESTART IDENTITY CASCADE")


@pytest_asyncio.fixture(autouse=True)
async def patch_admin_sessions(postgres_sessionmaker):
    from example.main import admin_schema

    original = {}
    for group in admin_schema.categories:
        if not hasattr(group, 'subcategories'):
            continue
        for cat in group.subcategories:
            if hasattr(cat, 'db_async_session'):
                original[id(cat)] = cat.db_async_session
                cat.db_async_session = postgres_sessionmaker

    yield

    for group in admin_schema.categories:
        if not hasattr(group, 'subcategories'):
            continue
        for cat in group.subcategories:
            if id(cat) in original:
                cat.db_async_session = original[id(cat)]


@pytest_asyncio.fixture
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
