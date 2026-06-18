import pytest

from brilliance_admin.exceptions import FieldError, ValidationError
from brilliance_admin.schema.table.fields import InlineField, StringField
from brilliance_admin.schema.table.fields_schema import FieldsSchema
from brilliance_admin.utils import DeserializeAction


class InlineRowSchema(FieldsSchema):
    fields = ["name"]

    name = StringField()

    async def validate_name(self, value):
        if value != "test":
            raise FieldError("Only 'test' is allowed", "only_test")
        return "validated_test"


class InlineFormSchema(FieldsSchema):
    fields = ["inline"]

    inline = InlineField(
        many=True,
        table_schema=InlineRowSchema(),
    )


@pytest.mark.asyncio
async def test_inline_deserialize_fields_success():
    result = await InlineFormSchema().deserialize_fields(
        {
            "inline": [
                {"name": "test"},
            ],
        },
        DeserializeAction.CREATE,
        extra={},
    )

    assert result == {
        "inline": [
            {"name": "validated_test"},
        ],
    }


@pytest.mark.asyncio
async def test_inline_deserialize_fields_nested_error():
    with pytest.raises(ValidationError) as exc_info:
        await InlineFormSchema().deserialize_fields(
            {
                "inline": [
                    {"name": "wrong"},
                ],
            },
            DeserializeAction.CREATE,
            extra={},
        )

    assert exc_info.value.data == {
        "inline": FieldError(
            message=[
                {
                    "name": FieldError(
                        message="Only 'test' is allowed",
                        code="only_test",
                    ),
                },
            ],
            code="inline_nested",
        ),
    }
