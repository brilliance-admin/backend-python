from brilliance_admin import schema, sqlalchemy
from brilliance_admin.schema.table.admin_action import ActionData, ActionMessage, ActionResult, admin_action
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
        list_display=[
            'username',
            'email',
            'is_staff',
            'is_admin',
            'is_active',
            'last_login',
            'created_at',
        ],
    )
    table_filters = sqlalchemy.SQLAlchemyFieldsSchema(
        model=User,
        created_at=schema.DateTimeField(range=True),
        last_login=schema.DateTimeField(range=True),
    )

    @admin_action(
        title=_('password.change_password'),
        form_schema=schema.FieldsSchema(
            new_password=schema.StringField(label=_('password.new_password'), min_length=6, password=True)
        ),
    )
    async def change_password(self, action_data: ActionData):
        return ActionResult(_('password.password_changed'))
