import asyncio
import datetime
import uuid
from typing import Any

from faker import Faker

from brilliance_admin import auth, schema
from brilliance_admin.exceptions import FieldError
from brilliance_admin.schema.table.admin_action import ActionData, ActionMessage, ActionResult, admin_action
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


STATUS_COLORS = {
    'process': 'grey-lighten-1',
    'success': 'green-darken-1',
    'error': 'red-lighten-2',
}


class PaymentFieldsSchema(schema.FieldsSchema):
    id = schema.IntegerField(label='ID', read_only=True)
    amount = schema.IntegerField(label=_('amount'))
    endpoint = schema.StringField(label=_('endpoint'))
    description = schema.StringField(label=_('description'))
    other_field = schema.StringField(read_only=True)
    whitelist_ips = schema.ArrayField(label=_('whitelist_ips'))
    status = schema.ChoiceField(
        label=_('status'),
        tag_colors=STATUS_COLORS,
        choices=list({'value': k, 'title': k.capitalize()} for k in STATUS_COLORS),
    )
    # image = schema.ImageField(label=_('image'))
    created_at = schema.DateTimeField(label=_('created_at'), read_only=True)

    list_display = [
        'id',
        'amount',
        'endpoint',
        'status',
        'description',
        'created_at',
        'get_provider_registry',
        'get_provider_registry_info',
    ]

    @schema.function_field(label=_('registry_checked'), type=schema.BooleanField)
    async def get_provider_registry(self, record, user, **kwargs):
        return True

    @schema.function_field(label=_('registry_info_checked'), type=schema.BooleanField)
    async def get_provider_registry_info(self, record, user, **kwargs):
        return False


class CreatePaymentSchema(schema.FieldsSchema):
    amount = schema.IntegerField(label=_('amount'))
    is_throw_error = schema.BooleanField(label=_('is_throw_error'))

    async def validate_is_throw_error(self, value):
        if value:
            raise FieldError(_('throw_error'))
        return value


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
    table_schema = PaymentFieldsSchema(readonly_fields=['amount'])
    pk_name = 'id'
    ordering_fields = [
        'id',
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
        return ActionResult(message=ActionMessage(_('deleted_successfully')))

    @admin_action(title=_('action_with_exception'), allow_empty_selection=True)
    async def action_with_exception(self, action_data: ActionData):
        await asyncio.sleep(0.5)
        raise Exception(_('exception_example'))

    def _get_data(self, pk):
        fake = Faker()
        Faker.seed(pk)

        statuses = list(STATUS_COLORS.keys())
        status = statuses[fake.pyint(min_value=0, max_value=len(statuses) - 1)]
        return {
            'id': pk,
            'amount': 10 * fake.pyint(min_value=0, max_value=100),
            'status': status,
            'endpoint': fake.word(),
            'whitelist_ips': ['localhost', '0.0.0.0'],
            'description': fake.sentence(nb_words=5),
            'other_field': fake.word(),
            'image': f'https://picsum.photos/id/{5039-pk+1}/200/300',
            'created_at': datetime.datetime(2025, 6, 16, 9, 45, 29) - datetime.timedelta(hours=pk, minutes=pk),
        }

    # pylint: disable=too-many-arguments
    async def get_list(
        self,
        list_data: schema.ListData,
        user: auth.UserABC,
        language_context: LanguageContext,
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
    ) -> schema.UpdateResult:
        logger.info('Updated pk=%s data=%s', pk, data)
        await asyncio.sleep(0.5)
        return schema.UpdateResult(pk=0)

    async def create(
            self,
            data: dict, user:
            auth.UserABC,
            language_context: LanguageContext,
    ) -> schema.CreateResult:
        logger.info('Create data=%s', data)
        return schema.CreateResult(pk=0)
