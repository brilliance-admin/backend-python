from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from brilliance_admin.api.utils import get_category
from brilliance_admin.exceptions import AdminAPIException
from brilliance_admin.schema.admin_schema import AdminSchema
from brilliance_admin.schema.graphs.category_graphs import CategoryGraphs, GraphData, GraphsDataResult
from brilliance_admin.translations import LanguageContext
from brilliance_admin.utils import get_logger

router = APIRouter(prefix="/graph", tags=["Category - Graph"])

logger = get_logger()


@router.post(path='/{group}/{category}/')
async def graph_data(request: Request, group: str, category: str, data: GraphData) -> GraphsDataResult:
    schema: AdminSchema = request.app.state.schema
    schema_category, user = await get_category(request, group, category, check_type=CategoryGraphs)

    result: GraphsDataResult = await schema_category.get_data(data, user)

    language_slug = request.headers.get('Accept-Language')
    language_context: LanguageContext = schema.get_language_context(language_slug)
    context = {'language_context': language_context}

    try:
        return JSONResponse(result.model_dump(mode='json', context=context))
    except AdminAPIException as e:
        return JSONResponse(e.get_error().model_dump(mode='json', context=context), status_code=e.status_code)
