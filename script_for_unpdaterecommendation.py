import math

import pandas as pd
from sqlalchemy.orm import joinedload


from my_app import app, db
from my_app.models import RecommendationParameters, Materials, Coating, Tools

app.app_context().push()

# reccommendation_parameters = RecommendationParameters.query.all()
# for i in reccommendation_parameters:
#     db.session.delete(i)
#
# db.session.commit()

dict_df = pd.read_excel('Стойкость (1).xlsx', sheet_name=[0, 1, 2, 3])
for key, df in dict_df.items():
    material = df.columns[0]
    for row in df.index:
        coating: str = df.iloc[row, 0]
        tool = 'Фреза 6157-7005'
        material_id = Materials.query.filter_by(name=material).first().id
        # try:
        #     if 'AlTiC' in coating:
        #         coating = coating.replace(coating, 'AlTiCrN3') if '+' not in coating else coating
        #     if 'AlTiC' in coating and '+' in coating:
        #         coating = coating.replace(coating, 'AlTiCrN3+TiB2')
        #     if 'AlTiN3' in coating and '+' in coating:
        #         coating = coating.replace(coating, 'AlTiN3+TiB2')
        #
        coating_id = Coating.query.filter_by(name=coating.strip()).first().id
        # except AttributeError as e:
        #     print(coating)

        tool: Tools = Tools.query.filter_by(name=tool).first()
        tool_id = tool.id
        spindle_speed = (df.iloc[row, -1]*1000)/(math.pi*tool.milling_geometry.diameter)
        feed_table = df.iloc[row, 4]*4*spindle_speed
        recommendation_parameters = RecommendationParameters(
            material_id=material_id,
            coating_id=coating_id,
            tool_id=tool_id,
            feed_table=feed_table,
            spindle_speed=spindle_speed
        )
        db.session.add(recommendation_parameters)

db.session.commit()


# all_coating = Coating.query.filter_by(name='AlTiCrN3+TiB2').all()
# for i in all_coating:
#     if i.name == 'AlTiCrN3+TiB2':
#         print(i.name, '---')



