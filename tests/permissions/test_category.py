from brilliance_admin.auth import UserABC
from brilliance_admin.permissions.category import PermissionsSettingsCategory
from brilliance_admin.schema.admin_schema import AdminSchema
from brilliance_admin.schema.category import CategoryGroup
from brilliance_admin.schema.table.fields.base import ChoiceField
from example.main import admin_schema
from example.sections.user_session import UserSessionAdmin
from example.sections.users import UserAdmin


def test_permissions_category_generates_rules_on_startup(postgres_sessionmaker):
    permissions_category = PermissionsSettingsCategory()
    user_category = UserAdmin(
        db_async_session=postgres_sessionmaker,
        subcategories=[UserSessionAdmin(db_async_session=postgres_sessionmaker)],
    )

    test_schema = AdminSchema(
        auth=admin_schema.auth,
        categories=[
            CategoryGroup(slug='users', subcategories=[user_category]),
            CategoryGroup(slug='permissions', subcategories=[permissions_category]),
        ],
    )

    fields = permissions_category.table_schema.get_fields()
    assert set(fields) == {
        'users.user.list',
        'users.user.retrieve',
        'users.user.create',
        'users.user.update',
        'users.user.admin_action.delete',
        'users.user.admin_action.change_password',
        'users.user.usersession.list',
        'users.user.usersession.retrieve',
        'users.user.usersession.create',
        'users.user.usersession.update',
        'users.user.usersession.admin_action.delete',
    }
    field = fields['users.user.admin_action.change_password']
    assert isinstance(field, ChoiceField)
    choices = field.generate_choices()
    assert [choice['value'] for choice in choices] == ['inherit', 'allow', 'deny']
    language_context = test_schema.get_language_context('ru')
    assert [language_context.get_text(choice['title']) for choice in choices] == [
        'Наследовать', 'Разрешить', 'Запретить',
    ]

    result = test_schema.generate_admin_schema(UserABC(username='test_admin'), 'en')
    category_data = result.categories['permissions']['categories']['permissions-settings']
    assert set(category_data['table_info']['table_schema']['fields']) == set(fields)
