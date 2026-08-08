from fastapi import FastAPI
from fastapi.testclient import TestClient

from brilliance_admin.schema.admin_schema import (
    DEFAULT_DEBUG_TRACEBACK_LIMIT,
    AdminSchema,
    add_limited_debug_traceback_middleware,
)


def _raise_0():
    return _raise_1()


def _raise_1():
    return _raise_2()


def _raise_2():
    return _raise_3()


def _raise_3():
    return _raise_4()


def _raise_4():
    return _raise_5()


def _raise_5():
    return _raise_6()


def _raise_6():
    return _raise_7()


def _raise_7():
    return _raise_8()


def _raise_8():
    return _raise_9()


def _raise_9():
    return _raise_10()


def _raise_10():
    return _raise_11()


def _raise_11():
    raise ValueError('limited traceback check')


def test_debug_traceback_middleware_limits_plain_text_traceback():
    app = FastAPI(debug=True)
    traceback_limit = 5
    add_limited_debug_traceback_middleware(app, traceback_limit)

    @app.get('/boom')
    async def boom():
        _raise_0()

    client = TestClient(app, raise_server_exceptions=False)

    response = client.get('/boom', headers={'accept': 'text/plain'})

    assert response.status_code == 500
    assert response.headers['content-type'].startswith('text/plain')
    assert 'ValueError: limited traceback check' in response.text
    assert response.text.count('\n  File ') <= traceback_limit


def test_debug_traceback_limit_defaults_to_seven():
    admin_schema = AdminSchema(categories=[], auth=None)

    assert admin_schema.debug_traceback_limit == DEFAULT_DEBUG_TRACEBACK_LIMIT
    assert admin_schema.debug_traceback_limit == 7
