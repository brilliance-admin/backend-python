from brilliance_admin import schema, sqlalchemy
from brilliance_admin.auth import UserABC
from brilliance_admin.schema.table.admin_action import ActionData, ActionResult, admin_action
from brilliance_admin.schema.table.table_models import AutocompleteData
from brilliance_admin.translations import TranslateText as _
from example.sections.models import City, User
from sqlalchemy.orm import selectinload


async def cities_filter(stmt, data: AutocompleteData, user: UserABC):
    country = data.form_data.get('country_id')
    country_id = country.get('key') if isinstance(country, dict) else country

    if not country_id:
        return stmt.where(False)

    return stmt.options(selectinload(City.country)).where(City.country_id == country_id)


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
        exclude_fields=['password'],
        extra_kwargs={
            'city_id': {
                'filter_fn': cities_filter,
                'help_text': _('city_country_filter_help_text'),
            },
        },
        formset=schema.FormSet(
            fields=[
                schema.FormSet(
                    fields=[
                        'id',
                        'username',
                        'email',
                    ],
                ),
                schema.FormSet(
                    fields=[
                        schema.FormField('country_id', col_span=6),
                        schema.FormField('city_id', col_span=6),
                    ],
                ),
                schema.FormSet(
                    fields=[
                        'is_staff',
                        'is_admin',
                        'is_active',
                    ],
                ),
                schema.FormSet(
                    fields=[
                        schema.FormField('last_login', col_span=6),
                        schema.FormField('created_at', col_span=6),
                    ],
                ),
            ],
        ),
        list_display=[
            'username',
            'email',
            'country_id',
            'city_id',
            'is_staff',
            'is_admin',
            'is_active',
            'last_login',
            'created_at',
        ],
    )
    table_filters = sqlalchemy.SQLAlchemyFieldsSchema(
        model=User,
        created_at=schema.DateTimeField(
            range=True,
            filter_subtable=sqlalchemy.PostgreSQLFilterSubtable(),
        ),
        last_login=schema.DateTimeField(range=True),
        exclude_fields=['password'],
        extra_kwargs={
            'city_id': {
                'filter_fn': cities_filter,
                'help_text': _('city_country_filter_help_text'),
            },
        },
    )

    @admin_action(
        title=_('password.change_password'),
        icon='mdi-lock-reset',
        form_schema=schema.FieldsSchema(
            new_password=schema.StringField(label=_('password.new_password'), min_length=6, password=True)
        ),
    )
    async def change_password(self, action_data: ActionData, **kwargs):
        return ActionResult(_('password.password_changed'))
