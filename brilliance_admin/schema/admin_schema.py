import importlib.metadata
import json
import traceback
from copy import deepcopy
from html import escape
from importlib import resources
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import Field
from pydantic.dataclasses import dataclass

from brilliance_admin.auth import UserABC
from brilliance_admin.docs import build_redoc_docs, build_scalar_docs
from brilliance_admin.schema.category import BaseCategory, TableOptions
from brilliance_admin.translations import LanguageContext, LanguageManager
from brilliance_admin.utils import DataclassBase, SupportsStr, get_logger

DEFAULT_LANGUAGES = {
    'ru': 'Russian',
    'en': 'English',
}

logger = get_logger()


def format_limited_debug_traceback(exc: Exception, limit: int) -> str:
    return escape(''.join(
        traceback.format_exception(
            type(exc),
            exc,
            exc.__traceback__,
            limit=-limit,
        )
    ))


def add_limited_debug_traceback_middleware(app: FastAPI, traceback_limit: int) -> None:
    @app.middleware('http')
    async def limited_debug_traceback_middleware(request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as e:
            logger.exception('Unhandled admin exception: %s', e)
            return PlainTextResponse(format_limited_debug_traceback(e, traceback_limit), status_code=500)


@dataclass
class AdminSchemaData(DataclassBase):
    profile: UserABC | Any
    categories: Dict[str, dict] = Field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.profile, UserABC):
            self.profile = UserABC(username=self.profile.username)


# pylint: disable=too-many-instance-attributes
@dataclass
class AdminSettingsData(DataclassBase):
    title: SupportsStr
    description: SupportsStr | None
    login_greetings_message: SupportsStr | None
    navbar_density: str
    languages: Dict[str, str] | None
    main_page: str | None = None


@dataclass
class AdminIndexContextData(DataclassBase):
    title: str
    favicon_image: str | None
    settings_json: str


