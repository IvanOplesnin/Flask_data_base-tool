"""Явно помеченные демонстрационные зависимости для обучения интерфейсу."""

import numpy as np
import plotly.graph_objs as go
from dash import Dash, dcc, html


def create_reference_dash(flask_app):
    dash_app = Dash(server=flask_app, url_base_pathname='/dash_reference/')
    speed = np.linspace(20, 200, 30)

    def figure(title, y_title, values):
        return dcc.Graph(
            figure=go.Figure(
                data=[go.Scatter(x=speed, y=values, mode='lines', name='Демонстрационная зависимость')],
                layout=go.Layout(
                    title=title,
                    xaxis_title='Скорость резания Vc, м/мин',
                    yaxis_title=y_title,
                    annotations=[{
                        'text': 'ДЕМО: не является результатом измерения',
                        'xref': 'paper', 'yref': 'paper', 'x': 0.5, 'y': 0.02,
                        'showarrow': False, 'font': {'color': '#a33'},
                    }],
                ),
            )
        )

    dash_app.layout = html.Div(
        className='container py-3',
        children=[
            html.H2('Демонстрационные зависимости'),
            html.P('Справочные кривые нужны только для проверки интерфейса. Они не смешиваются с экспериментальными данными.'),
            html.Div([
                html.H3('Точение'),
                figure('Примерная зависимость стойкости от скорости', 'Стойкость, усл. ед.', 100 * speed ** -0.2),
                html.H3('Фрезерование'),
                figure('Примерная зависимость температуры от скорости', 'Температура, усл. ед.', 0.6 * speed ** 0.4),
                html.H3('Резьбонарезание'),
                figure('Примерная зависимость нагрузки от скорости', 'Нагрузка, усл. ед.', 0.8 * speed ** -0.12),
            ]),
        ],
    )

    return dash_app

