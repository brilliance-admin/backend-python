from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from brilliance_admin.api.utils import get_category, get_user
from brilliance_admin.exceptions import AdminAPIException
from brilliance_admin.schema.admin_schema import AdminSchema
from brilliance_admin.schema.dashboard.category_dashboard import CategoryDashboard, DashboardContainer, DashboardData
from brilliance_admin.schema.table.table_action import TableAction
from brilliance_admin.translations import LanguageContext
from brilliance_admin.utils import get_logger

router = APIRouter(prefix="/dashboard", tags=["Category - Dashboard"])

logger = get_logger()


@router.post(path='/{group}/{category}/')
async def dashboard_data(
        request: Request,
        group: str,
        category: str,
        data: DashboardData,
        subcategory: str | None = None,
        parent_pk: Any | None = None,
) -> DashboardContainer:
    schema: AdminSchema = request.app.state.schema
    user = await get_user(request)
    schema_category, parent_category = get_category(
        schema,
        group,
        category,
        subcategory,
        check_type=CategoryDashboard,
    )

    # Permissions
    permissions = await schema.permissions_manager.get_user_permissions(user, for_schema_generation=False)
    if not permissions.has_action_permission(schema_category, TableAction.LIST):
        raise HTTPException(status_code=403, detail='Permission denied')

    result: DashboardContainer = await schema_category.get_data(
        data,
        user,
        parent_category,
        parent_pk,
    )

    language_slug = request.headers.get('Accept-Language')
    language_context: LanguageContext = schema.get_language_context(language_slug)
    context = {'language_context': language_context}

    try:
        return JSONResponse(result.model_dump(mode='json', context=context))
    except AdminAPIException as e:
        return JSONResponse(e.get_error().model_dump(mode='json', context=context), status_code=e.status_code)
