import pytest

from brilliance_admin.auth import AuthData
from brilliance_admin.exceptions import AdminAPIException
from brilliance_admin import sqlalchemy
from brilliance_admin.schema.admin_schema import AdminSchemaData
from example.sections.models import User, UserFactory


@pytest.mark.asyncio
async def test_login(sqlite_sessionmaker):
    auth = sqlalchemy.SQLAlchemyJWTAdminAuthentication(
        secret='123',
        db_async_session=sqlite_sessionmaker,
        user_model=User,
    )
    user = await UserFactory(username='123', password='test', is_admin=True)
    result = await auth.login(data=AuthData(username='123', password='test'))
    assert result.user.username == user.username


@pytest.mark.asyncio
async def test_login_not_admin(sqlite_sessionmaker):
    auth = sqlalchemy.SQLAlchemyJWTAdminAuthentication(
        secret='123',
        db_async_session=sqlite_sessionmaker,
        user_model=User,
    )
    await UserFactory(username='123', password='test')
    with pytest.raises(AdminAPIException) as e:
        await auth.login(data=AuthData(username='123', password='test'))

    assert e.value.get_error().code == 'not_an_admin'


@pytest.mark.asyncio
async def test_login_not_found(sqlite_sessionmaker):
    auth = sqlalchemy.SQLAlchemyJWTAdminAuthentication(
        secret='123',
        db_async_session=sqlite_sessionmaker,
        user_model=User,
    )
    with pytest.raises(AdminAPIException) as e:
        await auth.login(data=AuthData(username='123', password='test'))

    assert e.value.get_error().code == 'user_not_found'


@pytest.mark.asyncio
async def test_authenticate(sqlite_sessionmaker):
    auth = sqlalchemy.SQLAlchemyJWTAdminAuthentication(
        secret='123',
        db_async_session=sqlite_sessionmaker,
        user_model=User,
    )
    user = await UserFactory(username='123', password='test', is_admin=True)

    token = auth.get_token(user)
    result_user = await auth.authenticate(headers={'Authorization': f'Token {token}'})
    AdminSchemaData(categories={}, profile=result_user)

    assert result_user.username == user.username


@pytest.mark.asyncio
async def test_authenticate_bad_secret(sqlite_sessionmaker):
    auth = sqlalchemy.SQLAlchemyJWTAdminAuthentication(
        secret='123',
        db_async_session=sqlite_sessionmaker,
        user_model=User,
    )
    user = await UserFactory(username='123', password='test', is_admin=True)

    token = auth.get_token(user)
    result_user = await auth.authenticate(headers={'Authorization': f'Token {token}'})
    AdminSchemaData(categories={}, profile=result_user)
    assert result_user.username == user.username

    auth.secret = 'another'
    with pytest.raises(AdminAPIException) as e:
        await auth.authenticate(headers={'Authorization': f'Token {token}'})

    assert e.value.get_error().code == 'token_error'


@pytest.mark.asyncio
async def test_authenticate_not_admin(sqlite_sessionmaker):
    auth = sqlalchemy.SQLAlchemyJWTAdminAuthentication(
        secret='123',
        db_async_session=sqlite_sessionmaker,
        user_model=User,
    )
    user = await UserFactory(username='123', password='test')
    with pytest.raises(AdminAPIException) as e:
        token = auth.get_token(user)
        await auth.authenticate(headers={'Authorization': f'Token {token}'})

    assert e.value.get_error().code == 'user_not_found'
