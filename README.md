<div align="center">
  <img src="https://github.com/brilliance-admin/backend-python/blob/main/example/static/logo-outline.png?raw=true"
       alt="Brilliance Admin"
       width="600">
</div>

<div align="center">

[![PyPI](https://img.shields.io/pypi/v/brilliance-admin)](https://pypi.org/project/brilliance-admin/)
[![License](https://img.shields.io/pypi/l/brilliance-admin)](https://github.com/brilliance-admin/backend-python/blob/main/LICENSE)
[![CI](https://github.com/brilliance-admin/backend-python/actions/workflows/deploy.yml/badge.svg)](https://github.com/brilliance-admin/backend-python/actions)

</div>

General-purpose admin panel framework powered by FastAPI. Some call it heavenly in its brilliance.

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
* Localization support with language selection in the interface.
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
    async def get_list(
            self,
            list_data: schema.ListData,
            user: auth.UserABC,
            language_manager: LanguageManager,
    ) -> schema.TableListResult:
        ...
        return schema.TableListResult(data=data, total_count=total_count)

    async def retrieve(
            self,
            pk: Any,
            user: auth.UserABC,
            language_manager: LanguageManager,
    ) -> schema.RetrieveResult:
        ...
        return schema.RetrieveResult(data=line)


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

Now, the `TerminalAdmin` instance can be passed to `categories`.

### Can be used both via inheritance and instancing

For `SQLAlchemyFieldsSchema`

``` python
class TerminalAdmin(sqlalchemy.SQLAlchemyAdmin):
    ...

    table_schema = sqlalchemy.SQLAlchemyFieldsSchema(
        model=Terminal, 
        list_display=['id', 'merchant_id'],
    )
    table_filters = sqlalchemy.SQLAlchemyFieldsSchema(
        model=Terminal, 
        fields=['id', 'created_at'],
        created_at=schema.DateTimeField(range=True),
    )
```

And `SQLAlchemyAdmin` category schema itself

> If `table_schema` is not specified, it will be generated automatically and will include all discovered fields and relationships of the table in the output.

``` python
category = sqlalchemy.SQLAlchemyAdmin(db_async_session=async_sessionmaker, model=Terminal)
```