@dataclass
class AdminSchema:
    categories: List[BaseCategory]
    auth: Any

    api_timeout_ms: int = 1000 * 5
    debug_traceback_limit: int = 7

    main_page: str | None = None

    title: SupportsStr | None = 'Admin'
    description: SupportsStr | None = None
    login_greetings_message: SupportsStr | None = None

    logo_image: str | None = None
    favicon_image: str | None = None

    navbar_density: str = 'default'

    base_url: str | None = None
    backend_prefix: str | None = None
    static_prefix: str | None = None

    language_manager: LanguageManager | None = None

    default_theme: str | None = None
    custom_themes: List[dict] = Field(default_factory=list)
    default_table_options: TableOptions = Field(default_factory=TableOptions)

    def __post_init__(self):
        for category in self.categories:
            if not issubclass(category.__class__, BaseCategory):
                raise TypeError(f'Root category "{category}" is not subclass of BaseCategory')
            self._apply_default_table_options(category)

        if not self.language_manager:
            self.language_manager = LanguageManager(DEFAULT_LANGUAGES)

    def _apply_default_table_options(self, category: BaseCategory) -> None:
        if getattr(category, '_type_slug', None) == 'table' and category.options is None:
            category.options = deepcopy(self.default_table_options)

        for subcategory in getattr(category, 'subcategories', []):
            self._apply_default_table_options(subcategory)

    def get_language_context(self, language_slug: str | None) -> LanguageContext:
        return LanguageContext(language_slug, language_manager=self.language_manager)

    def generate_admin_schema(self, user: UserABC, language_slug: str | None) -> AdminSchemaData:
        language_context: LanguageContext = self.get_language_context(language_slug)

        result = AdminSchemaData(profile=user)

        for category in self.categories:
            if not category.slug:
                msg = f'Category {type(category).__name__}.slug is empty'
                raise AttributeError(msg)

            try:
                category_schema = category.generate_category_schema(
                    user,
                    language_context,
                    admin_schema=self,
                )
                result.categories[category.slug] = category_schema.to_dict(keep_none=False)
            except Exception as e:
                msg = f'Root category "{category.slug}" generate_schema error: {e}'
                raise Exception(msg) from e

        return result

    def get_group(self, group_slug: str) -> Optional[BaseCategory]:
        for category in self.categories:
            if category.slug == group_slug:
                return category

        return None

    async def get_settings(self, request: Request) -> AdminSettingsData:
        language_slug = request.headers.get('Accept-Language')
        language_context: LanguageContext = self.get_language_context(language_slug)  # noqa: F841

        languages = None
        if self.language_manager.languages:
            languages = {}
            for k, v in self.language_manager.languages.items():
                languages[k] = v

        return AdminSettingsData(
            title=self.title,
            main_page=self.main_page,
            description=self.description,
            login_greetings_message=self.login_greetings_message,
            navbar_density=self.navbar_density,
            languages=languages,
        )

    def generate_app(
            self,
            debug=False,
            default_cors=True,

            include_scalar=False,
            include_docs=False,
            include_redoc=False,
    ) -> FastAPI:
        self.debug = debug

        # pylint: disable=unused-variable
        language_context = self.get_language_context(language_slug=None)

        app = FastAPI(
            title=language_context.get_text(self.title),
            description=language_context.get_text(self.description),
            debug=debug,
            docs_url='/docs' if include_docs else None,
            redoc_url=None,
        )

        if debug:
            add_limited_debug_traceback_middleware(app, self.debug_traceback_limit)
            self.run_debug_startup_checks()

        if default_cors:
            allow_origins = [self.backend_prefix.rstrip('/')] if self.backend_prefix else ["*"]
            app.add_middleware(
                CORSMiddleware,
                allow_origins=allow_origins,
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )

        static_dir = resources.files("brilliance_admin").joinpath("static")
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

        app.state.schema = self

        if include_scalar:
            app.include_router(build_scalar_docs(app))

        if include_redoc:
            app.include_router(build_redoc_docs(app, redoc_url='/redoc'))

        # pylint: disable=import-outside-toplevel
        from brilliance_admin.api.routers import brilliance_admin_router
        from brilliance_admin.exceptions import APIError, FieldError
        app.include_router(brilliance_admin_router)

        @app.exception_handler(RequestValidationError)
        async def validation_exception_handler(request: Request, exc: RequestValidationError):
            language_slug = request.headers.get('Accept-Language')
            language_context = self.get_language_context(language_slug)
            context = {'language_context': language_context}

            field_errors = {}
            for error in exc.errors():
                field_slug = str(error['loc'][-1]) if error['loc'] else 'unknown'
                field_errors[field_slug] = FieldError(message=error['msg'], field_slug=field_slug)

            api_error = APIError(code='validation_error', field_errors=field_errors)
            return JSONResponse(api_error.model_dump(mode='json', context=context), status_code=400)

        return app

    def run_debug_startup_checks(self):
        for category in self.iter_categories():
            check = getattr(category, 'run_debug_startup_checks', None)
            if check is not None:
                check()

    def iter_categories(self):
        stack = list(self.categories)
        while stack:
            category = stack.pop(0)
            yield category
            stack.extend(getattr(category, 'subcategories', []) or [])

    async def get_index_context_data(self, request: Request) -> dict:
        language_context = self.get_language_context(language_slug=None)
        context = {'language_context': language_context}
        resolved_base_url = self.base_url

        backend_prefix = self.backend_prefix
        if backend_prefix is None:
            backend_prefix = '/admin/'

        static_prefix = self.static_prefix
        if static_prefix is None:
            static_prefix = '/admin/static/'

        logo_image = self.logo_image
        if logo_image and logo_image.startswith('/') and resolved_base_url is not None:
            logo_image = urljoin(resolved_base_url, logo_image)

        settings_json = {
            'base_url': self.base_url,
            'backend_prefix': backend_prefix,
            'static_prefix': static_prefix,
            'version': importlib.metadata.version('brilliance-admin'),
            'api_timeout_ms': self.api_timeout_ms,
            'backend_debug': self.debug,
            'logo_image': logo_image,
            'default_theme': self.default_theme,
            'custom_themes': self.custom_themes,
        }
        data = AdminIndexContextData(
            title=str(self.title),
            favicon_image=self.favicon_image,
            settings_json=json.dumps(settings_json),
        )
        return data.model_dump(mode='json', context=context)
