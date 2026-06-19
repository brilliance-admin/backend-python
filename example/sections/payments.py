import asyncio
import datetime
import uuid
from typing import Any

from faker import Faker

from brilliance_admin import auth, schema
from brilliance_admin.exceptions import FieldError
from brilliance_admin.schema.table.admin_action import ActionData, ActionResult, admin_action
from brilliance_admin.translations import LanguageContext
from brilliance_admin.translations import TranslateText as _
from brilliance_admin.utils import get_logger

logger = get_logger()


class PaymentFiltersSchema(schema.FieldsSchema):
    id = schema.IntegerField(label='ID')
    created_at = schema.DateTimeField(label=_('created_at'), range=True)

    fields = [
        'id',
        'created_at',
    ]


class PaymentFieldsSchema(schema.FieldsSchema):
    list_display = [
        'id',
        'amount',
        'endpoint',
        'created_at',
        'get_provider_registry',
        'get_provider_registry_info',
    ]

    id = schema.IntegerField(label='ID', read_only=True)
    amount = schema.IntegerField(label=_('amount'), read_only=True)
    endpoint = schema.StringField(label=_('endpoint'))
    description = schema.StringField(label=_('description'))
    other_field = schema.StringField(read_only=True)
    whitelist_ips = schema.ArrayField(label=_('whitelist_ips'))
    # image = schema.ImageField(label=_('image'))
    created_at = schema.DateTimeField(label=_('created_at'), read_only=True)

    @schema.function_field(label=_('registry_checked'), type=schema.BooleanField)
    async def get_provider_registry(self, record, user, **kwargs):
        return True

    @schema.function_field(label=_('registry_info_checked'), type=schema.BooleanField)
    async def get_provider_registry_info(self, record, user, **kwargs):
        return False

    disputes = schema.InlineField(
        label=_('disputes'),
        help_text=_('disputes_help_text'),
        table_schema=schema.FieldsSchema(
            id=schema.IntegerField(label='ID', read_only=True),
            reason=schema.StringField(label=_('Name')),
            manager=schema.RelatedField(label=_('Manager')),
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

        for i in range(0, list_data.limit):
            pk = total_count - ((list_data.page - 1) * list_data.limit + i)
            if pk < 0:
                continue

            line_data = {'log': 'test'}
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
        LogsAdmin()
    ]

    @admin_action(
        title=_('create_payment'),
        description=_('create_payment_description'),
        form_schema=CreatePaymentSchema(),
        allow_empty_selection=True,
    )
    async def create_payment(self, action_data: ActionData):
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
        base_color='red-lighten-2',
        variant='outlined',
    )
    async def delete(self, action_data: ActionData):
        await asyncio.sleep(1)
        return ActionResult(_('deleted_successfully'))

    @admin_action(title=_('action_with_exception'), allow_empty_selection=True)
    async def action_with_exception(self, action_data: ActionData):
        await asyncio.sleep(0.5)
        raise Exception(_('exception_example'))

    def _get_data(self, pk):
        fake = Faker()
        Faker.seed(pk)

        return {
            'id': pk,
            'amount': 10 * fake.pyint(min_value=0, max_value=100),
            'endpoint': fake.word(),
            'whitelist_ips': ['localhost', '0.0.0.0'],
            'description': fake.sentence(nb_words=50),
            'other_field': fake.word(),
            'image': f'https://picsum.photos/id/{5039-pk+1}/200/300',
            'created_at': datetime.datetime(2025, 6, 16, 9, 45, 29) - datetime.timedelta(hours=pk, minutes=pk),
            'disputes': [
                {
                    'id': 1,
                    'reason': 'Reason title',
                    'manager': {'key': 1, 'title': 'Manager name'},
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
