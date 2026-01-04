from unittest import mock

import pytest
from fastapi import Request

from example.main import admin_schema, app

SCOPE = {
    'type': 'http',
    'method': 'GET',
    'path': '/',
    'raw_path': b'/',
    'headers': [],
    'query_string': b'',
    'scheme': 'http',
    'server': ('testserver', 80),
    'client': ('testclient', 50000),
    'root_path': '',
    'app': app,
    'asgi': {'version': '3.0'},
}


@pytest.mark.asyncio
async def test_index_context_data():
    request = Request(scope=SCOPE)
    result = await admin_schema.get_index_context_data(request)
    assert result == {
        'favicon_image': '/admin/static/favicon.ico',
        'settings_json': mock.ANY,
        'title': 'Brilliance Admin Демо',
    }
