from my_app.extensions import db
from my_app.models import Material, MaterialType, Tool, User


def create_user(username, password, role):
    user = User(username=username, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def test_login_and_role_restrictions(client, app):
    app.config['AUTH_REQUIRED'] = True
    with app.app_context():
        create_user('reader', 'reader-password', 'reader')

    assert client.get('/').status_code == 302
    response = client.post('/login', data={'username': 'reader', 'password': 'reader-password'}, follow_redirects=True)
    assert response.status_code == 200
    assert client.get('/add').status_code == 403


def test_admin_can_open_user_management(client, app):
    app.config['AUTH_REQUIRED'] = True
    with app.app_context():
        create_user('admin', 'admin-password', 'admin')

    client.post('/login', data={'username': 'admin', 'password': 'admin-password'})
    assert client.get('/users').status_code == 200


def test_login_displays_invalid_credentials_message(client, app):
    app.config['AUTH_REQUIRED'] = True
    with app.app_context():
        create_user('admin', 'admin-password', 'admin')

    response = client.post('/login', data={'username': 'admin', 'password': 'wrong-password'}, follow_redirects=True)

    assert 'Неверный логин или пароль.'.encode() in response.data


def test_admin_can_delete_users_with_any_role(client, app):
    app.config['AUTH_REQUIRED'] = True
    with app.app_context():
        create_user('root-admin', 'admin-password', 'admin')
        users_to_delete = [
            ('second-admin', create_user('second-admin', 'admin-password', 'admin')),
            ('writer', create_user('writer', 'writer-password', 'writer')),
            ('reader', create_user('reader', 'reader-password', 'reader')),
        ]
        user_ids = [user.id for _, user in users_to_delete]

    client.post('/login', data={'username': 'root-admin', 'password': 'admin-password'})
    for username, user in users_to_delete:
        user_id = user.id
        response = client.post(f'/users/{user_id}/delete', follow_redirects=True)
        assert response.status_code == 200
        assert f'Пользователь «{username}» удалён.'.encode() in response.data

    with app.app_context():
        assert all(db.session.get(User, user_id) is None for user_id in user_ids)


def test_writer_can_delete_material(client, app):
    app.config['AUTH_REQUIRED'] = True
    with app.app_context():
        create_user('writer', 'writer-password', 'writer')
        material = Material(name='40X', material_type=MaterialType(name='Сталь'))
        db.session.add(material)
        db.session.commit()
        material_id = material.id

    client.post('/login', data={'username': 'writer', 'password': 'writer-password'})
    response = client.post(f'/materials/{material_id}/delete', follow_redirects=True)

    assert response.status_code == 200
    assert 'Материал удалён.'.encode() in response.data
    with app.app_context():
        assert db.session.get(Material, material_id) is None


def test_reader_cannot_delete_material(client, app):
    app.config['AUTH_REQUIRED'] = True
    with app.app_context():
        create_user('reader', 'reader-password', 'reader')
        material = Material(name='09Г2С', material_type=MaterialType(name='Сталь'))
        db.session.add(material)
        db.session.commit()
        material_id = material.id

    client.post('/login', data={'username': 'reader', 'password': 'reader-password'})

    assert client.post(f'/materials/{material_id}/delete').status_code == 403


def test_writer_can_add_tap(client, app):
    app.config['AUTH_REQUIRED'] = True
    with app.app_context():
        create_user('writer', 'writer-password', 'writer')

    client.post('/login', data={'username': 'writer', 'password': 'writer-password'})
    response = client.post('/catalog/taps/add', data={
        'name': 'M10 tap',
        'material_tool': 'HSS',
        'thread_standard': 'M10',
        'thread_diameter': '10',
        'pitch': '1.5',
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b'M10 tap' in response.data


def test_writer_can_add_and_manage_tap_from_main_tool_form(client, app):
    app.config['AUTH_REQUIRED'] = True
    with app.app_context():
        create_user('writer', 'writer-password', 'writer')

    client.post('/login', data={'username': 'writer', 'password': 'writer-password'})
    assert 'Метчик (резьбонарезание)'.encode() in client.get('/add').data

    response = client.post('/add', data={
        'name': 'M12 machine tap',
        'name_easy': 'Метчик M12',
        'material_tool': 'HSS-Co',
        'thread_standard': 'M12',
        'thread_diameter': '12',
        'pitch': '1.75',
        'submit': 'Добавить метчик',
    }, follow_redirects=True)
    assert response.status_code == 200

    with app.app_context():
        tap = db.session.scalar(db.select(Tool).where(Tool.name == 'M12 machine tap'))
        assert tap.tool_type == 'tap'
        assert tap.processing_type == 'threading'
        assert tap.tap_geometry.thread_standard == 'M12'
        tap_id = tap.id

    assert b'M12 machine tap' in client.get('/tools?tool_type=tap').data
    assert b'M12 machine tap' in client.get('/processing/threading').data
    assert 'Геометрия метчика'.encode() in client.get(f'/tool/{tap_id}/info').data

    response = client.post(f'/tool/{tap_id}/update', data={
        'name': 'M12 machine tap',
        'name_easy': 'Метчик M12 x 1.5',
        'material_tool': 'HSS-Co',
        'thread_standard': 'M12x1.5',
        'thread_diameter': '12',
        'pitch': '1.5',
        'submit': 'Добавить метчик',
    }, follow_redirects=True)
    assert response.status_code == 200

    with app.app_context():
        tap = db.session.get(Tool, tap_id)
        assert tap.name_easy == 'Метчик M12 x 1.5'
        assert tap.tap_geometry.thread_standard == 'M12x1.5'
        assert tap.tap_geometry.pitch == 1.5
