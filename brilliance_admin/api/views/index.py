from pathlib import PurePosixPath

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from jinja2 import Environment, PackageLoader, select_autoescape

from brilliance_admin.schema import AdminSchema

router = APIRouter()

templates = Jinja2Templates(
    env=Environment(
        loader=PackageLoader("brilliance_admin", "templates"),
        autoescape=select_autoescape(["html", "xml"]),
    )
)

# Всё, что не должно попадать в SPA (можете расширять список)
EXACT_BLOCK = {"/openapi.json"}
PREFIX_BLOCK = ("/docs", "/redoc", "/scalar", "/static")


@router.get('/{rest_of_path:path}', response_class=HTMLResponse, include_in_schema=False)
async def admin_index(request: Request, rest_of_path: str):
    '''
    The request responds with a pre-rendered SPA served as an HTML page.
    '''

    path = PurePosixPath('/' + rest_of_path)

    if '..' in path.parts:
        raise HTTPException(status_code=404)

    path_str = str(path)
    if path_str in EXACT_BLOCK or path_str.startswith(PREFIX_BLOCK):
        raise HTTPException(status_code=404)

    schema: AdminSchema = request.app.state.schema

    return templates.TemplateResponse(
        request=request,
        name='index.html',
        context=await schema.get_index_context_data(request),
    )
