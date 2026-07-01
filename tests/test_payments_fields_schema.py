from unittest import mock

import pytest

from brilliance_admin.auth import UserABC
from example.sections.payments import PaymentsAdmin

category_schema_data = {
    'dashboard_info': None,
    'icon': 'mdi-credit-card-outline',
    'description': 'Статичные данные',
    'link': None,
    'categories': {},
    'table_info': mock.ANY,
    'title': 'Платежи',
    'type': 'table',
 }


@pytest.mark.asyncio
async def test_generate_category_schema(language_context):
    category = PaymentsAdmin()
    new_schema = category.generate_category_schema(UserABC(username="test"), language_context)
    assert new_schema.model_dump() == category_schema_data, new_schema.model_dump()
