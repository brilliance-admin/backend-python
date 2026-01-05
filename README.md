# Brilliance Admin Backend

[![PyPI](https://img.shields.io/pypi/v/brilliance-admin)](https://pypi.org/project/brilliance-admin/)
[![License](https://img.shields.io/pypi/l/brilliance-admin)](https://github.com/brilliance-admin/backend-python/blob/main/LICENSE)
[![CI](https://github.com/brilliance-admin/backend-python/actions/workflows/deploy.yml/badge.svg)](https://github.com/brilliance-admin/backend-python/actions)

General-purpose admin panel framework powered by FastAPI. Some call it heavenly in its brilliance.

- Serves a prebuilt SPA frontend as static files
- Generates schemas for frontend sections on the backend
- Provides a backend-driven API for admin interfaces
- Designed for fast data management and data viewing from any sources
- Inspired by Django Admin and Django REST Framework
- Focused on minimal boilerplate and simplified backend-controlled configuration

### [Live Demo](https://brilliance-admin.com/) | [Example App](https://github.com/brilliance-admin/backend-python/tree/main/example) | Documentation (todo)


### Features:

* Tables with full CRUD support, including filtering, sorting, and pagination.
* Ability to define custom table actions with forms, response messages, and file uploads.
* SQLAlchemy integration with automatic field generation from models.
* Authorization via any account data source.
* Localization support with language selection in the interface.

## How to use it

You need to generate `AdminSchema` instance:
``` python
from admin_panel import schema

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

### SQLAlchemy integration
Brilliance Admin supports automatic schema generation from SQLAlchemy and provides a ready-made CRUD implementation for tables.

``` python
from admin_panel import sqlalchemy
from admin_panel.translations import TranslateText as _

from your_project.models import Terminal


class TerminalAdmin(sqlalchemy.SQLAlchemyAdmin):
    db_async_session = async_sessionmaker
    model = Terminal
    title = _('terminals')
    icon = 'mdi-console-network-outline'
    
    ordering_fields = ['id']
    search_fields = ['id', 'title']

    table_schema = sqlalchemy.SQLAlchemyFieldsSchema(
        model=Terminal, 
        list_display=['id', 'merchant_id'],
    )
    table_filters = sqlalchemy.SQLAlchemyFieldsSchema(
        model=Terminal, 
        fields=['id', 'created_at'],
        created_at=schema.DateTimeField(range=True),
    )


category = TerminalAdmin()
```

Now, the `TerminalAdmin` instance can be passed to `categories`.

### Can be used both via inheritance and instancing

For `SQLAlchemyFieldsSchema`

``` python
class TerminalTableSchema(sqlalchemy.SQLAlchemyFieldsSchema):
    model = Terminal
    fields = ['id', 'created_at']

    created_at=schema.DateTimeField(range=True)


class TerminalAdmin(sqlalchemy.SQLAlchemyAdmin):
    table_schema = TerminalTableSchema()
```

And `SQLAlchemyAdmin` category schema itself

> If `table_schema` is not specified, it will be generated automatically and will include all discovered fields and relationships of the table in the output.

``` python
category = sqlalchemy.SQLAlchemyAdmin(db_async_session=async_sessionmaker, model=Terminal)
```

