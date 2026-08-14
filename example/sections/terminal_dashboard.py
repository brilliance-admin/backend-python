from brilliance_admin import schema
from brilliance_admin.schema.dashboard.category_dashboard import (
    ChartData,
    DashboardContainer,
    DashboardData,
)


CHART_OPTIONS = {
    'responsive': True,
    'maintainAspectRatio': False,
    'plugins': {
        'legend': {
            'position': 'bottom',
            'labels': {
                'font': {'size': 12},
                'usePointStyle': True,
                'pointStyle': 'circle',
                'padding': 14,
            },
        },
        'tooltip': {
            'mode': 'index',
            'intersect': False,
            'cornerRadius': 8,
            'padding': 12,
        },
    },
    'scales': {
        'x': {
            'grid': {'display': False},
            'ticks': {'font': {'size': 11}},
        },
        'y': {
            'ticks': {'font': {'size': 11}},
        },
    },
    'layout': {'padding': 12},
}


class TerminalDashboard(schema.CategoryDashboard):
    slug = 'terminal-dashboard'
    title = 'Dashboard'
    icon = 'mdi-chart-box-outline'

    async def get_data(
            self,
            data: DashboardData,
            user,
            parent_category=None,
            parent_pk=None,
    ) -> DashboardContainer:
        labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        payment_count = [142, 168, 151, 190, 214, 236, 221]
        payout_count = [91, 104, 98, 121, 133, 149, 138]
        payment_amount = [18200, 21750, 19940, 24600, 28100, 30720, 29480]
        payout_amount = [10950, 12640, 11880, 14520, 16100, 18450, 17210]
        conversion = [88.4, 91.2, 84.7, 93.6, 79.5, 86.8, 95.1]
        errors = [4, 5, 3, 6, 7, 5, 4]
        error_rate = [round(100 - value, 2) for value in conversion]

        def count_amount_options(title):
            return {
                'responsive': True,
                'maintainAspectRatio': False,
                'plugins': {
                    **CHART_OPTIONS['plugins'],
                    'title': {
                        'display': True,
                        'text': title,
                        'font': {'size': 16, 'weight': 'bold'},
                    },
                },
                'scales': {
                    'x': CHART_OPTIONS['scales']['x'],
                    'count': {
                        'position': 'left',
                        'title': {'display': True, 'text': 'Count'},
                        'ticks': {'font': {'size': 11}},
                    },
                    'amount': {
                        'position': 'right',
                        'title': {'display': True, 'text': 'Amount'},
                        'grid': {'drawOnChartArea': False},
                        'ticks': {'font': {'size': 11}},
                    },
                },
            }

        payments_chart = ChartData(
            type='bar',
            height=70,
            data={
                'labels': labels,
                'datasets': [
                    {
                        'label': 'Payment count',
                        'data': payment_count,
                        'backgroundColor': 'primary',
                        'borderRadius': 4,
                        'yAxisID': 'count',
                    },
                    {
                        'label': 'Payment amount',
                        'type': 'line',
                        'data': payment_amount,
                        'borderColor': 'info',
                        'pointBorderColor': 'info',
                        'pointBorderWidth': 2,
                        'pointRadius': 4,
                        'tension': 0.35,
                        'yAxisID': 'amount',
                    },
                ],
            },
            options=count_amount_options('Payments: count and amount'),
        )

        payouts_chart = ChartData(
            type='bar',
            height=70,
            data={
                'labels': labels,
                'datasets': [
                    {
                        'label': 'Payout count',
                        'data': payout_count,
                        'backgroundColor': 'success',
                        'borderRadius': 4,
                        'yAxisID': 'count',
                    },
                    {
                        'label': 'Payout amount',
                        'type': 'line',
                        'data': payout_amount,
                        'borderColor': 'warning',
                        'pointBorderColor': 'warning',
                        'pointBorderWidth': 2,
                        'pointRadius': 4,
                        'tension': 0.35,
                        'yAxisID': 'amount',
                    },
                ],
            },
            options=count_amount_options('Payouts: count and amount'),
        )

        conversion_errors_chart = ChartData(
            type='bar',
            height=70,
            data={
                'labels': labels,
                'datasets': [
                    {
                        'label': 'Errors',
                        'data': errors,
                        'backgroundColor': 'error',
                        'borderRadius': 4,
                        'yAxisID': 'errors',
                    },
                    {
                        'label': 'Conversion',
                        'type': 'line',
                        'data': conversion,
                        'borderColor': 'primary',
                        'pointBorderColor': 'primary',
                        'pointBorderWidth': 2,
                        'pointRadius': 4,
                        'tension': 0.35,
                        'yAxisID': 'conversion',
                    },
                ],
            },
            options={
                'responsive': True,
                'maintainAspectRatio': False,
                'plugins': {
                    **CHART_OPTIONS['plugins'],
                    'title': {
                        'display': True,
                        'text': 'Conversion and errors',
                        'font': {'size': 16, 'weight': 'bold'},
                    },
                },
                'scales': {
                    'x': CHART_OPTIONS['scales']['x'],
                    'errors': {
                        'position': 'left',
                        'title': {'display': True, 'text': 'Errors'},
                        'ticks': {'font': {'size': 11}},
                    },
                    'conversion': {
                        'position': 'right',
                        'title': {'display': True, 'text': 'Conversion, %'},
                        'grid': {'drawOnChartArea': False},
                        'ticks': {'font': {'size': 11}},
                    },
                },
            },
        )

        success_errors_share_chart = ChartData(
            type='bar',
            height=70,
            data={
                'labels': labels,
                'datasets': [
                    {
                        'label': 'Success',
                        'data': conversion,
                        'backgroundColor': 'success',
                        'borderRadius': 4,
                        'stack': 'status',
                    },
                    {
                        'label': 'Errors',
                        'data': error_rate,
                        'backgroundColor': 'error',
                        'borderRadius': 4,
                        'stack': 'status',
                    },
                ],
            },
            options={
                **CHART_OPTIONS,
                'plugins': {
                    **CHART_OPTIONS['plugins'],
                    'title': {
                        'display': True,
                        'text': 'Success and errors share',
                        'font': {'size': 16, 'weight': 'bold'},
                    },
                },
                'scales': {
                    'x': {
                        **CHART_OPTIONS['scales']['x'],
                        'stacked': True,
                    },
                    'y': {
                        'stacked': True,
                        'min': 0,
                        'max': 100,
                        'title': {'display': True, 'text': 'Share, %'},
                        'ticks': {'font': {'size': 11}},
                    },
                },
            },
        )

        return DashboardContainer(
            components=[
                DashboardContainer(cols=12, md=6, components=[payments_chart]),
                DashboardContainer(cols=12, md=6, components=[payouts_chart]),
                DashboardContainer(cols=12, components=[conversion_errors_chart]),
                DashboardContainer(cols=12, components=[success_errors_share_chart]),
            ],
        )
