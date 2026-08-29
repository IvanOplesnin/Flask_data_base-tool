import pytest

from my_app import create_app
from my_app.extensions import db


@pytest.fixture()
def app(tmp_path):
    database_path = tmp_path / 'test.sqlite'
    application = create_app({
        'TESTING': True,
        'AUTH_REQUIRED': False,
        'DISABLE_DASHBOARDS': True,
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'test-secret-key',
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{database_path}',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'IMPORT_UPLOAD_FOLDER': str(tmp_path / 'uploads'),
        'IMPORT_MAX_FILE_SIZE': 1024 * 1024,
    })

    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()
