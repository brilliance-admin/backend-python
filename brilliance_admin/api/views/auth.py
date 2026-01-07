from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from brilliance_admin.auth import AdminAuthentication, AuthData, AuthResult
from brilliance_admin.exceptions import AdminAPIException, APIError
from brilliance_admin.schema.admin_schema import AdminSchema
from brilliance_admin.translations import LanguageContext

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    path='/login/',
    responses={401: {"model": APIError}},
)
async def login(request: Request, auth_data: AuthData) -> AuthResult:
    schema: AdminSchema = request.app.state.schema

    language_slug = request.headers.get('Accept-Language')
    language_context: LanguageContext = schema.get_language_context(language_slug)
    context = {'language_context': language_context}

    auth: AdminAuthentication = schema.auth
    try:
        result: AuthResult = await auth.login(auth_data)
    except AdminAPIException as e:
        return JSONResponse(e.get_error().model_dump(mode='json', context=context), status_code=e.status_code)

    return JSONResponse(content=result.model_dump(mode='json', context=context))
