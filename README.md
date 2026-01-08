<div align="center">
  <img src="https://github.com/brilliance-admin/backend-python/blob/main/example/static/logo-outline.png?raw=true"
       alt="Brilliance Admin"
       width="600">

[![PyPI](https://img.shields.io/pypi/v/brilliance-admin)](https://pypi.org/project/brilliance-admin/)
[![CI](https://github.com/brilliance-admin/backend-python/actions/workflows/deploy.yml/badge.svg)](https://github.com/brilliance-admin/backend-python/actions)

Simple and lightweight admin panel framework powered by `FastAPI` and `Vue3` `Vuetify` together. \
Integrated with `SQLAlchemy`. Inspaired by Django Admin and DRF.\
_Some call it heavenly in its brilliance._

### [Live Demo](https://brilliance-admin.com/) | [Demo Sources](https://github.com/brilliance-admin/backend-python/tree/main/example) | Documentation (todo)

  <img src="https://github.com/brilliance-admin/backend-python/blob/main/screenshots/websitemockupgenerator.png?raw=true"
       alt="Preview">

</div>

**Key ideas:**
- **API oriented**\
Works entirely on FastAPI and provides a prebuilt SPA [frontend](https://github.com/brilliance-admin/frontend) via static files (Vue3 + Vuetify). No separate startup is required.
> Data generation/updating API separated from rendering fontend with zero hardcode, this makes it possible to have a single frontend with multiple backend implementations in different languages and makes test coverage easier.
- **Rich visualization**\
Providing rich and convenient ways to display and manage data (tables, charts, etc) from any data source.
- **ORM**\
Automatic schema generation and methods for CRUD operations.
- **Minimal boilerplate**\
Focused on simplified, but rich configuration.

**How it works:**
- After authentication, the user receives the admin panel schema, and the frontend renders it
- The frontend communicates with the backend via API to fetch and modify data

### Features:

* Tables with full CRUD support, including filtering, sorting, and pagination.
* Ability to define custom table actions with forms, response messages, and file downloads.
* Graphs via ChartJS
* Localization support
* Adapted for different screen sizes and mobile devices
* Authorization via any account data source

**Integrations:**
* **SQLAlchemy** - schema autogeneration for tables + CRUD operations + authorization

**Planned:**
* Role-based access control system
* Nested data support for creation and detail views
* Django ORM inegration

## How to use it

Installation:
``` shell
pip install brilliance-admin
```

You need to generate `AdminSchema` instance:
``` python
from brilliance_admin import schema


class CategoryExample(schema.CategoryTable):
    "Implementation of get_list and retrieve; update and create are optional"


admin_schema = schema.AdminSchema(
    title='Admin Panel',
    auth=YourAdminAuthentication(),
    groups=[
        schema.Group(
            slug='example',
            title='Example',
            icon='mdi-star',
            categories=[
                CategoryExample(),
            ]
        ),
    ],
)

admin_app = admin_schema.generate_app()

# Your FastAPI app
app = FastAPI()
app.mount('/admin', admin_app)
```

## SQLAlchemy integration

Supports automatic schema generation for CRUD tables:

``` python
category = sqlalchemy.SQLAlchemyAdmin(db_async_session=async_sessionmaker, model=Terminal)
```

> [!NOTE]
> If `table_schema` is not specified, it will be generated automatically with all discovered fields and relationships

Now, the `category` instance can be passed to `categories`.

### DRF class style schema

``` python
from brilliance_admin import sqlalchemy
from brilliance_admin.translations import TranslateText as _

from your_project.models import Terminal


class TerminalFiltersSchema(sqlalchemy.SQLAlchemyFieldsSchema):
    model = Terminal
    fields = ['id', 'created_at']
    created_at = schema.DateTimeField(range=True)


class TerminalSchema(sqlalchemy.SQLAlchemyFieldsSchema):
    model = Terminal
    list_display = ['id', 'merchant_id']


class TerminalAdmin(sqlalchemy.SQLAlchemyAdmin):
    db_async_session = async_sessionmaker
    model = Terminal
    title = _('terminals')
    icon = 'mdi-console-network-outline'
    
    ordering_fields = ['id']
    search_fields = ['id', 'title']

    table_schema = TerminalSchema()
    table_filters = TerminalFiltersSchema()


category = TerminalAdmin()
```

### Can be used both via inheritance and instancing

Optionally, functional-style generation can be used to reduce boilerplate code

Availiable for `SQLAlchemyAdmin` and `SQLAlchemyFieldsSchema`

``` python
category = sqlalchemy.SQLAlchemyAdmin(
    db_async_session=async_sessionmaker,
    model=Terminal,

    table_schema = sqlalchemy.SQLAlchemyFieldsSchema(
        model=Terminal, 
        list_display=['id', 'merchant_id'],
    ),
    table_filters = sqlalchemy.SQLAlchemyFieldsSchema(
        model=Terminal, 
        fields=['id', 'created_at'],
        created_at=schema.DateTimeField(range=True),
    ),
)
```

### SQLAlchemy JWT Authentication

``` python
auth = sqlalchemy.SQLAlchemyJWTAdminAuthentication(
    secret='auth_secret',
    db_async_session=async_session,
    user_model=User,
)
```

## Comparison of Similar Projects

| Criterion | Brilliance Admin | Django Admin | FastAPI Admin | Starlette Admin | SQLAdmin |
|---------|------------------|---------------------|---------------|-----------------|----------|
| Base framework | FastAPI | Django | FastAPI | Starlette / FastAPI | FastAPI / Starlette |
| Rendering model | Prebuilt Vue 3 + Vuetify SPA + Jinja2 | Server-side Django templates | Server-side Jinja2 templates + Tabler UI | Server-side Jinja2 templates + Tabler UI | Server-side Jinja2 templates + Bootstrap |
| Frontend architecture | Separate frontend (SPA) | Classic server-rendered UI | Server-rendered UI with JS interactivity | Server-rendered UI with JS interactivity | Server-rendered UI |
| Data source | Any source + SQLAlchemy | Django ORM | Tortoise ORM | Any source + SQLAlchemy, MongoDB | SQLAlchemy |
| Multiple databases per model | Yes | Database routers | No (global engine) | Yes (session per ModelView) | No (single engine per Admin) |
| Schema generation | User-defined format | From Django models | From ORM models | User-defined format | From SQLAlchemy models |
| Async support | Yes | No | Yes | Yes | Yes |
| API-first approach | Yes | No | Partially | Partially | No |
