from unittest.mock import AsyncMock

import pytest
from asyncpg.exceptions import ForeignKeyViolationError
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from example.main import admin_schema, app
from example.sections.models import Currency, CurrencyFactory

client = TestClient(app)


@pytest.mark.parametrize('operation', ['create', 'update'])
@pytest.mark.parametrize('field', ['num_code', 'char_code'])
@pytest.mark.parametrize('language,message', [
    ('ru', 'Значение уникального поля или сочетание значений уже используется.'),
    ('en', 'A unique field value or combination of values is already in use.'),
])
async def test_duplicate_returns_friendly_error_and_rolls_back(
    postgres_sessionmaker, operation, field, language, message,
):
    original = await CurrencyFactory(title='Original', num_code=123, char_code='ORIGINAL')
    target = await CurrencyFactory(title='Target', num_code=456, char_code='TARGET')
    data = {'title': 'Changed', 'num_code': 789, 'char_code': 'CHANGED', 'depth': 2}
    data[field] = getattr(original, field)
    route_params = {'group': 'currencies', 'category': 'currency'}
    if operation == 'update':
        route_params['pk'] = target.id
    url = app.url_path_for(f'table_{operation}', **route_params)
    method = 'POST' if operation == 'create' else 'PATCH'

    response = client.request(method, url, json=data, headers={'Accept-Language': language})
    assert response.status_code == 400, response.text
    assert response.json() == {
        'message': message,
        'code': 'unique_violation',
        'field_errors': None,
    }

    async with postgres_sessionmaker() as session:
        records = (await session.execute(select(Currency).order_by(Currency.id))).scalars().all()
        assert [(record.title, record.num_code, record.char_code) for record in records] == [
            ('Original', 123, 'ORIGINAL'),
            ('Target', 456, 'TARGET'),
        ]

    data[field] = 789 if field == 'num_code' else 'CHANGED'
    response = client.request(method, url, json=data, headers={'Accept-Language': language})
    assert response.status_code == 200, response.text


@pytest.mark.parametrize('operation', ['create', 'update'])
@pytest.mark.parametrize('cause_type', [ForeignKeyViolationError, None])
async def test_other_integrity_errors_keep_existing_response(mocker, operation, cause_type):
    target = await CurrencyFactory(title='Target', num_code=456, char_code='TARGET')
    category = next(
        category
        for category in admin_schema.iter_categories()
        if getattr(category, 'model', None) is Currency
    )
    original = Exception('Database constraint failure')
    if cause_type is not None:
        original.__cause__ = cause_type('Database constraint failure')
    error = IntegrityError('statement', {}, original)
    mocker.patch.object(category.table_schema, operation, new=AsyncMock(side_effect=error))
    route_params = {'group': 'currencies', 'category': 'currency'}
    if operation == 'update':
        route_params['pk'] = target.id
    url = app.url_path_for(f'table_{operation}', **route_params)

    response = client.request(
        'POST' if operation == 'create' else 'PATCH',
        url,
        json={'title': 'Changed', 'num_code': 789, 'char_code': 'CHANGED', 'depth': 2},
        headers={'Accept-Language': 'en'},
    )

    assert response.status_code == 500, response.text
    assert response.json() == {
        'message': 'Database integrity error: Database constraint failure',
        'code': 'db_integrity_error',
        'field_errors': None,
    }
