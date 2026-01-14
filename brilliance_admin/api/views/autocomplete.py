from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from brilliance_admin.api.utils import get_category
from brilliance_admin.exceptions import AdminAPIException
from brilliance_admin.schema.admin_schema import AdminSchema
from brilliance_admin.schema.table.table_models import AutocompleteData, AutocompleteResult
from brilliance_admin.translations import LanguageContext
from brilliance_admin.utils import get_logger

router = APIRouter(prefix="/autocomplete", tags=["Autocomplete"])

logger = get_logger()


@router.post(path='/{group}/{category}/')
async def autocomplete(request: Request, group: str, category: str, data: AutocompleteData):
    schema: AdminSchema = request.app.state.schema
    schema_category, user = await get_category(request, group, category)

    language_slug = request.headers.get('Accept-Language')
    language_context: LanguageContext = schema.get_language_context(language_slug)
    context = {'language_context': language_context}

    try:
        result: AutocompleteResult = await schema_category.autocomplete(data, user, language_context, schema)
    except AdminAPIException as e:
        return JSONResponse(e.get_error().model_dump(mode='json', context=context), status_code=e.status_code)
    except Exception as e:
        logger.exception('Autocomplete %s.%s exceptoin: %s', e, group, category, extra={'data': data})
        return JSONResponse({}, status_code=500)

    return JSONResponse(result.model_dump(mode='json', context=context))
