import math
from io import BytesIO

from my_app.extensions import db
from my_app.models import Coating, Coefficient, Experiment, ImportBatch, Insert, Material, MaterialType, MillingGeometry, Tool, User
from my_app.services.cutting_calculations import calculate_milling, calculate_threading, calculate_turning
from my_app.services.experiment_import import csv_template


def create_user(username, password, role):
    user = User(username=username, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def create_catalog_data():
    material = Material(name='Сталь 45', material_type=MaterialType(name='Сталь'))
    tool = Tool(name='Фреза тестовая', material_tool='ВК10-ОМ', processing_type='milling')
    coating = Coating(name='TiN')
    db.session.add_all([material, tool, coating])
    db.session.commit()


def valid_csv():
    return (
        'external_id;material;tool;coating;spindle_speed;feed_table;depth_cut;width_cut;length_path;durability;data_experiment\n'
        'EXP-P1;Сталь 45;Фреза тестовая;TiN;1200;240;1;5;500;35.5;2026-09-27\n'
    )


def test_cutting_calculation_contracts_return_explicit_units():
    milling = calculate_milling(cutting_speed=100, diameter=10, number_teeth=4, feed_per_tooth=0.1, depth_cut=2, width_cut=5)
    assert math.isclose(milling.spindle_speed, 10000 / math.pi, rel_tol=1e-9)
    assert math.isclose(milling.feed_rate, (10000 / math.pi) * 0.4, rel_tol=1e-9)
    assert milling.extra['material_removal_rate_mm3_min'] > 0

    turning = calculate_turning(cutting_speed=80, diameter=40, feed_per_revolution=0.2)
    assert turning.processing_type == 'turning'
    assert turning.feed_rate > 0

    threading = calculate_threading(cutting_speed=20, diameter=10, pitch=1.5)
    assert math.isclose(threading.feed_rate, threading.spindle_speed * 1.5, rel_tol=1e-9)


def test_inner_turning_formulas_cover_roughness_force_power_and_passes():
    result = calculate_turning(
        cutting_speed=260,
        diameter=80,
        roughness=3.2,
        nose_radius=0.8,
        depth_cut=2,
        approach_angle=95,
        rake_angle=6,
        kc1=1675,
        mc=0.24,
        stock_allowance=5,
        length_cut=200,
    )
    assert math.isclose(result.feed_rate / result.spindle_speed, 0.251, rel_tol=0.02)
    assert math.isclose(result.spindle_speed, 260 * 1000 / (math.pi * 80), rel_tol=1e-9)
    assert 1000 < result.extra['cutting_force_n'] < 1250
    assert 4.5 < result.extra['cutting_power_kw'] < 5.1
    assert result.extra['passes'] == 3
    assert result.extra['total_time_min'] > result.extra['time_per_pass_min']


def test_inner_milling_formulas_cover_rctf_and_removal_rate():
    result = calculate_milling(
        cutting_speed=170,
        diameter=10,
        number_teeth=4,
        feed_per_tooth=0.08,
        depth_cut=3,
        width_cut=1,
    )
    assert math.isclose(result.spindle_speed, 170 * 1000 / (math.pi * 10), rel_tol=1e-9)
    assert result.extra['rctf'] > 1
    assert math.isclose(result.extra['material_removal_rate_cm3_min'], 3 * 1 * result.feed_rate / 1000, rel_tol=1e-9)


def test_coolant_reduces_speed_when_no_explicit_factor_is_given():
    emulsion = calculate_milling(
        cutting_speed=100, diameter=10, number_teeth=4, feed_per_tooth=0.1, coolant='emulsion'
    )
    dry = calculate_milling(
        cutting_speed=100, diameter=10, number_teeth=4, feed_per_tooth=0.1, coolant='none'
    )
    assert math.isclose(dry.cutting_speed, emulsion.cutting_speed * 0.8, rel_tol=1e-9)
    assert dry.spindle_speed < emulsion.spindle_speed


def test_calculation_api_passes_inner_formula_parameters(client):
    response = client.post('/api/calculate/turning', json={
        'cutting_speed': 260,
        'diameter': 80,
        'roughness': 3.2,
        'nose_radius': 0.8,
        'depth_cut': 2,
        'approach_angle': 95,
        'rake_angle': 6,
        'kc1': 1675,
        'mc': 0.24,
    })
    assert response.status_code == 200
    data = response.get_json()
    assert math.isclose(data['extra']['cutting_power_kw'], 4.7773, rel_tol=1e-3)


def test_cutting_reference_autofills_base_regimes_and_kienzle(client, app):
    with app.app_context():
        material = Material(name='Сталь 45', material_type=MaterialType(name='Сталь'))
        tool = Tool(name='Фреза со справочником', processing_type='milling')
        tool.milling_geometry = MillingGeometry(diameter=10, number_teeth=4, type_shank='cylindrical')
        coating = Coating(name='TiAlN')
        coefficient = Coefficient(
            material=material,
            tool=tool,
            coating=coating,
            cutting_force_coefficient=1,
            cutting_temperature_coefficient=1,
            durability_coefficient=1,
            kc1=1675,
            mc=0.24,
            base_cutting_speed=170,
            base_feed_per_tooth=0.08,
        )
        db.session.add_all([material, tool, coating, coefficient])
        db.session.commit()
        ids = (material.id, tool.id, coating.id)

    reference = client.get('/api/cutting-reference', query_string={
        'material_id': ids[0], 'tool_id': ids[1], 'coating_id': ids[2],
    })
    assert reference.status_code == 200
    assert reference.get_json()['reference']['kc1'] == 1675

    response = client.post('/api/calculate/milling', json={
        'material_id': ids[0], 'tool_id': ids[1], 'coating_id': ids[2],
        'diameter': 10, 'number_teeth': 4, 'depth_cut': 3, 'width_cut': 5,
    })
    assert response.status_code == 200
    data = response.get_json()
    assert math.isclose(data['cutting_speed'], 170, rel_tol=1e-9)
    assert math.isclose(data['extra']['feed_per_tooth'], 0.08, rel_tol=1e-9)
    assert data['extra']['cutting_power_kw'] > 0


def test_calculation_api_rejects_incomplete_data_and_returns_warning(client):
    response = client.post('/api/calculate/milling', json={'cutting_speed': 100})
    assert response.status_code == 400
    assert 'Диаметр' in response.get_json()['error']

    response = client.post('/api/calculate/turning', json={
        'cutting_speed': 80, 'diameter': 40, 'feed_per_revolution': 0.2,
        'material': 'Титан ВТ6', 'coolant': 'none',
    })
    assert response.status_code == 200
    assert response.get_json()['warnings']


def test_processing_page_does_not_keep_tool_from_another_operation(client, app):
    with app.app_context():
        material_type = MaterialType(name='Сталь')
        material = Material(name='40X', material_type=material_type)
        milling_tool = Tool(name='Фреза', processing_type='milling')
        turning_tool = Tool(name='Резец', processing_type='turning')
        coating = Coating(name='TiAlN')
        db.session.add_all([material, milling_tool, turning_tool, coating])
        db.session.commit()
        turning_tool_id = turning_tool.id
        milling_tool_id = milling_tool.id
    response = client.get(f'/expected_parameters?processing_type=turning&tool_id={milling_tool_id}')
    assert response.status_code == 200
    assert f'value="{milling_tool_id}" selected'.encode() not in response.data
    response = client.get(f'/expected_parameters?processing_type=milling&tool_id={turning_tool_id}')
    assert response.status_code == 200
    assert f'value="{turning_tool_id}" selected'.encode() not in response.data


def test_russian_csv_template_is_accepted():
    russian = csv_template('experiments', language='ru')
    assert 'Идентификатор эксперимента;Материал;Инструмент' in russian


def test_insert_catalog_has_add_form(client, app):
    app.config['AUTH_REQUIRED'] = True
    with app.app_context():
        create_user('writer', 'writer-password', 'writer')
    client.post('/login', data={'username': 'writer', 'password': 'writer-password'})
    response = client.post('/catalog/inserts/add', data={
        'name': 'CNMG120408', 'material': 'Т15К6', 'geometry': 'ромб 80°',
        'rake_angle': '6', 'relief_angle': '7',
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'CNMG120408' in response.data
    with app.app_context():
        insert = db.session.scalar(db.select(Insert).where(Insert.name == 'CNMG120408'))
        assert insert.geometry == 'ромб 80°'


def test_writer_import_is_hidden_until_admin_publishes(client, app):
    app.config['AUTH_REQUIRED'] = True
    with app.app_context():
        create_user('writer', 'writer-password', 'writer')
        create_user('admin', 'admin-password', 'admin')
        create_user('reader', 'reader-password', 'reader')
        create_catalog_data()

    client.post('/login', data={'username': 'writer', 'password': 'writer-password'})
    response = client.post('/imports/upload', data={
        'experiments_file': (BytesIO(valid_csv().encode()), 'experiments.csv'),
    }, content_type='multipart/form-data')
    assert response.status_code == 302
    with app.app_context():
        batch = db.session.scalar(db.select(ImportBatch))
        batch_id = batch.id
    client.post(f'/imports/{batch_id}/confirm')
    with app.app_context():
        experiment = db.session.scalar(db.select(Experiment).where(Experiment.external_id == 'EXP-P1'))
        assert experiment.publication_status == 'draft'
        assert db.session.get(ImportBatch, batch_id).review_status == 'pending'

    client.post('/logout')
    client.post('/login', data={'username': 'reader', 'password': 'reader-password'})
    assert b'EXP-P1' not in client.get('/experiments').data

    client.post('/logout')
    client.post('/login', data={'username': 'admin', 'password': 'admin-password'})
    response = client.post(f'/imports/{batch_id}/publish', follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        assert db.session.scalar(db.select(Experiment).where(Experiment.external_id == 'EXP-P1')).publication_status == 'published'
