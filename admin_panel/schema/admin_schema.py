import importlib.metadata
import json
from importlib import resources
from typing import Any, Dict, List, Optional, Type
from urllib.parse import urljoin

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic.dataclasses import dataclass

from admin_panel.auth import UserABC
from admin_panel.docs import build_redoc_docs, build_scalar_docs
from admin_panel.schema.group import Group, GroupSchemaData
from admin_panel.translations import LanguageManager, TranslateText
from admin_panel.utils import DataclassBase


@dataclass
class AdminSchemaData(DataclassBase):
    groups: Dict[str, GroupSchemaData]
    profile: UserABC | Any

    def __post_init__(self):
        if not isinstance(self.profile, UserABC):
            self.profile = UserABC(username=self.profile.username)


# pylint: disable=too-many-instance-attributes
@dataclass
class AdminSettingsData(DataclassBase):
    title: str | TranslateText
    description: str | TranslateText | None
    login_greetings_message: str | TranslateText | None
    navbar_density: str
    logo_image: str | None
    languages: Dict[str, str] | None


@dataclass
class AdminIndexContextData(DataclassBase):
    title: str
    favicon_image: str
    settings_json: str


@dataclass
class AdminSchema:
    groups: List[Group]
    auth: Any

    title: str | TranslateText | None = 'Admin'
    description: str | TranslateText | None = None
    login_greetings_message: str | TranslateText | None = None
    navbar_density: str = 'default'

    favicon_image: str = '/admin/static/favicon.ico'
    backend_prefix = None
    static_prefix = None

    language_manager_class: Type[LanguageManager] = LanguageManager

    def __post_init__(self):
        for group in self.groups:
            if not issubclass(group.__class__, Group):
                raise TypeError(f'Group "{group}" is not instance of Group subclass')

    def get_language_manager(self, language_slug: str | None) -> LanguageManager:
        return self.language_manager_class(language_slug)

    def generate_schema(self, user: UserABC, language_slug: str | None) -> AdminSchemaData:
        language_manager: LanguageManager = self.get_language_manager(language_slug)

        groups = {}

        for group in self.groups:
            if not group.slug:
                msg = f'Category group {type(group).__name__}.slug is empty'
                raise AttributeError(msg)

            groups[group.slug] = group.generate_schema(user, language_manager)

        return AdminSchemaData(
            groups=groups,
            profile=user,
        )

    def get_group(self, group_slug: str) -> Optional[Group]:
        for group in self.groups:
            if group.slug == group_slug:
                return group

        return None

    async def get_settings(self, request: Request) -> AdminSettingsData:
        language_slug = request.headers.get('Accept-Language')
        language_manager: LanguageManager = self.get_language_manager(language_slug)

        languages = None
        if language_manager.languages:
            languages = {}
            for k, v in language_manager.languages.items():
                languages[k] = language_manager.get_text(v)

        return AdminSettingsData(
            title=self.title,
            description=self.description,
            login_greetings_message=self.login_greetings_message,
            navbar_density=self.navbar_density,
            logo_image=None,
            languages=languages,
        )

    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-positional-arguments
    def generate_app(
            self,
            debug=False,
            allow_cors=True,

            include_scalar=False,
            include_docs=False,
            include_redoc=False,
    ) -> FastAPI:
        # pylint: disable=unused-variable
        language_manager = self.get_language_manager(language_slug=None)

        app = FastAPI(
            title=language_manager.get_text(self.title),
            description=language_manager.get_text(self.description),
            debug=debug,
            docs_url='/docs' if include_docs else None,
            redoc_url=None,
        )

        if allow_cors:
            app.add_middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"]
            )

        static_dir = resources.files("admin_panel").joinpath("static")
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

        app.state.schema = self

        if include_scalar:
            app.include_router(build_scalar_docs(app))

        if include_redoc:
            app.include_router(build_redoc_docs(app, redoc_url='/redoc'))

        # pylint: disable=import-outside-toplevel
        from admin_panel.api.routers import admin_panel_router
        app.include_router(admin_panel_router)

        return app

    async def get_index_context_data(self, request: Request) -> dict:
        language_manager = self.get_language_manager(language_slug=None)
        context = {'language_manager': language_manager}

        backend_prefix = self.backend_prefix
        if not backend_prefix:
            backend_prefix = urljoin(str(request.base_url), '/admin/')

        static_prefix = self.static_prefix
        if not static_prefix:
            static_prefix = urljoin(str(request.base_url), '/admin/static/')

        settings_json = {
            'backend_prefix': backend_prefix,
            'static_prefix': static_prefix,
            'version': importlib.metadata.version('admin-panel'),
            'api_timeout_ms': 1000 * 5,
        }
        data = AdminIndexContextData(
            title=str(self.title),
            favicon_image=self.favicon_image,
            settings_json=json.dumps(settings_json),
        )
        return data.model_dump(mode='json', context=context)
