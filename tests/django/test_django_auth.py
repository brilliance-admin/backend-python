import pytest

from brilliance_admin.auth import AuthData
from brilliance_admin.exceptions import AdminAPIException
from brilliance_admin.integrations.django import DjangoJWTAdminAuthentication
from example.sections.django_models import DjangoUser, DjangoUserFactory


@pytest.mark.asyncio
async def test_login():
    auth = DjangoJWTAdminAuthentication(
        secret='123',
        user_model=DjangoUser,
    )
    user = await DjangoUserFactory(username='admin', password='test', is_admin=True)
    result = await auth.login(data=AuthData(username='admin', password='test'), debug=True)
    assert result.user.username == user.username


@pytest.mark.asyncio
async def test_login_not_admin():
    auth = DjangoJWTAdminAuthentication(
        secret='123',
        user_model=DjangoUser,
    )
    await DjangoUserFactory(username='admin', password='test', is_admin=False)
    with pytest.raises(AdminAPIException) as e:
        await auth.login(data=AuthData(username='admin', password='test'), debug=True)

    assert e.value.get_error().code == 'not_an_admin'


@pytest.mark.asyncio
async def test_login_not_found():
    auth = DjangoJWTAdminAuthentication(
        secret='123',
        user_model=DjangoUser,
    )
    with pytest.raises(AdminAPIException) as e:
        await auth.login(data=AuthData(username='admin', password='test'), debug=True)

    assert e.value.get_error().code == 'user_not_found'


@pytest.mark.asyncio
async def test_authenticate():
    auth = DjangoJWTAdminAuthentication(
        secret='123',
        user_model=DjangoUser,
    )
    user = await DjangoUserFactory(username='admin', password='test', is_admin=True)

    token = auth.get_token(user)
    result_user = await auth.authenticate(headers={'Authorization': f'Token {token}'})

    assert result_user.username == user.username


@pytest.mark.asyncio
async def test_authenticate_bad_secret():
    auth = DjangoJWTAdminAuthentication(
        secret='123',
        user_model=DjangoUser,
    )
    user = await DjangoUserFactory(username='admin', password='test', is_admin=True)

    token = auth.get_token(user)
    auth.secret = 'another'

    with pytest.raises(AdminAPIException) as e:
        await auth.authenticate(headers={'Authorization': f'Token {token}'})

    assert e.value.get_error().code == 'token_error'


@pytest.mark.asyncio
async def test_login_valid_password_sync():
    auth = DjangoJWTAdminAuthentication(
        secret='123',
        user_model=DjangoUser,
        password_validator=lambda user, password: password == 'correct_password',
    )
    await DjangoUserFactory(username='admin', password='correct_password', is_admin=True)

    result = await auth.login(data=AuthData(username='admin', password='correct_password'))

    assert result.token is not None
    assert result.user.username == 'admin'


@pytest.mark.asyncio
async def test_login_valid_password_async():
    async def async_password_validator(user, password):
        return password == 'correct_password'

    auth = DjangoJWTAdminAuthentication(
        secret='123',
        user_model=DjangoUser,
        password_validator=async_password_validator,
    )
    await DjangoUserFactory(username='admin', password='correct_password', is_admin=True)

    result = await auth.login(data=AuthData(username='admin', password='correct_password'))

    assert result.token is not None
    assert result.user.username == 'admin'
