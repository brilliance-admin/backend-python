import factory

from django.db import models
from example.utils import DjangoFactoryBase


class PaymentCurrency(models.Model):
    title = models.CharField(max_length=255)
    num_code = models.IntegerField(null=True, unique=True, blank=True)
    char_code = models.CharField(max_length=10, unique=True)
    depth = models.IntegerField(default=2)

    class Meta:
        db_table = 'payment_benchmark_currency'

    def __str__(self):
        return f'{self.num_code or self.id} [{self.char_code} {self.title}]'


class PaymentProvider(models.Model):
    name = models.CharField(max_length=255)
    payment_module_id = models.IntegerField(null=True, blank=True)
    payout_module_id = models.IntegerField(null=True, blank=True)
    registry_module = models.IntegerField(null=True, blank=True)
    requests_timeout = models.IntegerField(default=30)

    class Meta:
        db_table = 'payment_benchmark_provider'

    def __str__(self):
        return self.name


class PaymentEndpoint(models.Model):
    key = models.CharField(max_length=64, unique=True)
    payment_form_id = models.IntegerField(null=True, blank=True)
    means_of_payment_type_id = models.IntegerField(null=True, blank=True)
    use_capcha = models.BooleanField(default=False)
    merchant_id = models.IntegerField()
    currency = models.ForeignKey(PaymentCurrency, models.PROTECT, null=True, blank=True)
    title = models.CharField(max_length=255)
    status = models.IntegerField(default=1)
    site = models.CharField(max_length=255, null=True, blank=True)
    secret_key = models.CharField(max_length=255, default='')
    success_url = models.URLField(null=True, blank=True)
    fail_url = models.URLField(null=True, blank=True)
    test_mode = models.BooleanField(default=True)
    callback_check_url = models.URLField(null=True, blank=True)
    callback_notify_url = models.URLField(null=True, blank=True)
    payout_callback_notify_url = models.URLField(null=True, blank=True)
    callback_additional_fields = models.JSONField(null=True, blank=True, default=dict)
    payment_registry_enabled = models.BooleanField(default=False)
    payout_registry_enabled = models.BooleanField(default=False)
    allow_h2h_api = models.BooleanField(default=False)
    integration_type = models.CharField(max_length=10, default='h2h')
    payment_card_token_available = models.BooleanField(default=False)
    payout_card_token_available = models.BooleanField(default=False)
    proxy_id = models.IntegerField(null=True, blank=True)
    tz = models.CharField(max_length=255, default='UTC')
    language_id = models.IntegerField(null=True, blank=True)
    rolling_is_visible = models.BooleanField(default=False)
    direct_merchant_redirect = models.BooleanField(default=False)
    redirect_in_process_status = models.BooleanField(default=False)
    ips = models.BooleanField(default=False)
    domain_template_url = models.URLField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    platform = models.CharField(max_length=255, null=True, blank=True)
    callback_signature_without_spaces = models.BooleanField(default=False)
    use_db_bank_data = models.BooleanField(default=False)
    balances_name = models.CharField(max_length=255, null=True, blank=True)
    payment_timeout_hours = models.BigIntegerField(default=24)
    payment_waiting_hours = models.BigIntegerField(default=1)

    class Meta:
        db_table = 'payment_benchmark_endpoint'

    def __str__(self):
        return f'{self.title} (Merchant id: {self.merchant_id})'


class PaymentBuyer(models.Model):
    endpoint = models.ForeignKey(PaymentEndpoint, models.PROTECT)
    remote_id = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'payment_benchmark_buyer'

    def __str__(self):
        return f'Endpoint id: {self.endpoint_id} - {self.remote_id}'


class PaymentMeansOfPaymentType(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=255, unique=True)
    logo = models.ImageField(upload_to='mop_logo/', blank=True, null=True)
    is_card = models.BooleanField(default=False)

    class Meta:
        db_table = 'payment_benchmark_means_of_payment_type'

    def __str__(self):
        return f'{self.name} ({self.code})'


