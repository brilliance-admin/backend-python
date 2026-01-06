<div align="center">
  <img src="https://github.com/brilliance-admin/backend-python/blob/main/example/static/logo-outline.png?raw=true"
       alt="Brilliance Admin"
       width="600">
</div>

<div align="center">

[![PyPI](https://img.shields.io/pypi/v/brilliance-admin)](https://pypi.org/project/brilliance-admin/)
[![License](https://img.shields.io/pypi/l/brilliance-admin)](https://github.com/brilliance-admin/backend-python/blob/main/LICENSE)
[![CI](https://github.com/brilliance-admin/backend-python/actions/workflows/deploy.yml/badge.svg)](https://github.com/brilliance-admin/backend-python/actions)

General-purpose admin panel framework powered by FastAPI. Some call it heavenly in its brilliance.

  <img src="https://github.com/brilliance-admin/backend-python/blob/main/screenshots/websitemockupgenerator.png?raw=true"
       alt="Preview">

</div>

**Key ideas:**
- Providing rich ways to display and manage data (tables, charts etc) from any data sources
- Automatic schema generation from ORM (SQLAlchemy models implemented)
- The backend is separated from the frontend, with no hardcoding, but the frontend is embedded via static files and does not require a separate runtime.
- Focused on minimal boilerplate and simplified, but rich configuration

**How it works:**
- Works entirely on FastAPI and provides a prebuilt SPA via static files (Vue3 + Vuetify)
- After authentication, the user receives the admin panel schema, and the frontend renders it
- The frontend communicates with the backend via API to fetch and modify data


### [Live Demo](https://brilliance-admin.com/) | [Example App](https://github.com/brilliance-admin/backend-python/tree/main/example) | Documentation (todo)

### Features:

* Tables with full CRUD support, including filtering, sorting, and pagination.
* Ability to define custom table actions with forms, response messages, and file downloads.
* SQLAlchemy integration with automatic field generation from models.
* Authorization via any account data source.
* Localization support.
* Adapted for different screen sizes and mobile devices.

**Planned:**
* Role-based access control system
* Nested data support for creation and detail views

## How to use it

Installation:
``` shell
pip install brilliance-admin
```

You need to generate `AdminSchema` instance:
``` python
from admin_panel import schema


class CategoryExample(schema.CategoryTable):
    "Implementation of get_list and retrieve, update and create are optional"


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

### Django Rest Framework class style schema

``` python
from admin_panel import sqlalchemy
from admin_panel.translations import TranslateText as _

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

| Criterion | Brilliance Admin | Django Unfold | FastAPI Admin |
|---------|------------------|---------------|---------------|
| Base framework | FastAPI | Django | FastAPI |
| Rendering model | Prebuilt Vuetify Vue3 SPA + Jinja2 | Server-side Django templates | Server-side templates Jinja2 + Tabler UI |
| Frontend architecture | Separate frontend (SPA) | Classic server-rendered UI | Server-rendered UI with JS interactivity |
| Data Source | Any source + SQLAlchemy | Django ORM | Tortoise ORM |
| Schema generation | Dynamic, schema-first | From Django models | From ORM models |
| Async support | Yes | No | Yes |
| API-first approach | Yes | No | Partially |
