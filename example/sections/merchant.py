from brilliance_admin import schema, sqlalchemy
from brilliance_admin.translations import TranslateText as _
from example.sections.models import Merchant


class MerchantAdmin(sqlalchemy.SQLAlchemyAdmin):
    model = Merchant
    title = _('merchants')
    icon = 'mdi-card-account-details-outline'

    ordering_fields = [
        'id',
        'user_id',
    ]
    search_fields = [
        'id',
        'title',
    ]

    table_schema = sqlalchemy.SQLAlchemyFieldsSchema(
        model=Merchant,
        readonly_fields=[
            'created_at',
        ],
        fields=[
            'id',
            'user_id',
            'title',
            'provider_settings',
            'tx_actions',
            'description',
            'created_at',
            'terminals',
            'disputes',
        ],
        title=schema.StringField(multilined=True, required=True),
        description=schema.StringField(tinymce=True, required=True),
        disputes=schema.InlineField(
            label=_('disputes'),
            help_text=_('disputes_help_text'),
            table_schema=schema.FieldsSchema(
                id=schema.IntegerField(label='ID', read_only=True),
                reason=schema.StringField(label=_('Name')),
                manager=schema.RelatedField(label=_('Manager')),
                created_at=schema.DateTimeField(label=_('created_at'), read_only=True),
            )
        ),
    )
    table_filters = sqlalchemy.SQLAlchemyFieldsSchema(
        model=Merchant,
        fields=[
            'id',
            'user_id',
            'created_at',
            'terminals',
        ],
        created_at=schema.DateTimeField(range=True),
    )
