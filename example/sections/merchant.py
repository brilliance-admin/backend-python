from brilliance_admin import schema, sqlalchemy
from brilliance_admin.translations import TranslateText as _
from example.sections.models import Merchant, MerchantStatus


class MerchantFieldsSchema(sqlalchemy.SQLAlchemyFieldsSchema):
    model = Merchant
    readonly_fields = [
        'created_at',
    ]
    fields = [
        'id',
        'user_id',
        'is_active',
        'title',
        'status',
        'provider_settings',
        'tx_actions',
        'description',
        'created_at',
        'terminals',
    ]
    list_display = [
        'id',
        'user_id',
        'title',
        'status',
        'tx_actions',
        'description',
        'created_at',
        'terminals',
    ]

    title = schema.StringField(multilined=True, required=True)
    status = schema.IntegerField(choices=MerchantStatus)
    description = schema.StringField(tinymce=True, help_text='help text', required=True)
    extra_kwargs = {
        'tx_actions': {'help_text': 'help text'},
        'terminals': {'help_text': 'help text'},
    }


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

    table_schema = MerchantFieldsSchema()
    table_filters = sqlalchemy.SQLAlchemyFieldsSchema(
        model=Merchant,
        fields=[
            'id',
            'user_id',
            'created_at',
            'terminals',
            'is_active',
        ],
        created_at=schema.DateTimeField(range=True, label='Created at long-long label'),
    )
