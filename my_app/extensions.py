"""Инициализация расширений Flask без привязки к конкретному приложению."""

from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'web.login'
login_manager.login_message = 'Войдите в систему, чтобы продолжить.'
