import datetime

import pandas as pd

from my_app import app, db
from my_app.models import Coating, Experiments, WearTables

app.app_context().push()

dict_df = pd.read_excel('123.xlsx', sheet_name=[0, 1, 2])

df = dict_df[2]
x = df['l, м'] * 1000
material = 'ВТ3-1'
tool_id = 1
material_id = 5
# materials = Materials.query.all()
# for materials in materials:
#     print(materials.name, '-', materials.id)


# for columns in df.columns[1:]:
#     coating = columns.replace(' ', '') if "Без " not in columns else columns
#     y = df[columns]
#     material_id = 5
#     coating_id = Coating.query.filter_by(name=coating).first().id
#     tool_id = 1
#     points = list(zip(x, y))
#     points = [point for point in points if not pd.isna(point[1])]
#     points.insert(0, (0, 0))
#     y1 = list(filter(lambda x: x[1] > 0.3, points))[0][1]
#     x1 = list(filter(lambda x: x[1] > 0.3, points))[0][0]
#     x0, y0 = (list(filter(lambda x: x[1] < 0.3, points))[-1][0],
#               list(filter(lambda x: x[1] < 0.3, points))[-1][1])
#     y2 = 0.3
#     x2 = x0 + (x1 - x0) * (y2 - y0) / (y1 - y0)
#     new_experiment = Experiments(
#         material_id=material_id,
#         coating_id=coating_id,
#         tool_id=tool_id,
#         spindle_speed=2000,
#         feed_table=200,
#         depth_cut=1.5,
#         width_cut=5,
#         length_path=x2,
#         durability=x2 / 200,
#         data_experiment=datetime.date(2021, 6, 24)
#     )
#     db.session.add(new_experiment)
#     db.session.flush()
#     experiment_id = new_experiment.id
#     for point in points:
#         length = point[0]
#         wear = point[1]
#         new_wear_table = WearTables(
#             experiment_id=experiment_id,
#             length=length,
#             wear=wear
#         )
#         db.session.add(new_wear_table)
#
# db.session.commit()

# experiments = Experiments.query.filter_by(material_id=5).all()
# for j in experiments:
#     wear_tables = WearTables.query.filter_by(experiment_id=j.id).all()
#     for i in wear_tables:
#         db.session.delete(i)
#     db.session.delete(j)
# db.session.commit()

df = df.drop(['(ZrAl)N (NNV)', 'ZrN'], axis=1)
print(df.columns)
for columns in df.columns[1:]:
    columns_ = columns.strip()
    if 'Без' in columns_:
        coating = columns_
    else:
        coating = '(CrAlSi)N' if 'DLC' not in columns_ else '(CrAlSi)N+DLC'

    print(coating)
    coating_id = Coating.query.filter_by(name=coating.strip()).first().id
    y = df[columns]
    points = list(zip(x, y))
    points = [point for point in points if not pd.isna(point[1])]
    points.insert(0, (0, 0))
    y1 = list(filter(lambda x: x[1] > 0.3, points))[0][1]
    x1 = list(filter(lambda x: x[1] > 0.3, points))[0][0]
    x0, y0 = (list(filter(lambda x: x[1] < 0.3, points))[-1][0],
              list(filter(lambda x: x[1] < 0.3, points))[-1][1])
    y2 = 0.3
    x2 = x0 + (x1 - x0) * (y2 - y0) / (y1 - y0)
    new_experiment = Experiments(
        material_id=material_id,
        coating_id=coating_id,
        tool_id=tool_id,
        spindle_speed=2000,
        feed_table=200,
        depth_cut=1.5,
        width_cut=5,
        length_path=x2,
        durability=x2 / 200,
        data_experiment=datetime.date(2021, 7, 12)
    )
    db.session.add(new_experiment)
    db.session.flush()
    experiment_id = new_experiment.id
    print(experiment_id)
    for point in points:
        length = point[0]
        wear = point[1]
        new_wear_table = WearTables(
            experiment_id=experiment_id,
            length=length,
            wear=wear
        )
        db.session.add(new_wear_table)
        print(new_wear_table)


db.session.commit()
