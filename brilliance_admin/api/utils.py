from fastapi import HTTPException

from brilliance_admin.auth import AdminAuthentication


async def get_user(request):
    auth: AdminAuthentication = request.app.state.schema.auth
    user = await auth.authenticate(request.headers)
    return user


async def get_category(request, group: str, category: str, subcategory: str | None, check_type=None):
    user = await get_user(request)

    schema_group = request.app.state.schema.get_group(group)
    if not schema_group:
        raise HTTPException(status_code=404, detail="Group not found")

    schema_category = schema_group.get_category(category)
    if not schema_category:
        raise HTTPException(status_code=404, detail="Category not found")

    if check_type and not issubclass(schema_category.__class__, check_type):
        detail = f"Category {group}.{category} is not a {check_type.__name__}"
        raise HTTPException(status_code=404, detail=detail)

    if subcategory:
        schema_subcategory = schema_category.get_subcategory(subcategory)
        if not schema_subcategory:
            detail = f'Category {group}.{category} subcategory "{subcategory}" not found'
            raise HTTPException(status_code=404, detail=detail)

        if check_type and not issubclass(schema_category.__class__, check_type):
            detail = (
                f'Category {group}.{category} subcategory "{subcategory}" '
                f'is not a {check_type.__name__}'
            )
            raise HTTPException(status_code=404, detail=detail)
        return schema_subcategory, user, schema_category

    return schema_category, user, None
