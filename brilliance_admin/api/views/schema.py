from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from brilliance_admin.auth import AdminAuthentication
from brilliance_admin.exceptions import AdminAPIException, APIError
from brilliance_admin.schema import AdminSchema, AdminSchemaData

router = APIRouter(prefix="/schema", tags=["Main admin schema"])


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
    admin_schema = schema.generate_schema(user, language_slug)
    return admin_schema
