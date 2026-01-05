import logging
from fastapi.staticfiles import StaticFiles
import logging.config

import structlog
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from structlog.dev import RichTracebackFormatter

from admin_panel import schema
from admin_panel.auth import AdminAuthentication, AuthData, AuthResult, UserABC, UserResult
from admin_panel.exceptions import AdminAPIException, APIError
from admin_panel.translations import LanguageManager
from admin_panel.translations import TranslateText as _
from example.phrases import LANGUAGES_PHRASES
from example.sections.currency import CurrencyAdmin
from example.sections.graphs import GraphsExample
from example.sections.merchant import MerchantAdmin
from example.sections.payments import PaymentsAdmin
from example.sections.terminal import TerminalAdmin
from example.sections.users import UserAdmin
from example.sqlite import async_sessionmaker_, lifespan

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


class CustomLanguageManager(LanguageManager):
    languages = {
        'ru': 'Russian',
        'en': 'English',
        'test': 'Test',
    }
    languages_phrases = LANGUAGES_PHRASES


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
    async def login(self, data: AuthData) -> AuthResult:
        if data.username != 'admin' or data.password != 'admin':
            raise AdminAPIException(APIError(code='user_not_found'), status_code=401)

        return AuthResult(token='test', user=UserResult(username='test_admin'))

    async def authenticate(self, headers: dict) -> UserABC:
        return UserABC(username='test_admin')


admin_schema = schema.AdminSchema(
    title=_('admin_title'),
    description=_('admin_description'),
    login_greetings_message=_('login_greetings_message'),
    logo_image='/static/logo-outline.png',

    auth=FakeAdminAuthentication(),
    language_manager_class=CustomLanguageManager,

    groups=[
        schema.Group(
            slug='payments',
            title=_('payments'),
            icon='mdi-cash-multiple',
            categories=[
                PaymentsAdmin(),
            ]
        ),
        schema.Group(
            slug='users',
            title=_('users'),
            icon='mdi-account',
            categories=[
                UserAdmin(db_async_session=async_sessionmaker_),
            ]
        ),
        schema.Group(
            slug='merchants',
            title=_('merchants'),
            icon='mdi-folder-account-outline',
            categories=[
                MerchantAdmin(db_async_session=async_sessionmaker_),
                TerminalAdmin(db_async_session=async_sessionmaker_),
            ]
        ),
        schema.Group(
            slug='currencies',
            title=_('currencies'),
            icon='mdi-cash-multiple',
            categories=[
                CurrencyAdmin(db_async_session=async_sessionmaker_),
            ]
        ),
        schema.Group(
            slug='statistics',
            title=_('statistics'),
            icon='mdi-finance',
            categories=[
                GraphsExample(),
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
