from fastapi import APIRouter

from .views.schema import router as schema_router
from .views.table import router as schema_table
from .views.auth import router as schema_auth
from .views.autocomplete import router as schema_autocomplete
from .views.graphs import router as schema_graphs
from .views.settings import router as schema_settings
from .views.index import router as schema_index

brilliance_admin_router = APIRouter()
brilliance_admin_router.include_router(schema_router)
brilliance_admin_router.include_router(schema_table)
brilliance_admin_router.include_router(schema_auth)
brilliance_admin_router.include_router(schema_autocomplete)
brilliance_admin_router.include_router(schema_graphs)
brilliance_admin_router.include_router(schema_settings)
brilliance_admin_router.include_router(schema_index)
