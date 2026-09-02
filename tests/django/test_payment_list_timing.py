import time

import pytest
from django.db import connection

from brilliance_admin import schema
from brilliance_admin.auth import UserABC
from brilliance_admin.integrations.django import DjangoAdmin, DjangoFieldsSchema
from example.sections.models_payment import (
    PaymentBenchmark, PaymentBenchmarkFactory, PaymentBuyerFactory, PaymentCurrency, PaymentCurrencyFactory,
    PaymentEndpoint, PaymentEndpointFactory, PaymentMeansOfPayment, PaymentMeansOfPaymentFactory,
    PaymentMeansOfPaymentType, PaymentMeansOfPaymentTypeFactory, PaymentProvider, PaymentProviderFactory)


class PaymentBenchmarkFieldsSchema(DjangoFieldsSchema):
    model = PaymentBenchmark


class PaymentBenchmarkAdmin(DjangoAdmin):
    model = PaymentBenchmark
    table_schema = PaymentBenchmarkFieldsSchema()
    list_display = [
        'id',
        'status',
        'amount',
        'currency',
        'endpoint',
        'provider',
        'integration_type',
        'old_amount',
        'buyer',
        'created_at',
        'updated_at',
        'complete_date',
        'cancel_at',
        'means_of_payment',
        'means_of_payment_type',
        'remote_id',
        'test_mode',
    ]

    def get_queryset(self, *args, **kwargs):
        return self.model.objects.filter(endpoint__is_active=True).select_related(
            'currency',
            'endpoint',
            'provider',
            'buyer',
            'means_of_payment',
            'means_of_payment__mop_type',
            'means_of_payment_type',
        )


PAYMENT_MODELS = [
    PaymentCurrency,
    PaymentProvider,
    PaymentEndpoint,
    PaymentBuyerFactory._meta.model,
    PaymentMeansOfPaymentType,
    PaymentMeansOfPayment,
    PaymentBenchmark,
]


@pytest.fixture
def payment_benchmark_schema():
    with connection.schema_editor() as schema_editor:
        for model in PAYMENT_MODELS:
            schema_editor.create_model(model)

    yield

    with connection.schema_editor() as schema_editor:
        for model in reversed(PAYMENT_MODELS):
            schema_editor.delete_model(model)


@pytest.mark.asyncio
@pytest.mark.benchmark
async def test_payment_list_timing(payment_benchmark_schema, language_context):
    yappi = pytest.importorskip('yappi')

    currency = await PaymentCurrencyFactory()
    provider = await PaymentProviderFactory()
    endpoint = await PaymentEndpointFactory(currency=currency)
    means_of_payment_type = await PaymentMeansOfPaymentTypeFactory()

    for _ in range(50):
        buyer = await PaymentBuyerFactory(endpoint=endpoint)
        means_of_payment = await PaymentMeansOfPaymentFactory(mop_type=means_of_payment_type)
        await PaymentBenchmarkFactory(
            endpoint=endpoint,
            currency=currency,
            provider=provider,
            buyer=buyer,
            means_of_payment=means_of_payment,
            means_of_payment_type=means_of_payment_type,
        )

    category = PaymentBenchmarkAdmin()
    category.run_debug_startup_checks()

    yappi.clear_stats()
    yappi.set_clock_type('wall')
    yappi.start()
    started_at = time.perf_counter()
    result = await category.get_list(
        list_data=schema.ListData(limit=50),
        user=UserABC(username='benchmark'),
        language_context=language_context,
        debug=True,
    )
    total_ms = round((time.perf_counter() - started_at) * 1000, 2)
    yappi.stop()

    print(
        'Payment Django list 50 records: '
        f'total={total_ms}ms, '
        f'serialize={result.debug_info.serialize_ms}ms, '
        f'debug_queries={result.debug_info.db_query_count}'
    )
    print_yappi_stats(yappi.get_func_stats())

    assert result.total_count == 50
    assert len(result.data) == 50


def print_yappi_stats(stats):
    stats.sort('ttot', 'desc')
    targets = (
        'brilliance_admin',
        'asgiref',
        'related_descriptors',
        'models_payment',
    )

    print('Yappi wall-clock top:')
    printed = 0
    for stat in stats:
        if not any(target in stat.full_name for target in targets):
            continue
        print(
            f'{stat.ttot * 1000:8.2f}ms '
            f'{stat.tsub * 1000:8.2f}ms '
            f'{stat.ncall:5} '
            f'{stat.full_name}'
        )
        printed += 1
        if printed >= 30:
            break
