from brilliance_admin import schema, sqlalchemy
from brilliance_admin.translations import TranslateText as _
from example.sections.models import PrivacyPolicyVersion


class PrivacyPolicyVersionFieldsSchema(sqlalchemy.SQLAlchemyFieldsSchema):
    model = PrivacyPolicyVersion
    list_display = [
        'version',
        'title',
        'is_active',
        'published_at',
        'created_at',
    ]

    content = schema.StringField(tinymce=True, allow_html=True, required=True)


class PrivacyPolicyVersionAdmin(sqlalchemy.SQLAlchemyAdmin):
    model = PrivacyPolicyVersion
    title = _('privacy_policy_versions')
    icon = 'mdi-shield-lock-outline'
    has_create = False
    has_update = False

    ordering_fields = [
        'id',
        'published_at',
        'created_at',
    ]

    table_schema = PrivacyPolicyVersionFieldsSchema()
