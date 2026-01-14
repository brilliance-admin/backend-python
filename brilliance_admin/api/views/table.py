from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from brilliance_admin.api.utils import get_category
from brilliance_admin.exceptions import AdminAPIException, APIError
from brilliance_admin.schema import AdminSchema
from brilliance_admin.schema.table.admin_action import ActionData, ActionResult
from brilliance_admin.schema.table.category_table import CategoryTable
from brilliance_admin.schema.table.table_models import (
    CreateResult, ListData, RetrieveResult, TableListResult, UpdateResult)
from brilliance_admin.translations import LanguageContext
from brilliance_admin.utils import get_logger

router = APIRouter(prefix="/table", tags=["Category - Table"])

logger = get_logger()


# pylint: disable=too-many-arguments
@router.post(path='/{group}/{category}/list/')
async def table_list(request: Request, group: str, category: str, list_data: ListData) -> TableListResult:
    schema: AdminSchema = request.app.state.schema

    schema_category, user = await get_category(request, group, category, check_type=CategoryTable)

    language_slug = request.headers.get('Accept-Language')
    language_context: LanguageContext = schema.get_language_context(language_slug)
    context = {'language_context': language_context}

    try:
        result: TableListResult = await schema_category.get_list(list_data, user, language_context, schema)
    except AdminAPIException as e:
        return JSONResponse(e.get_error().model_dump(mode='json', context=context), status_code=e.status_code)

    try:
        return JSONResponse(content=result.model_dump(mode='json', context=context))
    except Exception as e:
        logger.exception('Admin list error: %s; result: %s', e, result)
        raise HTTPException(status_code=500, detail=f"Content error: {e}") from e


@router.post(path='/{group}/{category}/retrieve/{pk}/')
async def table_retrieve(request: Request, group: str, category: str, pk: Any) -> RetrieveResult:
    schema: AdminSchema = request.app.state.schema

    schema_category, user = await get_category(request, group, category, check_type=CategoryTable)
    if not schema_category.has_retrieve:
        raise HTTPException(status_code=404, detail=f"Category {group}.{category} is not allowed for retrive")

    language_slug = request.headers.get('Accept-Language')
    language_context: LanguageContext = schema.get_language_context(language_slug)
    context = {'language_context': language_context}

    try:
        result: RetrieveResult = await schema_category.retrieve(pk, user, language_context, schema)
    except AdminAPIException as e:
        return JSONResponse(e.get_error().model_dump(mode='json', context=context), status_code=e.status_code)

    return JSONResponse(content=result.model_dump(mode='json', context=context))


@router.post(
    path='/{group}/{category}/create/',
    responses={400: {"model": APIError}},
)
async def table_create(request: Request, group: str, category: str) -> CreateResult:
    schema: AdminSchema = request.app.state.schema

    schema_category, user = await get_category(request, group, category, check_type=CategoryTable)
    if not schema_category.has_create:
        raise HTTPException(status_code=404, detail=f"Category {group}.{category} is not allowed for create")

    language_slug = request.headers.get('Accept-Language')
    language_context: LanguageContext = schema.get_language_context(language_slug)
    context = {'language_context': language_context}

    try:
        result: CreateResult = await schema_category.create(await request.json(), user, language_context, schema)
    except AdminAPIException as e:
        return JSONResponse(e.get_error().model_dump(mode='json', context=context), status_code=e.status_code)

    return JSONResponse(content=result.model_dump(mode='json', context=context))


@router.patch(
    path='/{group}/{category}/update/{pk}/',
    responses={400: {"model": APIError}},
)
async def table_update(request: Request, group: str, category: str, pk: Any) -> UpdateResult:
    schema: AdminSchema = request.app.state.schema

    schema_category, user = await get_category(request, group, category, check_type=CategoryTable)
    if not schema_category.has_update:
        raise HTTPException(status_code=404, detail=f"Category {group}.{category} is not allowed for update")

    language_slug = request.headers.get('Accept-Language')
    language_context: LanguageContext = schema.get_language_context(language_slug)
    context = {'language_context': language_context}

    try:
        result: UpdateResult = await schema_category.update(pk, await request.json(), user, language_context, schema)
    except AdminAPIException as e:
        return JSONResponse(e.get_error().model_dump(mode='json', context=context), status_code=e.status_code)

    return JSONResponse(content=result.model_dump(mode='json', context=context))


@router.post(
    path='/{group}/{category}/action/{action}/',
    responses={400: {"model": APIError}},
)
async def table_action(
        request: Request,
        group: str,
        category: str,
        action: str,
        action_data: ActionData,
) -> ActionResult:
    schema: AdminSchema = request.app.state.schema

    schema_category, user = await get_category(request, group, category, check_type=CategoryTable)

    language_slug = request.headers.get('Accept-Language')
    language_context: LanguageContext = schema.get_language_context(language_slug)
    context = {'language_context': language_context}

    try:
        # pylint: disable=protected-access
        result: ActionResult = await schema_category._perform_action(
            request, action, action_data, language_context, user, schema,
        )
    except AdminAPIException as e:
        return JSONResponse(e.get_error().model_dump(mode='json', context=context), status_code=e.status_code)

    return JSONResponse(content=result.model_dump(mode='json', context=context))
