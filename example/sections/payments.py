import asyncio
import datetime
import traceback
import uuid
from typing import Any

from faker import Faker

from brilliance_admin import auth, schema
from brilliance_admin.exceptions import FieldError
from brilliance_admin.schema.table.admin_action import ActionData, ActionResult, admin_action
from brilliance_admin.translations import LanguageContext
from brilliance_admin.translations import TranslateText as _
from brilliance_admin.utils import get_logger
from example.sections.models import TerminalStatuses

logger = get_logger()


class PaymentFiltersSchema(schema.FieldsSchema):
    id = schema.IntegerField(label='ID', help_text='ID help text\nhelp text')
    created_at = schema.DateTimeField(label=_('created_at'), range=True)
    status = schema.ChoiceField(label='Status', required=True, choices=TerminalStatuses)

    fields = [
        'id',
        'status',
        'created_at',
    ]


class PaymentFieldsSchema(schema.FieldsSchema):
    list_display = [
        'id',
        'amount',
        'endpoint',
        'status',
        'created_at',
        'get_provider_registry',
        'get_provider_registry_info',
    ]

    id = schema.IntegerField(label='ID', read_only=True)
    amount = schema.IntegerField(label=_('amount'), read_only=True, required=True)
    endpoint = schema.StringField(label=_('endpoint'))
    description = schema.StringField(label=_('description'), help_text='help text example')
    other_field = schema.StringField(read_only=True)
    status = schema.ChoiceField(label=_('status'), required=True, choices=TerminalStatuses)
    whitelist_ips = schema.ArrayField(label=_('whitelist_ips'), help_text=_('whitelist_ips__help_text'))
    # image = schema.ImageField(label=_('image'))
    gateway_settings = schema.JSONField(help_text='help text', read_only=True)
    created_at = schema.DateTimeField(label=_('created_at'), read_only=True)

    formset = schema.FormSet(
        fields=[
            schema.FormSet(
                fields=[
                    'id',
                    'get_provider_registry',
                    'get_provider_registry_info',
                    'status',
                ]
            ),
            schema.FormSet(
                fields=[
                    'endpoint',
                    'amount',
                ],
                col_span=6,
            ),
            schema.FormSet(
                fields=[
                    'created_at',
                ],
                col_span=6,
            ),
            schema.FormSet(
                title='Main 2',
                description='form description form description form description form description',
                fields=[
                    schema.FormField('other_field', col_span=6),
                    schema.FormField('description', col_span=6),
                    'gateway_settings',
                    'whitelist_ips',
                ]
            ),
            'disputes',
        ]
    )

    @schema.function_field(label=_('registry_checked'), type=schema.BooleanField)
    async def get_provider_registry(self, record, user, **kwargs):
        return True

    @schema.function_field(
        label=_('registry_info_checked'),
        help_text=_('registry_info_checked'),
        type=schema.BooleanField,
    )
    async def get_provider_registry_info(self, record, user, **kwargs):
        return False

    disputes = schema.InlineField(
        label=_('disputes'),
        help_text=_('disputes_help_text'),
        table_schema=schema.FieldsSchema(
            id=schema.IntegerField(label='ID', read_only=True),
            reason=schema.StringField(label=_('Name')),
            manager=schema.RelatedField(label=_('Manager')),
            errors=schema.JSONField(help_text='This is errors', read_only=True),
            created_at=schema.DateTimeField(label=_('created_at'), read_only=True),
        )
    )


class CreatePaymentSchema(schema.FieldsSchema):
    amount = schema.IntegerField(label=_('amount'))
    is_throw_error = schema.BooleanField(label=_('is_throw_error'))

    async def validate_is_throw_error(self, value):
        if value:
            raise FieldError(_('throw_error'))
        return value


class LogsAdmin(schema.CategoryTable):
    has_update = False
    has_create = False
    slug = 'logs'

    table_schema = schema.FieldsSchema(
        log=schema.StringField(label=_('Log')),
    )

    # pylint: disable=too-many-arguments
    async def get_list(
            self,
            list_data: schema.ListData,
            user: auth.UserABC,
            language_context: LanguageContext,
            debug: bool,
            parent_category=None,
            parent_pk=None,
    ) -> schema.TableListResult:
        await asyncio.sleep(0.2)

        data = []
        total_count = 5039

        fake = Faker()
        for i in range(0, list_data.limit):
            pk = total_count - ((list_data.page - 1) * list_data.limit + i)
            if pk < 0:
                continue

            line_data = {'log': fake.sentence(nb_words=20)}
            line = await self.table_schema.serialize(line_data, extra={'user': user, 'record': line_data})
            data.append(line)

        return schema.TableListResult(data=data, total_count=total_count)


