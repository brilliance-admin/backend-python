from brilliance_admin import sqlalchemy
from brilliance_admin.auth import UserABC
from brilliance_admin.schema.table.table_models import AutocompleteData
from brilliance_admin.translations import TranslateText as _
from example.sections.models import User, UserSession


async def users_filter(stmt, data: AutocompleteData, user: UserABC):
    return stmt.where(User.is_active == True)


class UserSessionAdmin(sqlalchemy.SQLAlchemyAdmin):
    model = UserSession
    title = _('user_sessions')
    icon = 'mdi-history'

    ordering_fields = [
        'id',
        'started_at',
        'ended_at',
    ]

    search_fields = [
        'ip_address',
        'city',
        'browser',
    ]

    table_schema = sqlalchemy.SQLAlchemyFieldsSchema(
        model=UserSession,
        extra_kwargs={
            'user_agent': {'read_only': True},
        },
    )

    table_filters = sqlalchemy.SQLAlchemyFieldsSchema(
        model=UserSession,
        exclude_fields=[],
        extra_kwargs={
            'user_id': {'filter_fn': users_filter},
            'started_at': {'range': True},
            'ended_at': {'range': True},
        },
    )
