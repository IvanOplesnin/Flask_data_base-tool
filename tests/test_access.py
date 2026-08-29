from my_app.extensions import db
from my_app.models import User


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


def test_admin_can_delete_writer(client, app):
    app.config['AUTH_REQUIRED'] = True
    with app.app_context():
        create_user('admin', 'admin-password', 'admin')
        writer = create_user('writer', 'writer-password', 'writer')
        writer_id = writer.id

    client.post('/login', data={'username': 'admin', 'password': 'admin-password'})
    response = client.post(f'/users/{writer_id}/delete', follow_redirects=True)

    assert response.status_code == 200
    assert 'Пользователь «writer» удалён.'.encode() in response.data
    with app.app_context():
        assert db.session.get(User, writer_id) is None


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
