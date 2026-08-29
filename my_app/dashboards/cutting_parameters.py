from dash import Dash, dcc, html, Input, Output, callback, ctx
import plotly.graph_objs as go
import numpy as np


def create_dash(flask_app):
    dash_app = Dash(server=flask_app, url_base_pathname='/dash/')

    dash_app.layout = html.Div(className='container-mt-5', children=[
        html.H1('Параметры резания'),

        # Отображение результатов расчёта
        html.Div(className='row', children=[
            html.Div(className='col', children=[
                html.Span('Сила резания: '),
                html.Span(id='cutting_force', children='-')
            ]),
            html.Div(className='col', children=[
                html.Span('Температура резания: '),
                html.Span(id='cutting_temperature', children='-')
            ]),
            html.Div(className='col', children=[
                html.Span('Стойкость инструмента: '),
                html.Span(id='tool_life', children='-')
            ])
        ]),

        # Выпадающий список параметров
        html.Div(className='form-group', children=[
            html.Label('Параметр', htmlFor='parameter-dropdown'),
            dcc.Dropdown(
                id='parameter-dropdown',
                options=[
                    {'label': 'Сила резания', 'value': 'cutting_force'},
                    {'label': 'Температура резания', 'value': 'cutting_temperature'},
                    {'label': 'Стойкость инструмента', 'value': 'tool_life'}
                ],
                value='cutting_force',
                className='form-control'
            )
        ]),

        # Контейнер для графиков и слайдеров
        html.Div(style={'display': 'flex'}, children=[
            # Первый график и слайдер
            html.Div(style={'flex': '1', 'padding': '10px'}, children=[
                html.Div(className='slider-container', children=[
                    html.Div(className='value-container', children=[
                        html.Label('Скорость резания (V), м/мин:', htmlFor='slider_speed'),
                        dcc.Slider(
                            id='slider_speed',
                            min=10,
                            max=200,
                            step=1,
                            value=75,
                            marks={i: str(i) for i in range(10, 201, 20)},
                            className='form-range'
                        ),
                        html.Br(),
                        html.Div(children=[
                            html.Div('Введите скорость резания(м/мин): ', style={'display': 'inline'}),
                            dcc.Input(id='input_speed', type='number', size='5', min=0, max=200, value=75),
                            html.Div(' м/мин', style={'display': 'inline'}),
                            html.Div(children=[
                                html.Div('Выбранная скорость резания: ', style={'display': 'inline'}),
                                html.Span(id='cutting_speed_value', children='75', className='result',
                                          style={'display': 'inline'}),
                                html.Span(' м/мин', style={'display': 'inline'})
                            ]),
                            dcc.Graph(id='graph_speed')
                        ])
                    ])
                ])
            ]),

            # Второй график и слайдер
            html.Div(style={'flex': '1', 'padding': '10px'}, children=[
                html.Div(className='slider-container', children=[
                    html.Div(className='value-container', children=[
                        html.Label('Подача на зуб (S), мм/зуб:', htmlFor='slider_s'),
                        dcc.Slider(
                            id='slider_s',
                            min=0.001,
                            max=0.5,
                            step=0.001,
                            value=0.025,
                            marks={round(i, 3): str(round(i, 3)) for i in [0.001, 0.1, 0.2, 0.3, 0.4, 0.5]},
                            className='form-range'
                        ),
                        html.Br(),
                        html.Div(children=[
                            html.Div('Введите подачу на зуб(S): ', style={'display': 'inline'}),
                            dcc.Input(id='input_supply', type='number', size='5', min=0, max=0.5, value=0.025,
                                      step=0.001,
                                      style={'display': 'inline'}),
                            html.Div(' мм/зуб', style={'display': 'inline'}),
                            html.Div(children=[
                                html.Div('Выбранная подача на зуб: ', style={'display': 'inline'}),
                                html.Span(id='feed_per_tooth_value', children='0.025', className='result',
                                          style={
                                              'display': 'inline'
                                          }),
                                html.Span(' мм/зуб', style={'display': 'inline'})
                            ]),
                            dcc.Graph(id='graph_supply')

                        ])
                    ])
                ])
            ])
        ])
    ])

    @dash_app.callback(
        [Output('graph_speed', 'figure'),
         Output('graph_supply', 'figure'),
         Output('cutting_force', 'children'),
         Output('cutting_temperature', 'children'),
         Output('tool_life', 'children'),
         Output('cutting_speed_value', 'children'),
         Output('feed_per_tooth_value', 'children'),
         Output('slider_speed', 'value'),
         Output('slider_s', 'value'),
         Output('input_speed', 'value'),
         Output('input_supply', 'value')
         ],
        [Input('parameter-dropdown', 'value'),
         Input('slider_speed', 'value'),
         Input('slider_s', 'value'),
         Input('input_speed', 'value'),
         Input('input_supply', 'value')
         ]
    )
    def update_graph_and_calculations(selected_parameter, speed_slider, supply_slider, input_speed, input_supply):
        # Данные принадлежат текущей пользовательской сессии, а не процессу Flask.
        from flask import session
        graph_data = session.get('graph_data', {})

        # Проверяем наличие коэффициентов
        if not graph_data:
            # Возвращаем пустые графики и дефолтные значения
            fig_speed = go.Figure()
            fig_supply = go.Figure()
            cutting_force = '-'
            cutting_temperature = '-'
            tool_life = '-'
            length_processing = '-'
        else:
            # Извлекаем коэффициенты
            Kc = graph_data.get('cutting_force_coefficient', 1)
            Kt = graph_data.get('cutting_temperature_coefficient', 1)
            Kl = graph_data.get('durability_coefficient', 1)
            # Извлекаем данные для расчетов подачи в минуту и продйденного пути.
            diameter = graph_data.get('diameter', 1)
            teeth_count = graph_data.get('teeth_count', 1)
            material_name = graph_data.get('material_name', '')

            # Показатели степени
            a_force = -0.12
            b_force = 0.95
            a_temp = 0.4
            b_temp = 0.24
            a_life = -0.2
            b_life = -0.15 if 'ВТ' in material_name else -0.1

            # Приравниваем знавения слайдера к значению вводимого значения,
            # если функция вызывалась изменением input объукта.
            trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
            if trigger_id == 'input_speed':
                speed_slider = input_speed
            elif trigger_id == 'input_supply':
                supply_slider = input_supply

            # Диапазоны значений скорости и подачи
            speed_values = np.arange(10, 201, 1)
            supply_values = np.arange(0.001, 0.501, 0.001)

            rotation_per_minute = (speed_values * 1000) / (3.14 * diameter)
            feed_minute_massive = supply_slider * rotation_per_minute * teeth_count

            rotation_stat = (speed_slider * 1000) / (3.14 * diameter)
            # Массив значений на которое надо умножить время для получения расстояния
            supply_values_minute = supply_values * rotation_stat * teeth_count

            # Вычисление значений для графиков
            if selected_parameter == 'cutting_force':
                values_of_speed = Kc * (speed_values ** a_force) * (supply_slider ** b_force)
                values_of_supply = Kc * (speed_slider ** a_force) * (supply_values ** b_force)
                y_axis_title = 'Сила резания (Н)'
            elif selected_parameter == 'cutting_temperature':
                values_of_speed = Kt * (speed_values ** a_temp) * (supply_slider ** b_temp)
                values_of_supply = Kt * (speed_slider ** a_temp) * (supply_values ** b_temp)
                y_axis_title = 'Температура резания (°C)'
            elif selected_parameter == 'tool_life':
                values_of_speed = Kl * (speed_values ** a_life) * (supply_slider ** b_life)
                values_of_supply = Kl * (speed_slider ** a_life) * (supply_values ** b_life)
                y_axis_title = 'Стойкость инструмента (мин)'
            else:
                values_of_speed = Kl * (speed_values ** a_life) * (supply_slider ** b_life) * feed_minute_massive
                values_of_supply = Kl * (speed_slider ** a_life) * (supply_values ** b_life) * supply_values_minute
                y_axis_title = 'Пройденный путь (мм)'

            # Построение графиков
            fig_speed = go.Figure(data=[
                go.Scatter(x=speed_values, y=values_of_speed, mode='lines', name=y_axis_title)
            ])
            fig_supply = go.Figure(data=[
                go.Scatter(x=supply_values, y=values_of_supply, mode='lines', name=y_axis_title)
            ])

            # Добавление выбранных точек
            fig_speed.add_trace(go.Scatter(
                x=[speed_slider],
                y=[values_of_speed[int(speed_slider - 10)]],
                mode='markers',
                marker=dict(size=12, color='red'),
                name='Выбранная точка'
            ))
            fig_supply.add_trace(go.Scatter(
                x=[supply_slider],
                y=[values_of_supply[int((supply_slider - 0.001) / 0.001)]],
                mode='markers',
                marker=dict(size=12, color='red'),
                name='Выбранная точка'
            ))

            fig_speed.update_layout(
                title=f'Зависимость {y_axis_title} от скорости резания',
                xaxis_title='Скорость резания (м/мин)',
                yaxis_title=y_axis_title,
                legend=dict(
                    x=0.5,
                    y=-0.4,
                    xanchor='center',
                    yanchor='bottom'
                )
            )

            fig_supply.update_layout(
                title=f'Зависимость {y_axis_title} от подачи на зуб',
                xaxis_title='Подача на зуб (мм/зуб)',
                yaxis_title=y_axis_title,
                legend=dict(
                    x=0.5,
                    y=-0.4,
                    xanchor='center',
                    yanchor='bottom'
                )
            )

            # Вычисление результатов
            cutting_force_value = Kc * (speed_slider ** a_force) * (supply_slider ** b_force)
            cutting_temperature_value = Kt * (speed_slider ** a_temp) * (supply_slider ** b_temp)
            tool_life_value = Kl * (speed_slider ** a_life) * (supply_slider ** b_life)


            # Форматирование результатов
            cutting_force = f'{cutting_force_value:.2f} Н'
            cutting_temperature = f'{cutting_temperature_value:.2f} °C'
            tool_life = f'{tool_life_value:.2f} мин'


        # Обновление значений скорости и подачи
        cutting_speed_value = f'{speed_slider}'
        feed_per_tooth_value = f'{supply_slider:.3f}'

        return (
            fig_speed,
            fig_supply,
            cutting_force,
            cutting_temperature,
            tool_life,
            cutting_speed_value,
            feed_per_tooth_value,
            np.round(speed_slider, 2),
            np.round(supply_slider, 3),
            np.round(speed_slider, 2),
            np.round(supply_slider, 3)
        )

    return dash_app
