from brilliance_admin import schema
from brilliance_admin.schema.dashboard.category_dashboard import (
    ChartData,
    DashboardContainer,
    DashboardData,
    PeriodGraph,
    SmallGraph,
    Subcard,
)
from brilliance_admin.translations import TranslateText as _

CHART_OPTIONS_BASE = {
    'responsive': True,
    'maintainAspectRatio': False,
    'plugins': {
        'legend': {
            'position': 'top',
            'labels': {
                'font': {'size': 12},
                'usePointStyle': True,
                'pointStyle': 'circle',
                'padding': 16,
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
    'layout': {'padding': 16},
}


class DasbhoardFiltersSchema(schema.FieldsSchema):
    id = schema.IntegerField(label='ID')
    created_at = schema.DateTimeField(label=_('created_at'))
    _fields = [
        'id',
        'created_at',
    ]


class DasbhoardExample(schema.CategoryDashboard):
    slug = 'dashboard'
    title = _('dashboard.title')
    icon = 'mdi-chart-bar-stacked'
    table_filters = DasbhoardFiltersSchema()

    async def get_data(
            self,
            data: DashboardData,
            user,
            parent_category=None,
            parent_pk=None,
    ) -> DashboardContainer:
        chart_1 = ChartData(
            type='line',
            data={
                'labels': ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul"],
                'datasets': [
                    {
                        'label': "Dataset #1",
                        'borderColor': 'primary',
                        'fill': True,
                        'tension': 0.4,
                        'borderWidth': 2,
                        'pointRadius': 4,
                        'pointBorderColor': 'primary',
                        'pointBorderWidth': 2,
                        'pointHoverRadius': 6,
                        'data': [65, 59, 20, 81, 56, 55, 40],
                        'gradient': {
                            'backgroundColor': {
                                'axis': 'y',
                                'colors': {
                                    0: 'primary-zero',
                                    100: 'primary-fill',
                                },
                            },
                        },
                    },
                    {
                        'label': "Dataset #2",
                        'borderColor': 'secondary',
                        'fill': True,
                        'tension': 0.4,
                        'borderWidth': 2,
                        'pointRadius': 4,
                        'pointBorderColor': 'secondary',
                        'pointBorderWidth': 2,
                        'pointHoverRadius': 6,
                        'data': [30, 35, 29, 15, 3, 10, 22],
                        'gradient': {
                            'backgroundColor': {
                                'axis': 'y',
                                'colors': {
                                    0: 'secondary-zero',
                                    100: 'secondary-fill',
                                },
                            },
                        },
                    },
                ],
            },
            options={
                **CHART_OPTIONS_BASE,
                'plugins': {
                    **CHART_OPTIONS_BASE['plugins'],
                    'title': {
                        'display': True,
                        'text': 'Chart.js Line Chart',
                        'font': {'size': 16, 'weight': 'bold'},
                        'padding': {'bottom': 16},
                    },
                },
            },
        )
        chart_2 = ChartData(
            type='line',
            data={
                'labels': [
                    "Jun 2016",
                    "Jul 2016",
                    "Aug 2016",
                    "Sep 2016",
                    "Oct 2016",
                    "Nov 2016",
                    "Dec 2016",
                    "Jan 2017",
                    "Feb 2017",
                    "Mar 2017",
                    "Apr 2017",
                    "May 2017",
                ],
                'datasets': [
                    {
                        'label': "Rainfall",
                        'borderColor': '#6366f1',
                        'backgroundColor': 'rgba(99, 102, 241, 0.08)',
                        'fill': True,
                        'tension': 0.4,
                        'borderWidth': 2,
                        'pointRadius': 4,
                        'pointBackgroundColor': '#ffffff',
                        'pointBorderColor': '#6366f1',
                        'pointBorderWidth': 2,
                        'pointHoverRadius': 6,
                        'data': [26.4, 39.8, 66.8, 66.4, 40.6, 55.2, 77.4, 69.8, 57.8, 76, 110.8, 142.6],
                    },
                    {
                        'label': "Snowfall",
                        'borderColor': 'info',
                        'fill': True,
                        'tension': 0.4,
                        'borderWidth': 2,
                        'pointRadius': 4,
                        'pointBorderColor': 'info',
                        'pointBorderWidth': 2,
                        'pointHoverRadius': 6,
                        'data': [51.0, 39.4, 26.2, 6.8, 0.0, 0.0, 0.0, 0.0, 0.0, 1.2, 12.4, 29.6],
                        'gradient': {
                            'backgroundColor': {
                                'axis': 'y',
                                'colors': {
                                    0: 'info-zero',
                                    60: 'info-fill',
                                },
                            },
                        },
                    },
                    {
                        'label': "Temperature °C",
                        'borderColor': 'error',
                        'fill': True,
                        'tension': 0.4,
                        'borderWidth': 2,
                        'pointRadius': 4,
                        'pointBorderColor': 'error',
                        'pointBorderWidth': 2,
                        'pointHoverRadius': 6,
                        'data': [19.2, 22.8, 18.4, 11.2, 4.8, -1.6, -6.8, -5.2, 0.4, 8.6, 15.0, 18.8],
                        'yAxisID': 'y1',
                        'gradient': {
                            'backgroundColor': {
                                'axis': 'y',
                                'colors': {
                                    -10: 'error-zero',
                                    25: 'error-fill',
                                },
                            },
                        },
                    },
                ],
            },
            options={
                **CHART_OPTIONS_BASE,
                'plugins': {
                    **CHART_OPTIONS_BASE['plugins'],
                    'legend': {
                        **CHART_OPTIONS_BASE['plugins']['legend'],
                        'position': 'bottom',
                    },
                    'title': {
                        'display': True,
                        'text': _('dashboard.precipitation_in_toronto'),
                        'font': {'size': 16, 'weight': 'bold'},
                        'padding': {'bottom': 16},
                    },
                },
                'scales': {
                    'x': {
                        **CHART_OPTIONS_BASE['scales']['x'],
                        'title': {'display': True, 'text': 'Month of the Year'},
                    },
                    'y': {
                        **CHART_OPTIONS_BASE['scales']['y'],
                        'title': {'display': True, 'text': 'Precipitation in mm'},
                    },
                },
            },
        )
        chart_3 = ChartData(
            type='bar',
            data={
                'labels': ['Red', 'Blue', 'Yellow', 'Green', 'Purple', 'Orange'],
                'datasets': [
                    {
                        'label': 'Vote Count',
                        'data': [12, 19, 3, 5, 2, 3],
                        'backgroundColor': [
                            'rgba(239, 68, 68, 0.7)',
                            'rgba(59, 130, 246, 0.7)',
                            'rgba(234, 179, 8, 0.7)',
                            'rgba(34, 197, 94, 0.7)',
                            'rgba(139, 92, 246, 0.7)',
                            'rgba(249, 115, 22, 0.7)',
                        ],
                        'hoverBackgroundColor': [
                            'rgba(239, 68, 68, 0.9)',
                            'rgba(59, 130, 246, 0.9)',
                            'rgba(234, 179, 8, 0.9)',
                            'rgba(34, 197, 94, 0.9)',
                            'rgba(139, 92, 246, 0.9)',
                            'rgba(249, 115, 22, 0.9)',
                        ],
                        'borderRadius': 6,
                    }
                ],
            },
            options={
                **CHART_OPTIONS_BASE,
                'animation': {'duration': 1500, 'easing': 'easeInOutQuad'},
            },
        )
        chart_4 = ChartData(
            type='doughnut',
            data={
                'labels': [
                    _('dashboard.deposites'),
                    _('dashboard.withdraws'),
                    _('dashboard.fees'),
                    _('dashboard.refunds'),
                ],
                'datasets': [
                    {
                        'data': [45, 30, 15, 10],
                        'backgroundColor': [
                            'rgba(59, 130, 246, 0.7)',
                            'rgba(249, 115, 22, 0.7)',
                            'rgba(139, 92, 246, 0.7)',
                            'rgba(34, 197, 94, 0.7)',
                        ],
                        'hoverBackgroundColor': [
                            'rgba(59, 130, 246, 0.9)',
                            'rgba(249, 115, 22, 0.9)',
                            'rgba(139, 92, 246, 0.9)',
                            'rgba(34, 197, 94, 0.9)',
                        ],
                        'borderWidth': 0,
                        'spacing': 4,
                        'borderRadius': 4,
                    }
                ],
            },
            options={
                'responsive': True,
                'maintainAspectRatio': False,
                'plugins': {
                    'legend': {
                        'position': 'bottom',
                        'labels': {
                            'font': {'size': 12},
                            'usePointStyle': True,
                            'pointStyle': 'circle',
                            'padding': 16,
                        },
                    },
                    'title': {
                        'display': True,
                        'text': _('dashboard.operations_distribution'),
                        'font': {'size': 16, 'weight': 'bold'},
                        'padding': {'bottom': 16},
                    },
                    'tooltip': {
                        'cornerRadius': 8,
                        'padding': 12,
                    },
                },
            },
        )
        dashboard_period = PeriodGraph(
            title=_('dashboard.period_title'),
            value='150 558,01 RUB',
            change=160,
            subcards=[
                Subcard(title=_('payin'), value='24 051.16 RUB'),
                Subcard(title=_('payout'), value='124 051.16 RUB'),
            ],
            vertical=['1 400,00 RUB', '1 050,00 RUB', '700,00 RUB', '350,00 RUB', '0,00 RUB'],
            horizontal=[
                _('weekday.wed'),
                _('weekday.thu'),
                _('weekday.fri'),
                _('weekday.sat'),
                _('weekday.sun'),
                _('weekday.mon'),
                _('weekday.tue'),
            ],
            values=[
                [25, 35],
                [35, 45],
                [8, 40],
                [85, 45],
                [40, 35],
                [65, 70],
                [15, 40],
            ],
        )
        wallet_balance = SmallGraph(
            title=_('dashboard.wallet_balance'),
            value='950 150 558,01 RUB',
            change=15,
            points={
                _('date.day_month') % {'day': 1, 'month': _('month.may')}: 5,
                _('date.day_month') % {'day': 5, 'month': _('month.may')}: 35,
                _('date.day_month') % {'day': 10, 'month': _('month.may')}: 45,
                _('date.day_month') % {'day': 15, 'month': _('month.may')}: 30,
                _('date.day_month') % {'day': 20, 'month': _('month.may')}: 35,
            },
        )
        payment_payout_diff = SmallGraph(
            title=_('dashboard.payment_payout_diff'),
            value='950 150 558,01 RUB',
            change=-15,
            points={
                _('date.day_month') % {'day': 1, 'month': _('month.may')}: 5,
                _('date.day_month') % {'day': 5, 'month': _('month.may')}: 35,
                _('date.day_month') % {'day': 10, 'month': _('month.may')}: 45,
                _('date.day_month') % {'day': 15, 'month': _('month.may')}: 30,
                _('date.day_month') % {'day': 20, 'month': _('month.may')}: 35,
            },
        )
        result = DashboardContainer(
            components=[
                DashboardContainer(cols=12, md=7, components=[dashboard_period]),
                DashboardContainer(cols=12, md=5, components=[wallet_balance, payment_payout_diff]),
                chart_1,
                chart_2,
                DashboardContainer(cols=12, md=6, components=[chart_3]),
                DashboardContainer(cols=12, md=6, components=[chart_4]),
            ],
        )
        return result
