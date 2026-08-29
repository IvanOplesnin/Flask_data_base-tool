from my_app.extensions import db
from my_app.models import Material, MaterialType, Tool


def test_processing_page_filters_tools_by_processing_type(client, app):
    with app.app_context():
        material_type = MaterialType(name='Steel')
        material = Material(name='Steel 45', material_type=material_type)
        milling_tool = Tool(name='Milling cutter', processing_type='milling')
        turning_tool = Tool(name='Turning tool', processing_type='turning')
        db.session.add_all([material, milling_tool, turning_tool])
        db.session.commit()

    response = client.get('/processing/milling')

    assert response.status_code == 200
    assert b'Milling cutter' in response.data
    assert b'Turning tool' not in response.data
