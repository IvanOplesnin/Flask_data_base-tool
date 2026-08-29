import plotly.graph_objs as go
from dash import Dash, dcc, html, Input, Output

from my_app.models import Experiments, WearTables


def create_dash_wear(flask_app):
    dash_app = Dash(server=flask_app,
                    url_base_pathname='/dash_wear/')

    def serve_layout():
        with flask_app.app_context():
            values: list[Experiments] = Experiments.query.all()
            dict_values = [
                {
                    'label': f'{experiment.material.name}, {experiment.coating.name}, {experiment.tool.name}',
                    'value': f'{experiment.id}'
                }
                for experiment in values if experiment.wear_tables
            ]
        return html.Div(className='container-mt-5',
                        children=[
                            dcc.Graph(id='dash_wear_graph'),
                            dcc.Dropdown(
                                id='dash_wear_dropdown',
                                options=dict_values,
                                multi=True  # Разрешаем множественный выбор
                            )
                        ]
                        )

    # Определяем layout как функцию
    dash_app.layout = serve_layout


    @dash_app.callback(
        Output('dash_wear_graph', 'figure'),
        Input('dash_wear_dropdown', 'value')
    )
    def update_figure(selected_experiment_ids):
        # Если ничего не выбрано, возвращаем пустую фигуру
        if not selected_experiment_ids:
            return go.Figure()

        # Убедимся, что selected_experiment_ids - это список
        if not isinstance(selected_experiment_ids, list):
            selected_experiment_ids = [selected_experiment_ids]

        with flask_app.app_context():
            fig = go.Figure()
            for experiment_id in selected_experiment_ids:
                # Преобразуем experiment_id в правильный тип (int)
                experiment_id = int(experiment_id)
                experiment = Experiments.query.get(experiment_id)
                if not experiment:
                    continue
                df: list[WearTables] = WearTables.query.filter_by(experiment_id=experiment_id).all()
                df_sorted = sorted(df, key=lambda x: x.length)
                x = [x.length for x in df_sorted]
                y = [y.wear for y in df_sorted]
                # Добавляем линию на график для каждого эксперимента
                fig.add_trace(go.Scatter(
                    x=x,
                    y=y,
                    mode='lines+markers',
                    name=f'{experiment.material.name}, {experiment.coating.name}, {experiment.tool.name}'
                ))

            # Добавляем горизонтальную линию y=0.3
            fig.add_hline(y=0.3)
            fig.update_layout(
                xaxis_title='Длина пути резания (мм)',
                yaxis_title='Износ по задней поверхности (мм)',
            )

            return fig


def create_wear_on_info_experiments(flask_app):
    dash_app = Dash(
        server=flask_app,
        url_base_pathname='/dash_wear_info/',  # Используем только этот параметр
        external_stylesheets=['/static/bootstrap.min.css']
    )

    dash_app.layout = html.Div(
        className='container mt-5',
        children=[
            dcc.Location(id='url', refresh=False),
            dcc.Graph(id='info_graph'),
        ]
    )

    @dash_app.callback(
        Output('info_graph', 'figure'),
        Input('url', 'search')
    )
    def update_graph(search):
        from urllib.parse import parse_qs
        query_params = parse_qs(search.lstrip('?'))
        experiment_id = query_params.get('experiment_id', [None])[0]

        if not experiment_id:
            return go.Figure()

        with flask_app.app_context():
            experiment = Experiments.query.get(int(experiment_id))
            if not experiment:
                return go.Figure()

            df: list[WearTables] = WearTables.query.filter_by(experiment_id=experiment.id).all()
            df_sorted = sorted(df, key=lambda x: x.length)
            x = [entry.length for entry in df_sorted]
            y = [entry.wear for entry in df_sorted]

            fig = go.Figure(
                data=[
                    go.Scatter(
                        x=x,
                        y=y,
                        mode='lines+markers',
                        name=f'Эксперимент {experiment.id}'
                    )
                ]
            )
            fig.add_hline(y=0.3)
            fig.update_layout(
                title=f'График износа для эксперимента {experiment.id}',
                xaxis_title='Длина пути резания (мм)',
                yaxis_title='Износ по задней поверхности (мм)',
            )
            return fig

