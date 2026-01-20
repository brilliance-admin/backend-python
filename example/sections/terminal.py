from brilliance_admin import sqlalchemy
from brilliance_admin.translations import TranslateText as _
from example.sections.models import Terminal


class TerminalAdmin(sqlalchemy.SQLAlchemyAdmin):
    has_create = False
    has_update = False
    has_delete = False

    model = Terminal
    title = _('terminals')
    icon = 'mdi-console-network-outline'

    ordering_fields = [
        'id',
    ]
    search_fields = [
        'id',
        'title',
    ]

    table_schema = sqlalchemy.SQLAlchemyFieldsSchema(
        model=Terminal,
        list_display=[
            'id',
            'status',
            'manager_id',
            'merchant_id',
            'public_id',
            'currency_id',
            'title',
            'is_h2h',
            'imitation_api',
            'test_mode',
            'is_active',
        ],
        readonly_fields=['errors'],
    )
    table_filters = sqlalchemy.SQLAlchemyFieldsSchema(
        model=Terminal,
        fields=[
            'id',
            'created_at',
            'merchant_id',
            'currency_id',
        ]
    )
