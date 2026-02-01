import importlib

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
    # admin_schema.backend_prefix = 'test'
    result = await admin_schema.get_index_context_data(request)
    version = importlib.metadata.version('brilliance-admin')
    assert result == {
        'favicon_image': '/static/favicon.jpg',
        'settings_json': '{"backend_prefix": "http://testserver/admin/", "static_prefix": '
        f'"http://testserver/admin/static/", "version": "{version}", "api_timeout_ms": '
        '5000, "logo_image": "http://testserver/static/logo-outline.png"}',
        'title': 'Brilliance Admin Demo',
    }


@pytest.mark.asyncio
async def test_settings():
    request = Request(scope=SCOPE)
    settings = await admin_schema.get_settings(request)
    s = AdminSettingsData(
        main_page='/dashboard/dashboard/',
        title=TranslateText(slug='admin_title'),
        description=TranslateText(slug='admin_description'),
        login_greetings_message=TranslateText(slug='login_greetings_message'),
        navbar_density='default',
        languages={'ru': 'Russian', 'en': 'English', 'test': 'Test'},
    )
    assert settings == s, settings
