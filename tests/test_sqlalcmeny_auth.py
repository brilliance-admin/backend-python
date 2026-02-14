import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from brilliance_admin.auth import AuthData
from brilliance_admin.exceptions import AdminAPIException
from brilliance_admin import sqlalchemy
from brilliance_admin.schema.admin_schema import AdminSchemaData
from example.main import app
from example.sections.models import User, UserFactory

client = TestClient(app)


@pytest.mark.asyncio
async def test_login(postgres_sessionmaker):
    auth = sqlalchemy.SQLAlchemyJWTAdminAuthentication(
        secret='123',
        db_async_session=postgres_sessionmaker,
        user_model=User,
    )
    user = await UserFactory(username='123', password='test', is_admin=True)
    result = await auth.login(data=AuthData(username='123', password='test'), debug=True)
    assert result.user.username == user.username


@pytest.mark.asyncio
async def test_login_not_admin(postgres_sessionmaker):
    auth = sqlalchemy.SQLAlchemyJWTAdminAuthentication(
        secret='123',
        db_async_session=postgres_sessionmaker,
        user_model=User,
    )
    await UserFactory(username='123', password='test')
    with pytest.raises(AdminAPIException) as e:
        await auth.login(data=AuthData(username='123', password='test'), debug=True)

    assert e.value.get_error().code == 'not_an_admin'


@pytest.mark.asyncio
async def test_login_not_found(postgres_sessionmaker):
    auth = sqlalchemy.SQLAlchemyJWTAdminAuthentication(
        secret='123',
        db_async_session=postgres_sessionmaker,
        user_model=User,
    )
    with pytest.raises(AdminAPIException) as e:
        await auth.login(data=AuthData(username='123', password='test'), debug=True)

    assert e.value.get_error().code == 'user_not_found'


@pytest.mark.asyncio
async def test_authenticate(postgres_sessionmaker):
    auth = sqlalchemy.SQLAlchemyJWTAdminAuthentication(
        secret='123',
        db_async_session=postgres_sessionmaker,
        user_model=User,
    )
    user = await UserFactory(username='123', password='test', is_admin=True)

    token = auth.get_token(user)
    result_user = await auth.authenticate(headers={'Authorization': f'Token {token}'})
    AdminSchemaData(categories={}, profile=result_user)

    assert result_user.username == user.username


@pytest.mark.asyncio
async def test_authenticate_bad_secret(postgres_sessionmaker):
    auth = sqlalchemy.SQLAlchemyJWTAdminAuthentication(
        secret='123',
        db_async_session=postgres_sessionmaker,
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
async def test_authenticate_not_admin(postgres_sessionmaker):
    auth = sqlalchemy.SQLAlchemyJWTAdminAuthentication(
        secret='123',
        db_async_session=postgres_sessionmaker,
        user_model=User,
    )
    user = await UserFactory(username='123', password='test')
    with pytest.raises(AdminAPIException) as e:
        token = auth.get_token(user)
        await auth.authenticate(headers={'Authorization': f'Token {token}'})

    assert e.value.get_error().code == 'user_not_found'


@pytest.mark.asyncio
async def test_login_valid_password_sync(postgres_sessionmaker, language_context):
    def async_password_validator(user, password):
        return password == 'correct_password'

    auth = sqlalchemy.SQLAlchemyJWTAdminAuthentication(
        secret='123',
        db_async_session=postgres_sessionmaker,
        user_model=User,
        password_validator=async_password_validator,
    )
    await UserFactory(username='admin', password='correct_password', is_admin=True)

    result = await auth.login(data=AuthData(username='admin', password='correct_password'))

    assert result.token is not None
    assert result.user.username == 'admin'


@pytest.mark.asyncio
async def test_login_valid_password_async(postgres_sessionmaker, language_context):
    async def async_password_validator(user, password):
        return password == 'correct_password'

    auth = sqlalchemy.SQLAlchemyJWTAdminAuthentication(
        secret='123',
        db_async_session=postgres_sessionmaker,
        user_model=User,
        password_validator=async_password_validator,
    )
    await UserFactory(username='admin', password='correct_password', is_admin=True)

    result = await auth.login(data=AuthData(username='admin', password='correct_password'))

    assert result.token is not None
    assert result.user.username == 'admin'


@pytest.mark.asyncio
async def test_login_invalid_password_async(postgres_sessionmaker, language_context):
    async def async_password_validator(user, password):
        return password == 'correct_password'

    auth = sqlalchemy.SQLAlchemyJWTAdminAuthentication(
        secret='123',
        db_async_session=postgres_sessionmaker,
        user_model=User,
        password_validator=async_password_validator,
    )
    await UserFactory(username='admin', password='correct_password', is_admin=True)

    with pytest.raises(AdminAPIException) as e:
        await auth.login(data=AuthData(username='admin', password='wrong_password'), debug=False)

    context = {'language_context': language_context}
    assert e.value.get_error().model_dump(context=context) == {
        'code': 'user_not_found',
        'field_errors': None,
        'message': None,
    }


@pytest.mark.asyncio
async def test_login_invalid_password(postgres_sessionmaker, language_context):
    auth = sqlalchemy.SQLAlchemyJWTAdminAuthentication(
        secret='123',
        db_async_session=postgres_sessionmaker,
        user_model=User,
        password_validator=lambda user, password: password == 'correct_password',
    )
    await UserFactory(username='admin', password='correct_password', is_admin=True)

    with pytest.raises(AdminAPIException) as e:
        await auth.login(data=AuthData(username='admin', password='wrong_password'), debug=True)

    context = {'language_context': language_context}
    assert e.value.get_error().model_dump(context=context) == {
        'code': 'user_not_found',
        'field_errors': None,
        'message': None,
    }


def test_username_validation_invalid():
    with pytest.raises(ValidationError):
        AuthData(username='../../../../../../Windows/win.iniadmin', password='test')
    with pytest.raises(ValidationError):
        AuthData(username='../etc/passwd', password='test')
    with pytest.raises(ValidationError):
        AuthData(username='admin; DROP TABLE users', password='test')
    with pytest.raises(ValidationError):
        AuthData(username='admin<script>', password='test')
    with pytest.raises(ValidationError):
        AuthData(username='user name', password='test')
    with pytest.raises(ValidationError):
        AuthData(username='', password='test')
    with pytest.raises(ValidationError):
        AuthData(username='a' * 151, password='test')


def test_username_validation_valid():
    assert AuthData(username='admin', password='test').username == 'admin'
    assert AuthData(username='user_name', password='test').username == 'user_name'
    assert AuthData(username='user.name', password='test').username == 'user.name'
    assert AuthData(username='user-name', password='test').username == 'user-name'
    assert AuthData(username='user@domain.com', password='test').username == 'user@domain.com'
    assert AuthData(username='User123', password='test').username == 'User123'


def test_login_api_invalid_username():
    response = client.post('/admin/auth/login/', json={
        'username': '../../../../../../Windows/win.iniadmin',
        'password': 'test',
    })
    assert response.status_code == 400
    assert response.json() == {
        'code': 'validation_error',
        'field_errors': {
            'username': {
                'code': None,
                'field_slug': 'username',
                'message': "String should match pattern '^[a-zA-Z0-9@._-]{1,150}$'",
            },
        },
        'message': None,
    }


def test_login_api_valid_username():
    response = client.post('/admin/auth/login/', json={
        'username': 'admin',
        'password': 'admin',
    })
    assert response.status_code == 200
    assert response.json()['user']['username'] == 'test_admin'
