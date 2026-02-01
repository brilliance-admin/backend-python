from brilliance_admin import schema, sqlalchemy
from brilliance_admin.translations import TranslateText as _

from example.sections.models import DeviceType, UserSession


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
    )

    table_filters = sqlalchemy.SQLAlchemyFieldsSchema(
        model=UserSession,
        started_at=schema.DateTimeField(range=True),
        ended_at=schema.DateTimeField(range=True),
        is_active=schema.BooleanField(),
        device_type=schema.ChoiceField(choices=DeviceType),
        country_code=schema.StringField(),
    )
