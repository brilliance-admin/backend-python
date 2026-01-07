from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from brilliance_admin.exceptions import AdminAPIException, APIError
from brilliance_admin.schema.admin_schema import AdminSchema, AdminSettingsData
from brilliance_admin.translations import LanguageContext

router = APIRouter(tags=["Settings"])


@router.post(
    path='/get-settings/',
    responses={400: {"model": APIError}},
)
async def get_settings(request: Request) -> AdminSettingsData:
    '''
    API endpoint for fetching admin panel configuration, including title, description, and the list of supported languages.
    '''
    schema: AdminSchema = request.app.state.schema

    language_slug = request.headers.get('Accept-Language')
    language_context: LanguageContext = schema.get_language_context(language_slug)
    context = {'language_context': language_context}

    try:
        admin_settings = await schema.get_settings(request)
        return JSONResponse(admin_settings.model_dump(mode='json', context=context))
    except AdminAPIException as e:
        return JSONResponse(e.get_error().model_dump(mode='json', context=context), status_code=e.status_code)