class PaymentMeansOfPayment(models.Model):
    mop_type = models.ForeignKey(PaymentMeansOfPaymentType, models.PROTECT)
    bank_card_id = models.IntegerField(null=True, blank=True)
    number = models.CharField(max_length=50, null=True, blank=True)
    detail = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = 'payment_benchmark_means_of_payment'

    def __str__(self):
        bank_card_str = f'Bank card id: {self.bank_card_id}'
        return f'{self.mop_type} {bank_card_str if self.bank_card_id else self.number}'


class PaymentBenchmark(models.Model):
    endpoint = models.ForeignKey(PaymentEndpoint, models.PROTECT)
    amount = models.BigIntegerField(default=0)
    old_amount = models.BigIntegerField(null=True, blank=True)
    currency = models.ForeignKey(PaymentCurrency, models.PROTECT, null=True)
    means_of_payment_type = models.ForeignKey(PaymentMeansOfPaymentType, models.PROTECT, null=True, blank=True)
    status = models.CharField(max_length=30, default='create', db_index=True)
    remote_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    means_of_payment = models.ForeignKey(PaymentMeansOfPayment, models.CASCADE, null=True)
    test_mode = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    complete_date = models.DateTimeField(null=True, blank=True, db_index=True)
    provider = models.ForeignKey(PaymentProvider, models.PROTECT, null=True, blank=True)
    integration_type = models.CharField(max_length=10, default='h2h')
    cancel_at = models.DateTimeField(null=True, blank=True)
    buyer = models.ForeignKey(PaymentBuyer, models.PROTECT, null=True)

    class Meta:
        db_table = 'payment_benchmark_payment'
        ordering = ('-id',)
        indexes = [models.Index(fields=['provider', 'endpoint'])]

    def __str__(self):
        return str(self.id)


class PaymentCurrencyFactory(DjangoFactoryBase):
    class Meta:
        model = PaymentCurrency

    title = 'US Dollar'
    num_code = 840
    char_code = factory.Sequence(lambda n: f'U{n:02d}')


class PaymentProviderFactory(DjangoFactoryBase):
    class Meta:
        model = PaymentProvider

    name = factory.Sequence(lambda n: f'Provider {n}')


class PaymentEndpointFactory(DjangoFactoryBase):
    class Meta:
        model = PaymentEndpoint

    key = factory.Sequence(lambda n: f'endpoint-key-{n}')
    merchant_id = 100
    currency = factory.SubFactory(PaymentCurrencyFactory)
    title = factory.Sequence(lambda n: f'Endpoint {n}')


class PaymentBuyerFactory(DjangoFactoryBase):
    class Meta:
        model = PaymentBuyer

    endpoint = factory.SubFactory(PaymentEndpointFactory)
    remote_id = factory.Sequence(lambda n: f'buyer-{n}')


class PaymentMeansOfPaymentTypeFactory(DjangoFactoryBase):
    class Meta:
        model = PaymentMeansOfPaymentType

    name = 'Card'
    code = factory.Sequence(lambda n: f'card-{n}')


class PaymentMeansOfPaymentFactory(DjangoFactoryBase):
    class Meta:
        model = PaymentMeansOfPayment

    mop_type = factory.SubFactory(PaymentMeansOfPaymentTypeFactory)
    number = factory.Sequence(lambda n: f'411111******{n:04d}')


class PaymentBenchmarkFactory(DjangoFactoryBase):
    class Meta:
        model = PaymentBenchmark

    endpoint = factory.SubFactory(PaymentEndpointFactory)
    amount = factory.Sequence(lambda n: 10000 + n)
    old_amount = factory.Sequence(lambda n: 9000 + n)
    currency = factory.SubFactory(PaymentCurrencyFactory)
    means_of_payment_type = factory.SubFactory(PaymentMeansOfPaymentTypeFactory)
    status = 'success'
    remote_id = factory.Sequence(lambda n: f'remote-{n}')
    means_of_payment = factory.SubFactory(PaymentMeansOfPaymentFactory)
    provider = factory.SubFactory(PaymentProviderFactory)
    buyer = factory.SubFactory(PaymentBuyerFactory)
