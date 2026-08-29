from my_app import db,app
from my_app.models import Csv_Files, Experiments, RecomededSpeed, Material,Toolsdate,Coating, Adhesive
import csv
import random


app.app_context().push()


# with open('adhesive.csv', encoding='utf-8') as csvfile:
#     reader = csv.DictReader(csvfile)
#     for row in reader:
#         material = row['material'].strip()
#         coating = row['coating'].strip()
#         temperature = row['temperature']
#         bond_strength_adhesive = row['tpp']
#         normal_shear_strength = row['prn']
#
#         adhesive = Adhesive(material=material,
#                             coating=coating,
#                             temperature=temperature,
#                             bond_strength_adhesive=bond_strength_adhesive,
#                             normal_shear_strength=normal_shear_strength)
#
#         db.session.add(adhesive)
#         db.session.commit()
#
# all_adhesive = Adhesive.query.all()
# for adhesive in all_adhesive:
#     db.session.delete(adhesive)

# random.randint(160, 180)
roughness = [0.8, 1.0, 1.6]
recomeded_speed = RecomededSpeed.query.all()

for rec in recomeded_speed:
    rec.Roughness = random.choice(roughness)
    db.session.commit()






