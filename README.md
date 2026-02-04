<div align="center">
  <img src="https://github.com/brilliance-admin/backend-python/blob/main/example/static/logo-outline.png?raw=true"
       alt="Brilliance Admin"
       width="600">

[![PyPI](https://img.shields.io/pypi/v/brilliance-admin)](https://pypi.org/project/brilliance-admin/)
[![CI](https://github.com/brilliance-admin/backend-python/actions/workflows/deploy.yml/badge.svg)](https://github.com/brilliance-admin/backend-python/actions)

Simple and lightweight data management framework powered by `FastAPI` and `Vue3` `Vuetify` all-in-one. \
Integrated with `SQLAlchemy`. Inspaired by Django Admin and DRF.\
_Some call it heavenly in its brilliance._

### [Live Demo](https://brilliance-admin.com/) | [Demo Sources](https://github.com/brilliance-admin/backend-python/tree/main/example) | [Documentation](https://docs.brilliance-admin.com/)

Old repo: https://github.com/Innova-Group-LLC/custom_admin

  <img src="https://raw.githubusercontent.com/brilliance-admin/.github/refs/heads/main/screenshots/04.02.2026/all-devices-black.png"
       alt="Preview">

</div>

>Not production ready, work in progress.

## Что предоставляет данный проект
Проект позволяет быстро интегрировать панель управления в ваш ASGI бэкенд.

Кратко основные возможности:
- Современный и удобный вывод данных из любого источника.
- Быстрая настройка управления данными через действия.

Фронтэнд часть работает на заранее собранном фронтэнде - [Repo Vue3 + Vuetify](https://github.com/brilliance-admin/frontend). \
Проект не использует темплейты, за исключением одного, который рендерит этот фронт.

### Кастомизация:

Вся кастомизация делается из python кода: в каком виде выводить и откуда. \
Если желаемая кастомизация не предусмотрена из коробки - возможно модифицировать фронт и использовать его, но планируется покрыть все распространенные юзер-кейсы, чтобы этого не потребовалось.

## What This Project Do
The project allows you to quickly integrate an admin panel into your ASGI backend.

Key features at a glance:
- Modern and convenient data display from any source.
- Quick setup of data management through actions.

The frontend runs on a pre-built frontend - [Repo Vue3 + Vuetify](https://github.com/brilliance-admin/frontend). \
The project does not use templates, except for one that renders this frontend.

### Customization:

All customization is done from Python code: how to display data and where to get it from. \
If the desired customization is not available out of the box, you can modify the frontend and use your own version, but the goal is to cover all common use cases so that there will be no need for that.

## Installation:
``` shell
pip install brilliance-admin
```

## SQLAlchemy Category Example
``` python
class UserAdmin(sqlalchemy.SQLAlchemyAdmin):
    model = User
    
    table_schema = sqlalchemy.SQLAlchemyFieldsSchema(
        model=User,
        # Fields would be discovered automaticly if fields is not presented
        readonly_fields=[
            "last_login",
            "created_at",
        ],
    )
    table_filters = sqlalchemy.SQLAlchemyFieldsSchema(
        model=User,
        fields=[
            "id",
            "username",
            "email",
            "is_admin",
            "created_at",
        ],
        created_at=schema.DateTimeField(range=True),
    )
```

## Admin Action Example
```python
    @admin_action(
        title=_('change_password'),
        form_schema=schema.FieldsSchema(
            new_password=schema.StringField(label=_('new_password'), min_length=6, password=True)
        ),
    )
    async def change_password(self, action_data: ActionData):
        new_password = action_data.form_data['new_password']
        users_id = action_data.pks
        # Here is your logic
        return ActionResult(message=ActionMessage(_('password_changed')))
```

Result:
<div align="center">
  <img src="https://github.com/brilliance-admin/.github/blob/main/screenshots/04.02.2026/change-password.png?raw=true"
       alt="Brilliance Admin"
       width="600">
</div>

## Panel Instance Example

``` python
from brilliance_admin import schema
from apps.users import UserAdmin

async def password_validator(user: User, password: str) -> bool:
    return await User.verify_password(password, user.password)

auth = sqlalchemy.SQLAlchemyJWTAdminAuthentication(
    secret=settings.auth_secret,
    db_async_session=your_db.async_session,
    user_model=User,
    password_validator=password_validator,
)

admin_schema = schema.AdminSchema(
    title='Admin Panel',
    auth=auth,
    categories=[
        schema.Category(
            slug='users',
            categories=[UserAdmin(db_async_session=your_db.async_session)]
        ),
    ],
)

admin_app = admin_schema.generate_app()
```

``` python
# Your FastAPI app (Any ASGI framework can be used)
app = FastAPI()
app.mount('/admin', admin_app)
```

For more details, check out our [how-to-start documentation](https://docs.brilliance-admin.com/how-to-start/)

<details open>
<summary><h2>Screenshots</h2></summary>
<img src="https://github.com/brilliance-admin/.github/blob/main/screenshots/04.02.2026/login-white.png?raw=true"/>
<img src="https://github.com/brilliance-admin/.github/blob/main/screenshots/04.02.2026/dashboard-white.png?raw=true"/>
<img src="https://github.com/brilliance-admin/.github/blob/main/screenshots/04.02.2026/dashboard-black.png?raw=true"/>
<img src="https://github.com/brilliance-admin/.github/blob/main/screenshots/04.02.2026/table-white.png?raw=true"/>
</details>

## Features

* Dashboards (ChartJS + custom components)
* Tables with full CRUD support, including filtering, sorting, and pagination.
* Ability to define custom table actions with forms, response messages, and file downloads.
* Localization support
* Adapted for different screen sizes and mobile devices
* Auth via any account data source

**Integrations:**

* **SQLAlchemy** - schema autogeneration for tables + CRUD operations + authorization

**Planned:**

* Role-based access permissions system via interface
* Backend interface for storing and viewing action history in the admin interface
* Nested data support for creation and detail views (inline editing), nested CRUD workflows
* Django ORM integration
* Support for Oauth providers

## Comparison of Similar Projects

The project closest in concept is [React Admin](https://github.com/marmelab/react-admin). <br>
It is an SPA frontend that store the schema UI inside and works with separate API backend providers.

The key difference of Brilliance Admin is that its all-in-one. <br>
It is more focused on rapid setup for data management, without the need to work with frontend configuration, while it still available.

## Comparison of Similar Python Projects

| Criterion | Brilliance Admin | Django Admin | FastAPI Admin | Starlette Admin | SQLAdmin |
|---------|------------------|--------------|---------------|-----------------|----------|
| Base framework | FastAPI | Django | FastAPI | Starlette | FastAPI |
| ASGI compatible | Yes | Partial | Yes | Yes | Yes |
| Rendering model | Prebuilt Vue 3 + Vuetify SPA + Jinja2 | Server-side Django templates | Server-side Jinja2 templates + Tabler UI | Server-side Jinja2 templates + Tabler UI | Server-side Jinja2 templates + Bootstrap |
| Frontend architecture | Separate frontend (SPA) | Classic server-rendered UI | Server-rendered UI with JS interactivity | Server-rendered UI with JS interactivity | Server-rendered UI |
| Data source | Any source + SQLAlchemy | Django ORM | Tortoise ORM | Any source + SQLAlchemy, MongoDB | SQLAlchemy |
| Multiple databases per model | Yes | Database routers | No (global engine) | Yes (session per ModelView) | No (single engine per Admin) |
| Schema generation | User-defined format | From Django models | From ORM models | User-defined format | From SQLAlchemy models |
| Async support | Yes | No | Yes | Yes | Yes |
| API-first approach | Yes | No | Partially | Partially | No |
| Built-in Localization | Yes | Yes | No | No | No |
