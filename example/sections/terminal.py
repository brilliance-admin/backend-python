from brilliance_admin import sqlalchemy
from brilliance_admin.translations import TranslateText as _
from example.sections.models import Fee, Terminal


class FeeFieldsSchema(sqlalchemy.SQLAlchemyFieldsSchema):
    model = Fee
    extra_kwargs = {
        'fix_amount': {'min_value': 0},
    }


class FeeAdmin(sqlalchemy.SQLAlchemyAdmin):
    model = Fee
    title = _('fees')

    ordering_fields = [
        'id',
    ]
    search_fields = [
        'id',
        'title',
    ]

    table_schema = FeeFieldsSchema()


class TerminalFieldsSchema(sqlalchemy.SQLAlchemyFieldsSchema):
    model = Terminal
    list_display = [
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
    ]
    readonly_fields = ['errors', 'created_at']

    fees = sqlalchemy.SQLAlchemyInlineField(
        label=_('fees'),
        help_text=_('fees_help_text'),
        many=True,
        table_schema=FeeFieldsSchema(),
    )


class TerminalAdmin(sqlalchemy.SQLAlchemyAdmin):
    has_create = False
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

    table_schema = TerminalFieldsSchema()
    table_filters = sqlalchemy.SQLAlchemyFieldsSchema(
        model=Terminal,
        fields=[
            'id',
            'created_at',
            'merchant_id',
            'currency_id',
        ],
    )
