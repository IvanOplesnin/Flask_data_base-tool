import os
from typing import Any
import json
from my_app import db, app
from my_app.models import CsvFiles, Experiments, RecommendationParameters, Materials, Tools, Coating, Coefficients, \
    MaterialType
# import pandas as pd
# import matplotlib.pyplot as plt
# import shutil
# import openpyxl
# import pprint
# import random
# #
app.app_context().push()

# data_force = pd.read_excel('Силы.xlsx', sheet_name=[0, 1, 2, 3])
# data_temrature = pd.read_excel('Температура.xlsx', sheet_name=[0, 1, 2, 3])
#
#
# def create_dict_coefficients(data):
#     last_columns = len(data.columns) - 1
#     dict_coefficients = {data.iloc[i, 0]: data.iloc[i, last_columns] for i in range(len(data))}
#     return dict_coefficients
#
#
# def create_dict_from_file(filename):
#     data = pd.read_excel(filename, sheet_name=[0, 1, 2, 3])
#     dict_return = {dt.columns[0]: create_dict_coefficients(dt) for i, dt in data.items()}
#     return dict_return
#
#
# list_file_name = ['Силы.xlsx', 'Температура.xlsx', "Стойкость.xlsx"]
#
# dictionary = {i.replace('.xlsx', ''): create_dict_from_file(i) for i in list_file_name}
#
# final_dict = {}
#
# for type_coefficient, dict_material in dictionary.items():
#     for material, dict_coefficients in dict_material.items():
#         for coating, coefficient in dict_coefficients.items():
#             if f'{material}, {coating}, Фреза 6157-7005' in final_dict.keys():
#                 final_dict[f'{material}, {coating}, Фреза 6157-7005'][type_coefficient] = coefficient
#             else:
#                 final_dict[f'{material}, {coating}, Фреза 6157-7005'] = {type_coefficient: coefficient}
#
# with open('coefficients.json', 'w', encoding='utf-8') as f:
#     json.dump(final_dict, f, indent=4, ensure_ascii=False)
#
#
# for key, values in final_dict.items():
#     material_id = Materials.query.filter_by(name=key.split(', ')[0].strip()).first().id
#     coating_id = coating.query.filter_by(name=key.split(', ')[1].strip()).first().id
#     tooldate_id = Tools.query.filter_by(name=key.split(', ')[2].strip()).first().id
#     force_coefficient = values['Силы']
#     temperature_coefficient = values['Температура']
#     durability_coefficient = random.randint(60, 100)
#     try:
#         coefficient = Coefficients(material_id=material_id,
#                                    coating_id=coating_id,
#                                    tool_id=tooldate_id,
#                                    cutting_force_coefficient=force_coefficient,
#                                    cutting_temperature_coefficient=temperature_coefficient,
#                                    durability_coefficient=durability_coefficient)
#
#         db.session.add(coefficient)
#         db.session.commit()
#     except:
#         print(material_id, coating_id, tooldate_id, ' - ', 'уже существуют в базе данных')
#
# #
# all_coefficient = Coefficients.query.all()
# for coef in all_coefficient:
#     print(coef)
    # db.session.delete(coef)
    # db.session.commit()

from my_app import db, app
from sqlalchemy.orm import Session
from sqlalchemy import text

# app.app_context().push()
# Создаем соединение с базой данных
# with Session(db.engine) as session:
#     session.execute(text('DROP TABLE IF EXISTS material_type'))
#     session.commit()  # Не забываем зафиксировать изменения
# from sqlalchemy import inspect
#
# inspector = inspect(db.engine)
# print(inspector.get_table_names())

# materials = Materials.query.all()
# try:
#     for material in materials:
#         if 'ВТ' in material.name:
#             material.type_id = 1
#         else:
#             material.type_id = 2
#     db.session.commit()
# except:
#     db.session.rollback()
# finally:
#     db.session.close()


