from brilliance_admin import schema
from brilliance_admin.schema.graphs.category_graphs import ChartData, GraphData, GraphsDataResult
from brilliance_admin.translations import TranslateText as _


class GraphsFiltersSchema(schema.FieldsSchema):
    id = schema.IntegerField(label='ID')
    created_at = schema.DateTimeField(label=_('created_at'))

    _fields = [
        'id',
        'created_at',
    ]


class GraphsExample(schema.CategoryGraphs):
    slug = 'graphs-example'
    title = _('graphs_example')
    icon = 'mdi-chart-bar-stacked'

    table_filters = GraphsFiltersSchema()

    async def get_data(self, data: GraphData, user) -> GraphsDataResult:
        return GraphsDataResult(
            charts=[
                ChartData(
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
                ),
                ChartData(
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
                ),
                ChartData(
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
                ),
            ]
        )
