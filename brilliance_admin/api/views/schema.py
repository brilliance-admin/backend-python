from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from brilliance_admin.auth import AdminAuthentication
from brilliance_admin.exceptions import AdminAPIException, APIError
from brilliance_admin.schema import AdminSchema, AdminSchemaData
from brilliance_admin.translations import LanguageContext
from brilliance_admin.utils import get_logger

router = APIRouter(prefix="/schema", tags=["Main admin schema"])

logger = get_logger()


@router.get(
    path='/',
    responses={400: {"model": APIError}},
)
async def schema_handler(request: Request) -> AdminSchemaData:
    '''
    Request for retrieving the admin panel schema, including all sections and their contents.
    '''
    schema: AdminSchema = request.app.state.schema

    auth: AdminAuthentication = schema.auth
    try:
        user = await auth.authenticate(request.headers)
    except AdminAPIException as e:
        return JSONResponse(e.get_error().model_dump(mode='json'), status_code=e.status_code)

    language_slug = request.headers.get('Accept-Language')
    language_context: LanguageContext = schema.get_language_context(language_slug)
    context = {'language_context': language_context}

    admin_schema = schema.generate_admin_schema(user, language_slug)

    try:
        return JSONResponse(content=admin_schema.model_dump(mode='json', context=context))
    except Exception as e:
        logger.exception('Admin schema model dump error: %s', e)
        raise HTTPException(status_code=500, detail="Content error") from e