class PaymentsAdmin(schema.CategoryTable):
    has_update = False
    has_create = False

    slug = 'payments'
    title = _('payments')
    description = _('payments_description')
    icon = 'mdi-credit-card-outline'

    search_enabled = True
    search_help = _('payments_search_fields')

    table_filters = PaymentFiltersSchema()
    table_schema = PaymentFieldsSchema()
    pk_name = 'id'
    ordering_fields = [
        'id',
    ]

    subcategories = [
        LogsAdmin(),
    ]

    @admin_action(
        title=_('create_payment'),
        description=_('create_payment_description'),
        icon='mdi-cash-plus',
        form_schema=CreatePaymentSchema(),
        allow_empty_selection=True,
    )
    async def create_payment(self, action_data: ActionData, **kwargs):
        await asyncio.sleep(1)
        fake = Faker()
        msg = _('payment_create_result') % {
            'gateway_id': str(uuid.uuid4()),
            'desctiption': fake.sentence(nb_words=100),
            'redirect_url': 'https://www.google.com',
        }
        return ActionResult(persistent_message=msg)

    @admin_action(
        title=_('delete'),
        confirmation_text=_('delete_confirmation_text'),
        base_color='red-lighten-1',
        icon='mdi-delete-outline',
        variant='outlined',
    )
    async def delete(self, action_data: ActionData, **kwargs):
        await asyncio.sleep(1)

    @admin_action(title=_('action_with_exception'), allow_empty_selection=True, icon='mdi-alert-circle-outline')
    async def action_with_exception(self, action_data: ActionData, **kwargs):
        await asyncio.sleep(0.5)
        # Try for traceback
        try:
            raise RuntimeError('test')
        except Exception as e:
            raise Exception(
                _('exception_example') % {
                    'traceback': ''.join(traceback.format_stack()),
                }
            ) from e

    @admin_action(
        title='Change amount',
        base_color='orange-darken-1',
        icon='mdi-pencil-circle-outline',
        form_schema=schema.FieldsSchema(
            amount=schema.IntegerField(label=_('amount'), required=True),
        ),
    )
    async def change_amount(self, action_data: ActionData, **kwargs):
        await asyncio.sleep(0.2)
        return ActionResult(f'Amount changed to {action_data.form_data["amount"]}')

    @admin_action(
        title='Update status',
        base_color='grey-darken-1',
        icon='mdi-sync-circle',
        form_schema=schema.FieldsSchema(
            status=schema.ChoiceField(label='Status', required=True, choices=TerminalStatuses),
        ),
    )
    async def update_status(self, action_data: ActionData, **kwargs):
        await asyncio.sleep(0.2)
        return ActionResult(f'Status updated to {action_data.form_data["status"]}')

    def _get_data(self, pk):
        fake = Faker()
        Faker.seed(pk)

        return {
            'id': pk,
            'amount': 10 * fake.pyint(min_value=0, max_value=100),
            'endpoint': fake.word(),
            'status': fake.random_element(elements=list(TerminalStatuses)).value,
            'whitelist_ips': ['localhost', '0.0.0.0'],
            'description': fake.sentence(nb_words=50),
            'other_field': fake.word(),
            'image': f'https://picsum.photos/id/{5039-pk+1}/200/300',
            'gateway_settings': ['first', 'second'],
            'created_at': datetime.datetime(2025, 6, 16, 9, 45, 29) - datetime.timedelta(hours=pk, minutes=pk),
            'disputes': [
                {
                    'id': 1,
                    'reason': 'Reason title',
                    'manager': {'key': 1, 'title': 'Manager name'},
                    'errors': [
                        'first',
                        'second',
                        {
                            'code': "provider_error",
                            'description': "Error from the provider. Please contact support.",
                        },
                    ],
                    'created_at': datetime.datetime(2025, 6, 16, 9, 45, 29) - datetime.timedelta(hours=pk, minutes=pk),
                },
                {
                    'id': 2,
                    'reason': 'Reason title 2',
                    'manager': {'key': 1, 'title': 'Manager second'},
                    'created_at': datetime.datetime(2025, 6, 16, 9, 45, 29) - datetime.timedelta(hours=pk, minutes=pk),
                }
            ],
        }

    # pylint: disable=too-many-arguments
    async def get_list(
            self,
            list_data: schema.ListData,
            user: auth.UserABC,
            language_context: LanguageContext,
            debug: bool,
            parent_category=None,
            parent_pk=None,
    ) -> schema.TableListResult:
        await asyncio.sleep(0.2)

        data = []
        total_count = 5039

        for i in range(0, list_data.limit):
            pk = total_count - ((list_data.page - 1) * list_data.limit + i)
            if pk < 0:
                continue

            line_data = self._get_data(pk)
            line = await self.table_schema.serialize(line_data, extra={'user': user, 'record': line_data})
            data.append(line)

        return schema.TableListResult(data=data, total_count=total_count)

    async def retrieve(
            self,
            pk: Any,
            user: auth.UserABC,
            language_context: LanguageContext,
            debug: bool,
            parent_category=None,
            parent_pk=None,
    ) -> schema.RetrieveResult:
        line_data = self._get_data(int(pk))
        line = await self.table_schema.serialize(line_data, extra={'user': user, 'record': line_data})
        return schema.RetrieveResult(data=line)

    async def update(
            self,
            pk: Any,
            data: dict,
            user: auth.UserABC,
            language_context: LanguageContext,
            debug: bool,
            parent_category=None,
            parent_pk=None,
    ) -> schema.UpdateResult:
        logger.info('Updated pk=%s data=%s', pk, data)
        await asyncio.sleep(0.5)
        return schema.UpdateResult(pk=0)

    async def create(
            self,
            data: dict,
            user: auth.UserABC,
            language_context: LanguageContext,
            debug: bool,
            parent_category=None,
            parent_pk=None,
    ) -> schema.CreateResult:
        logger.info('Create data=%s', data)
        return schema.CreateResult(pk=0)
