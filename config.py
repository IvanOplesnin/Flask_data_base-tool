import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(basedir, 'me_app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    AUTH_REQUIRED = True
    IMPORT_UPLOAD_FOLDER = os.environ.get('IMPORT_UPLOAD_FOLDER') or os.path.join(basedir, 'uploads', 'imports')
    IMPORT_MAX_FILE_SIZE = 10 * 1024 * 1024
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024


class TestConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or 'sqlite:///' + os.path.join(basedir, 'me_app_test.db')
    TESTING = True
    AUTH_REQUIRED = False
