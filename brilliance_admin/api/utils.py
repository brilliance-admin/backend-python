from fastapi import HTTPException

from brilliance_admin.auth import AdminAuthentication
from brilliance_admin.exceptions import AdminAPIException


def validate_subcategory_parent(subcategory: str | None = None, parent_pk: str | None = None):
    if (subcategory is None) != (parent_pk is None) or subcategory == '' or parent_pk == '':
        raise HTTPException(
            status_code=400,
            detail='subcategory and parent_pk must be provided together and must not be empty',
        )


async def get_user(request):
    auth: AdminAuthentication = request.app.state.schema.auth
    try:
        return await auth.authenticate(request.headers)
    except AdminAPIException as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.get_error().model_dump(mode='json'),
        ) from exc


def get_category(admin_schema, group: str, category: str, subcategory: str | None, check_type=None):
    schema_group = admin_schema.get_group(group)
    if not schema_group:
        raise HTTPException(status_code=404, detail="Group not found")

    schema_category = schema_group.get_category(category)
    if not schema_category:
        raise HTTPException(status_code=404, detail="Category not found")

    if subcategory:
        schema_subcategory = schema_category.get_subcategory(subcategory)
        if not schema_subcategory:
            detail = f'Category {group}.{category} subcategory "{subcategory}" not found'
            raise HTTPException(status_code=404, detail=detail)

        if check_type and not issubclass(schema_subcategory.__class__, check_type):
            detail = (
                f'Category {group}.{category} subcategory "{subcategory}" '
                f'is not a {check_type.__name__}'
            )
            raise HTTPException(status_code=404, detail=detail)
        return schema_subcategory, schema_category

    if check_type and not issubclass(schema_category.__class__, check_type):
        detail = f"Category {group}.{category} is not a {check_type.__name__}"
        raise HTTPException(status_code=404, detail=detail)

    return schema_category, None
