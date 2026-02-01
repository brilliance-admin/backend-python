from brilliance_admin import schema
from brilliance_admin.schema.dashboard.category_dashboard import (
    ChartData, DashboardContainer, DashboardData, PeriodGraph, SmallGraph, Subcard)
from brilliance_admin.translations import TranslateText as _


class GraphsFiltersSchema(schema.FieldsSchema):
    id = schema.IntegerField(label='ID')
    created_at = schema.DateTimeField(label=_('created_at'))

    _fields = [
        'id',
        'created_at',
    ]


class GraphsExample(schema.CategoryDashboard):
    slug = 'dashboard'
    title = _('dashboard.title')
    icon = 'mdi-chart-bar-stacked'

    table_filters = GraphsFiltersSchema()

    async def get_data(self, data: DashboardData, user) -> DashboardContainer:
        chart_1 = ChartData(
            type='line',
            data={
                'labels': ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul"],
                'datasets': [
                    {
                        'label': "Dataset #1",
                        'backgroundColor': "rgba(255,99,132,0.2)",
                        'borderColor': "rgba(255,99,132,1)",
                        'borderWidth': 2,
                        'hoverBackgroundColor': "rgba(255,99,132,0.4)",
                        'hoverBorderColor': "rgba(255,99,132,1)",
                        'data': [65, 59, 20, 81, 56, 55, 40],
                    },
                    {
                        'label': "Dataset #2",
                        'backgroundColor': "rgba(233, 150, 122,0.2)",
                        'borderColor': "rgba(233, 150, 122,1)",
                        'borderWidth': 2,
                        'hoverBackgroundColor': "rgba(233, 150, 122,0.4)",
                        'hoverBorderColor': "rgba(233, 150, 122,1)",
                        'data': [30, 35, 29, 15, 3, 10, 22],
                    },
                ],
            },
            options={
                'responsive': True,
                'plugins': {
                    'legend': {
                        'position': 'top',
                    },
                    'title': {'display': True, 'text': 'Chart.js Line Chart'},
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
                        'backgroundColor': 'lightblue',
                        'borderColor': 'royalblue',
                        'data': [26.4, 39.8, 66.8, 66.4, 40.6, 55.2, 77.4, 69.8, 57.8, 76, 110.8, 142.6],
                    }
                ],
            },
            options={
                'layout': {
                    'padding': 10,
                },
                'legend': {
                    'position': 'bottom',
                },
                'title': {'display': True, 'text': 'Precipitation in Toronto'},
                'scales': {
                    'yAxes': [{'scaleLabel': {'display': True, 'labelString': 'Precipitation in mm'}}],
                    'xAxes': [{'scaleLabel': {'display': True, 'labelString': 'Month of the Year'}}],
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
                            'rgba(255, 99, 132, 0.2)',
                            'rgba(54, 162, 235, 0.2)',
                            'rgba(255, 205, 86, 0.2)',
                            'rgba(75, 192, 192, 0.2)',
                            'rgba(153, 102, 255, 0.2)',
                            'rgba(255, 159, 64, 0.2)',
                        ],
                        'borderColor': [
                            'rgb(255, 99, 132)',
                            'rgb(54, 162, 235)',
                            'rgb(255, 205, 86)',
                            'rgb(75, 192, 192)',
                            'rgb(153, 102, 255)',
                            'rgb(255, 159, 64)',
                        ],
                        'borderWidth': 1,
                    }
                ],
            },
            height=50,
            options={
                'scales': {'x': {'beginAtZero': True, 'ticks': {'color': '#333'}}, 'y': {'ticks': {'color': '#333'}}},
                'animation': {'duration': 1500, 'easing': 'easeInOutQuad'},
            },
        )
        dashboard_period = PeriodGraph(
            title=_('dashboard.period_title'),
            value='150 558,01 RUB',
            change=160,
            subcards=[
                Subcard(title=_('payin'), value='24 051.16 RUB', color='#4CAF50'),
                Subcard(title=_('payout'), value='124 051.16 RUB', color='#1976D2'),
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
                DashboardContainer(
                    cols=12,
                    md=7,
                    components=[dashboard_period]
                ),
                DashboardContainer(
                    cols=12,
                    md=5,
                    components=[wallet_balance, payment_payout_diff]
                ),
                chart_1,
                chart_2,
                chart_3,
            ],
        )
        return result
