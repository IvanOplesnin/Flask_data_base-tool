from sqlalchemy import inspect
from my_app import create_app
from my_app.extensions import db

app = create_app()
from my_app.models import Material, Adhesive, Experiment, MaterialType

inspector = inspect(Material)
foreign_keys = inspector.relationships.items()
for name, relation in foreign_keys:
    print(f"Имя связи: {name}")
    print(f"Колонка: {relation.local_columns}")
    # print(f"Ссылаемая таблица: {relation.table}")
    print(f"Ссылаемые колонки: {relation.remote_side}\n")



