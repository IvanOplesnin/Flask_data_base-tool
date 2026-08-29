from io import BytesIO

from my_app.extensions import db
from my_app.models import Coating, Experiment, ImportBatch, Material, MaterialType, Tool, User, WearMeasurement


def create_user(username, password, role):
    user = User(username=username, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def create_catalog_data():
    material = Material(name='Steel 40X', material_type=MaterialType(name='Steel'))
    tool = Tool(name='End mill 10', material_tool='HSS', processing_type='milling')
    coating = Coating(name='TiN')
    db.session.add_all([material, tool, coating])
    db.session.commit()


def login_writer(client, app):
    app.config['AUTH_REQUIRED'] = True
    with app.app_context():
        create_user('writer', 'writer-password', 'writer')
        create_catalog_data()
    client.post('/login', data={'username': 'writer', 'password': 'writer-password'})


def valid_experiments_csv():
    return (
        'external_id;material;tool;coating;spindle_speed;feed_table;depth_cut;width_cut;length_path;durability;data_experiment\n'
        'EXP-001;Steel 40X;End mill 10;TiN;1200;240;1;5;500;35.5;2026-08-29\n'
    )


def valid_wear_csv():
    return 'external_id;length;wear\nEXP-001;100;0.03\nEXP-001;500;0.12\n'


def test_writer_can_preview_then_confirm_experiment_import(client, app):
    login_writer(client, app)

    response = client.post(
        '/imports/upload',
        data={
            'experiments_file': (BytesIO(valid_experiments_csv().encode()), 'experiments.csv'),
            'wear_file': (BytesIO(valid_wear_csv().encode()), 'wear_measurements.csv'),
        },
        content_type='multipart/form-data',
    )

    assert response.status_code == 302
    with app.app_context():
        import_batch = db.session.scalar(db.select(ImportBatch))
        assert import_batch.status == 'preview'
        assert import_batch.experiment_rows == 1
        assert import_batch.wear_rows == 2
        assert db.session.scalar(db.select(Experiment)) is None
        batch_id = import_batch.id

    response = client.post(f'/imports/{batch_id}/confirm', follow_redirects=True)

    assert response.status_code == 200
    assert 'Импорт завершён: экспериментов — 1, точек износа — 2.'.encode() in response.data
    with app.app_context():
        experiment = db.session.scalar(db.select(Experiment).where(Experiment.external_id == 'EXP-001'))
        assert experiment.import_batch_id == batch_id
        assert db.session.scalar(db.select(WearMeasurement).where(WearMeasurement.experiment_id == experiment.id))
        assert db.session.get(ImportBatch, batch_id).status == 'completed'


def test_invalid_import_is_not_confirmable_and_adds_no_data(client, app):
    login_writer(client, app)
    invalid_csv = valid_experiments_csv().replace('Steel 40X', 'Unknown steel')

    response = client.post(
        '/imports/upload',
        data={'experiments_file': (BytesIO(invalid_csv.encode()), 'experiments.csv')},
        content_type='multipart/form-data',
        follow_redirects=True,
    )

    assert 'материал «Unknown steel» не найден.'.encode() in response.data
    with app.app_context():
        import_batch = db.session.scalar(db.select(ImportBatch))
        assert import_batch.status == 'invalid'
        assert db.session.scalar(db.select(Experiment)) is None


def test_reader_cannot_open_import_pages(client, app):
    app.config['AUTH_REQUIRED'] = True
    with app.app_context():
        create_user('reader', 'reader-password', 'reader')

    client.post('/login', data={'username': 'reader', 'password': 'reader-password'})

    assert client.get('/imports').status_code == 403


def test_import_templates_are_available_to_writer(client, app):
    login_writer(client, app)

    response = client.get('/imports/templates/experiments')

    assert response.status_code == 200
    assert b'external_id;material;tool' in response.data


def test_writer_cannot_view_another_writers_import(client, app):
    app.config['AUTH_REQUIRED'] = True
    with app.app_context():
        owner = create_user('owner', 'owner-password', 'writer')
        create_user('other-writer', 'writer-password', 'writer')
        import_batch = ImportBatch(
            uploader_id=owner.id,
            status='invalid',
            experiments_filename='experiments.csv',
            experiments_path='/private/imports/experiments.csv',
            checksum='a' * 64,
        )
        db.session.add(import_batch)
        db.session.commit()
        batch_id = import_batch.id

    client.post('/login', data={'username': 'other-writer', 'password': 'writer-password'})

    assert client.get(f'/imports/{batch_id}').status_code == 403
