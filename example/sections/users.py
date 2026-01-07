from brilliance_admin import schema, sqlalchemy
from brilliance_admin.translations import TranslateText as _
from example.sections.models import User


class UserAdmin(sqlalchemy.SQLAlchemyAdmin):
    model = User
    title = _('users')
    icon = 'mdi-account-details'

    ordering_fields = [
        'id',
    ]
    search_fields = [
        'username',
    ]

    table_schema = sqlalchemy.SQLAlchemyFieldsSchema(
        model=User,
    )
    table_filters = sqlalchemy.SQLAlchemyFieldsSchema(
        model=User,
        created_at=schema.DateTimeField(range=True),
        last_login=schema.DateTimeField(range=True),
    )
