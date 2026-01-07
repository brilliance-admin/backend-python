import pytest

from brilliance_admin.translations import LanguageContext, LanguageManager
from example.sqlite import ASYNC_ENGINE, async_sessionmaker_, recreate_tables_async


@pytest.fixture
async def sqlite_sessionmaker():
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
