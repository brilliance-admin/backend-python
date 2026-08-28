import pytest

from brilliance_admin import schema
from brilliance_admin.exceptions import FieldError
from brilliance_admin.utils import DeserializeAction


@pytest.mark.asyncio
async def test_optional_integer_rejects_none_when_minimum_configured():
    field = schema.IntegerField(required=False, min_value=1)

    with pytest.raises(FieldError):
        await field.deserialize_field(None, DeserializeAction.CREATE, extra={})


@pytest.mark.asyncio
async def test_required_integer_rejects_none():
    field = schema.IntegerField(required=True)

    with pytest.raises(FieldError, match='Field is required'):
        await field.deserialize_field(None, DeserializeAction.CREATE, extra={})


@pytest.mark.asyncio
async def test_integer_rejects_value_below_minimum():
    field = schema.IntegerField(required=False, min_value=1)

    with pytest.raises(FieldError):
        await field.deserialize_field(0, DeserializeAction.CREATE, extra={})


@pytest.mark.asyncio
async def test_optional_decimal_rejects_none_when_minimum_configured():
    field = schema.DecimalField(required=False, min_value=1)

    with pytest.raises(FieldError):
        await field.deserialize_field(None, DeserializeAction.CREATE, extra={})


@pytest.mark.asyncio
async def test_required_decimal_rejects_none():
    field = schema.DecimalField(required=True)

    with pytest.raises(FieldError, match='Field is required'):
        await field.deserialize_field(None, DeserializeAction.CREATE, extra={})


@pytest.mark.asyncio
async def test_decimal_rejects_value_below_minimum():
    field = schema.DecimalField(required=False, min_value=1)

    with pytest.raises(FieldError):
        await field.deserialize_field('0.5', DeserializeAction.CREATE, extra={})
