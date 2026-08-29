from sqlalchemy import create_engine
import pandas as pd

from my_app import app, db
from my_app.models import MaterialType, Materials, Coating, Adhesive, Tools, MillingGeometry, \
    RecommendationParameters, Coefficients, Experiments, CsvFiles

app.app_context().push()  # this is needed to make the app context available to the views

engine = create_engine('sqlite:///C:/Users/aples/PycharmProjects/Flask_data_base-tool/me_app.db')

# material_type = pd.read_sql_query("SELECT * FROM material_type", engine)
# material = pd.read_sql_query("SELECT * FROM material", engine)
#
# for i in material_type.index:
#
#     new_material_type = MaterialType(name=material_type.loc[i, "name"])
#     db.session.add(new_material_type)
#
#
# print(material.columns)
#
# for i in material.index:
#     new_material = Materials(
#         name=material.loc[i, "Name"],
#         prop_physics=material.loc[i, "PropPhysics"],
#         structure=material.loc[i, "Structure"],
#         properties=material.loc[i, "Properties"],
#         gost=material.loc[i, "Gost"],
#         type_id=int(material.loc[i, 'type_id'])
#     )
#     db.session.add(new_material)
#
#
# db.session.commit()
# db.session.close()

# coating = pd.read_sql_query("SELECT * FROM Coating", engine)
#
# for i in coating.index:
#     new_coating = Coating(
#         name=coating.loc[i, "Name"],
#         material_coating=coating.loc[i, "MaterialCoating"],
#         color_coating=coating.loc[i, "ColorCoating"],
#         type_application=coating.loc[i, "TypeApplication"],
#         max_thickness=coating.loc[i, "MaxThickness"],
#         nano_hardness=coating.loc[i, "NanoHardness"],
#         temperature_resistance=coating.loc[i, "TemratureResistance"],
#         coefficient_friction=coating.loc[i, "KoefficientFriction"]
#     )
#     db.session.add(new_coating)
#
# db.session.commit()

# adhesive = pd.read_sql_query("SELECT * FROM Adhesive", engine)
#
#
# for i in adhesive.index:
#     material_id = Materials.query.filter(Materials.name.ilike(f'%{adhesive.loc[i, "material"]}%')).first().id
#     try:
#         adhesive.loc[i, "coating"] = adhesive.loc[i, "coating"].replace('AlTiСrN3', 'AlTiCrN3').replace(' +', '+')
#         coating_id = Coating.query.filter_by(name=adhesive.loc[i, "coating"]).first().id
#     except:
#         print(adhesive.loc[i, "coating"])
#         raise ValueError
#
#     new_adhesive = Adhesive(
#         material_id=material_id,
#         coating_id=coating_id,
#         temperature=int(adhesive.loc[i, "temperature"]),
#         bond_strength_adhesive=adhesive.loc[i, "bond_strength_adhesive"],
#         normal_shear_strength=adhesive.loc[i, "normal_shear_strength"],
#     )
#     db.session.add(new_adhesive)
#
# db.session.commit()


# tools = pd.read_sql_query("SELECT * FROM ToolsDate", engine)
#
# for i in tools.index:
#     if len(tools.loc[i, "Name"]) > 10:
#         new_tool = Tools(
#             name=tools.loc[i, "Name"],
#             name_easy=f'Фреза {tools.loc[i, "Diameter"]:.0f} мм',
#             tool_type='milling',
#             material_tool=tools.loc[i, "MaterialTool"],
#             is_indexable=False
#         )
#
#         new_geometry = MillingGeometry(
#             diameter=tools.loc[i, "Diameter"],
#             number_teeth=int(tools.loc[i, "NumberTeeth"]),
#             front_angle=5,
#             spiral_angle=30.0,
#             f_rear_angle=10.0,
#             s_rear_angle=15.0,
#             main_rear_angle=7.0,
#             angular_pitch='uneven'
#         )
#
#         new_tool.milling_geometry = new_geometry
#         db.session.add(new_tool)
#
# db.session.commit()

# tools = Tools.query.all()
# for tool in tools:
#     milling_geometry = MillingGeometry.query.filter_by(tool_id=tool.id).first()
#     db.session.delete(tool)
#     db.session.delete(milling_geometry)
#
#     db.session.commit()

recommendation_parameters = pd.read_sql_query("SELECT * FROM recomeded_speed", engine)
# for i in set(recommendation_parameters['Coating']):
#     coating_id = Coating.query.filter_by(name=i).first().id
#
# for i in set(recommendation_parameters['Material']):
#     material_id = Materials.query.filter_by(name=i).first().id


