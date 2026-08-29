from my_app.extensions import db
from my_app.models import Material, MaterialType


def test_material_uses_existing_plural_table_and_relation(app):
    with app.app_context():
        material_type = MaterialType(name='Steel')
        material = Material(name='40X', material_type=material_type)
        db.session.add(material)
        db.session.commit()

        stored_material = db.session.scalar(db.select(Material).where(Material.name == '40X'))

        assert stored_material.material_type.name == 'Steel'
        assert Material.__tablename__ == 'materials'
