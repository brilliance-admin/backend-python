import logging
import logging.config

import structlog
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from structlog.dev import RichTracebackFormatter

from brilliance_admin import schema
from brilliance_admin.auth import AdminAuthentication, AuthData, AuthResult, UserABC, UserResult
from brilliance_admin.exceptions import AdminAPIException, APIError
from brilliance_admin.translations import LanguageManager
from brilliance_admin.translations import TranslateText as _
from example.sections.currency import CurrencyAdmin
from example.sections.dashboard import DasbhoardExample
from example.sections.merchant import MerchantAdmin
from example.sections.payments import PaymentsAdmin
from example.sections.terminal import TerminalAdmin
from example.sections.user_session import UserSessionAdmin
from example.sections.users import UserAdmin
from example.database import async_sessionmaker_, lifespan

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.stdlib.ExtraAdder(),
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S", utc=False),
        structlog.dev.ConsoleRenderer(colors=True, sort_keys=True)
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.NOTSET),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=False
)

cr = structlog.dev.ConsoleRenderer.get_active()
cr.exception_formatter = RichTracebackFormatter(
    max_frames=1,
    show_locals=False,
    suppress=["uvicorn", "fastapi", "starlette"],
)


LOGIN_GREETINGS_MESSAGE = '''
<div class="text-h6 mb-1">
  Demo mode
</div>
<div class="text-caption">
  Login: admin<br>
  Password: admin
</div>
'''


class FakeAdminAuthentication(AdminAuthentication):
    async def login(self, data: AuthData, **kwargs) -> AuthResult:
        if data.username != 'admin' or data.password != 'admin':
            raise AdminAPIException(APIError(code='user_not_found'), status_code=401)

        return AuthResult(token='test', user=UserResult(username='test_admin'))

    async def authenticate(self, headers: dict) -> UserABC:
        return UserABC(username='test_admin')


custom_themes = [
    {
        "name": "pinkLight",
        "dark": False,
        "colors": {
            "light2": "#FBF5F7",
            "light3": "#E8D0D8",
            "secondary": "#C4A0AE",
            "darken1": "#A88392",
            "primary": "#D46B8A",
            "darken3": "#6B4458",
            "darken4": "#4A2E3D",
            "accent": "#D4A9B8",
            "error": "#C26161",
            "info": "#7BA4C9",
            "success": "#7BAF7F",
            "warning": "#C9A84E",
        },
    },
    {
        "name": "pinkDark",
        "dark": True,
        "colors": {
            "surface": "#160D12",
            "on-surface": "#F0E0E8",
            "light2": "#2E1825",
            "light3": "#E8A0B8",
            "secondary": "#5C3350",
            "darken1": "#D4789A",
            "primary": "#D46B8A",
            "on-primary": "#FFFFFF",
            "darken3": "#421E35",
            "darken4": "#0E0609",
            "accent": "#D4A9B8",
            "error": "#C26161",
            "info": "#7BA4C9",
            "success": "#7BAF7F",
            "warning": "#C9A84E",
        },
    },
]


admin_schema = schema.AdminSchema(
    title=_('admin_title'),
    description=_('admin_description'),
    login_greetings_message=_('login_greetings_message'),

    logo_image='/static/logo-outline.png',
    favicon_image='/static/favicon.jpg',

    main_page='/main/dashboard/',

    auth=FakeAdminAuthentication(),
    language_manager=LanguageManager(
        locales_dir='example/locales',
        languages={
            'en': 'English',
            'ru': 'Russian',
            'test': 'Test',
        },
    ),

    default_theme='deepPurpleDark',
    custom_themes=custom_themes,

    categories=[
        schema.CategoryLink(
            slug='docs',
            title=_('docs'),
            link='https://docs.brilliance-admin.com',
        ),
        schema.CategoryLink(
            slug='github',
            title="GitHub Repo",
            icon="mdi-github",
            link='https://github.com/brilliance-admin/backend-python',
        ),
        schema.CategoryGroup(
            slug='main',
            title=_('dashboard.title'),
            icon='mdi-finance',
            subcategories=[
                DasbhoardExample(),
            ]
        ),
        schema.CategoryGroup(
            slug='users',
            title=_('users'),
            icon='mdi-account',
            subcategories=[
                UserAdmin(db_async_session=async_sessionmaker_),
                UserSessionAdmin(db_async_session=async_sessionmaker_),
            ]
        ),
        schema.CategoryGroup(
            slug='payments',
            title=_('payments'),
            icon='mdi-folder-account-outline',
            subcategories=[
                PaymentsAdmin(),
                MerchantAdmin(db_async_session=async_sessionmaker_),
                TerminalAdmin(db_async_session=async_sessionmaker_),
            ]
        ),
        schema.CategoryGroup(
            slug='currencies',
            title=_('currencies'),
            icon='mdi-cash-multiple',
            subcategories=[
                CurrencyAdmin(db_async_session=async_sessionmaker_),
            ]
        ),
    ],
)

app = FastAPI(debug=True, lifespan=lifespan)
app.mount('/static', StaticFiles(directory='example/static'), name='static')

admin_app = admin_schema.generate_app(
    include_scalar=True, include_docs=True, include_redoc=True, debug=True,
)
app.mount('/admin', admin_app)


@app.get('/')
async def root():
    return RedirectResponse(url='/admin/')


@app.get('/health')
def health():
    return {'status': 'ok'}