tools_dict = {
    'Фреза 12': 'Фреза 6157-7005',
    'Фреза 20': 'Фреза 6157-7007'
}

# for i in set(recommendation_parameters['Tool']):
#     if i in tools_dict:
#         tool = Tools.query.filter_by(name=tools_dict[i]).first()
#         print(tool.id, tool.name)


for i in recommendation_parameters.index:
    if recommendation_parameters.loc[i, "Tool"] in tools_dict:
        material_id = Materials.query.filter_by(name=recommendation_parameters.loc[i, "Material"]).first().id
        coating_id = Coating.query.filter_by(name=recommendation_parameters.loc[i, "Coating"]).first().id
        tool_id = Tools.query.filter_by(name=tools_dict[recommendation_parameters.loc[i, "Tool"]]).first().id
        new_recommendation_parameters = RecommendationParameters(
            material_id=material_id,
            coating_id=coating_id,
            tool_id=tool_id,
            spindle_speed=int(recommendation_parameters.loc[i, "SpindleSpeed"]),
            feed_table=recommendation_parameters.loc[i, "FeedTable"],
            roughness=recommendation_parameters.loc[i, "Roughness"],
            hardening=recommendation_parameters.loc[i, "Hardening"],
            durability=recommendation_parameters.loc[i, "Durability"],
            micro_hardness=recommendation_parameters.loc[i, "Microhardness"]
        )
        db.session.add(new_recommendation_parameters)

db.session.commit()


# recommendation_parameters = RecommendationParameters.query.all()
# for recommendation_parameter in recommendation_parameters:
#     db.session.delete(recommendation_parameter)
#     db.session.commit()

# coefficients = pd.read_sql_query("SELECT * FROM Coefficients", engine)
# for i in coefficients.index:
#     new_coefficient = Coefficients(
#         material_id=int(coefficients.loc[i, "material_id"]),
#         coating_id=int(coefficients.loc[i, "coating_id"]),
#         tool_id=int(coefficients.loc[i, "tool_id"]),
#         cutting_force_coefficient=coefficients.loc[i, "cutting_force_coefficient"],
#         cutting_temperature_coefficient=coefficients.loc[i, "cutting_temperature_coefficient"],
#         durability_coefficient=coefficients.loc[i, "durability_coefficient"]
#     )
#     db.session.add(new_coefficient)
#     db.session.commit()


# csv_file = pd.read_sql_query("SELECT * FROM csv__files", engine)
# print(csv_file.columns)
#
# for i in csv_file.index:
#     new_csv_file = CsvFiles(
#         filename_strength=csv_file.loc[i, "filename_strengh"],
#         filename_temperature=csv_file.loc[i, "filename_temrature"],
#         path=csv_file.loc[i, "path"],
#         path_graphic_s=csv_file.loc[i, "path_graphik_s"],
#         path_graphic_t=csv_file.loc[i, "path_graphik_t"]
#     )
#     db.session.add(new_csv_file)
#     db.session.commit()


# experimnts = pd.read_sql_query("SELECT * FROM Experiments", engine)
# print(experimnts.columns)
# for i in experimnts.index:
#     material_id = Materials.query.filter_by(name=experimnts.loc[i, "Material"]).first().id
#     try:
#         coating_id = Coating.query.filter_by(
#             name=experimnts.loc[i, "Coating"].replace('AlTiNCrN3', 'AlTiCrN3')).first().id
#     except:
#         raise ValueError(f'{experimnts.loc[i, "Coating"]}')
#     tool_id = Tools.query.filter_by(name=experimnts.loc[i, "Tool"]).first().id
#     new_experiment = Experiments(
#         material_id=material_id,
#         coating_id=coating_id,
#         tool_id=tool_id,
#         spindle_speed=float(experimnts.loc[i, "SpindleSpeed"]),
#         feed_table=experimnts.loc[i, "FeedTable"],
#         depth_cut=experimnts.loc[i, "DepthCut"],
#         width_cut=experimnts.loc[i, "WidthCut"],
#         length_path=experimnts.loc[i, "LengthPath"],
#         durability=experimnts.loc[i, "Durability"],
#         csv_id=int(experimnts.loc[i, "csv_id"])
#     )
#     db.session.add(new_experiment)
# db.session.commit()

# experiments = Experiments.query.all()
# for experiment in experiments:
#     db.session.delete(experiment)
#     db.session.commit()
