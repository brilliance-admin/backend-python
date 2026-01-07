from fastapi import APIRouter, FastAPI, Request
from fastapi.openapi.docs import get_redoc_html
from fastapi.responses import HTMLResponse


def build_scalar_docs(app: FastAPI) -> APIRouter:
    # pylint: disable=import-outside-toplevel
    from scalar_fastapi import get_scalar_api_reference

    router = APIRouter()

    @router.get("/scalar", include_in_schema=False)
    async def scalar_docs(request: Request):
        root_path = request.scope.get("root_path", "")
        openapi_url = f"{root_path}{app.openapi_url}"
        return get_scalar_api_reference(
            openapi_url=openapi_url,
        )

    return router


# https://cdn.jsdelivr.net/npm/redoc/bundles/redoc.standalone.js
def build_redoc_docs(app, redoc_url):
    router = APIRouter()

    @router.get(redoc_url, include_in_schema=False)
    async def redoc(request: Request) -> HTMLResponse:
        root_path = request.scope.get("root_path", "")
        openapi_url = f"{root_path}{app.openapi_url}"
        return get_redoc_html(
            openapi_url=openapi_url,
            title=f"{request.app.state.schema.title} - ReDoc",
            redoc_js_url="https://cdn.jsdelivr.net/npm/redoc/bundles/redoc.standalone.js",
        )

    return router
