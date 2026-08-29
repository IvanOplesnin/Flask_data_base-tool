from sqlalchemy import inspect
from my_app import db, app
from my_app.models import Materials, Adhesive, Experiments, MaterialType

inspector = inspect(Materials)
foreign_keys = inspector.relationships.items()
for name, relation in foreign_keys:
    print(f"Имя связи: {name}")
    print(f"Колонка: {relation.local_columns}")
    # print(f"Ссылаемая таблица: {relation.table}")
    print(f"Ссылаемые колонки: {relation.remote_side}\n")



