from unittest import mock

import pytest
from fastapi import Request

from brilliance_admin.api.views.settings import AdminSettingsData
from brilliance_admin.translations import TranslateText
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
        'favicon_image': '/static/favicon.jpg',
        'settings_json': mock.ANY,
        'title': 'Brilliance Admin Demo',
    }


@pytest.mark.asyncio
async def test_settings():
    request = Request(scope=SCOPE)
    settings = await admin_schema.get_settings(request)
    s = AdminSettingsData(
        title=TranslateText(slug='admin_title'),
        description=TranslateText(slug='admin_description'),
        login_greetings_message=TranslateText(slug='login_greetings_message'),
        navbar_density='default',
        languages={'ru': 'Russian', 'en': 'English', 'test': 'Test'},
    )
    assert settings == s, settings
