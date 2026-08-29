"""Фабрика Flask-приложения."""

import os

import click
from flask import Flask

from config import Config, TestConfig
from my_app.extensions import db, login_manager, migrate


def create_app(config_object=None):
    """Создаёт настроенное приложение без глобальных побочных эффектов в тестах."""
    application = Flask(__name__)
    if config_object is None:
        config_object = TestConfig if os.environ.get('FLASK_CONFIG') == 'testing' else Config
    if isinstance(config_object, dict):
        application.config.from_mapping(config_object)
    else:
        application.config.from_object(config_object)

    db.init_app(application)
    migrate.init_app(application, db)
    login_manager.init_app(application)

    from my_app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @application.cli.command('create-admin')
    @click.option('--username', prompt=True)
    @click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True)
    def create_admin(username, password):
        """Создаёт или обновляет учётную запись администратора."""
        user = db.session.scalar(db.select(User).where(User.username == username))
        if user is None:
            user = User(username=username)
            db.session.add(user)
        user.role = 'admin'
        user.set_password(password)
        db.session.commit()
        click.echo(f'Администратор {username} готов.')

    from my_app.web import web_bp
    application.register_blueprint(web_bp)

    if not application.config.get('DISABLE_DASHBOARDS', False) and not os.environ.get('FLASK_SKIP_DASHBOARDS'):
        from my_app.dashboards.cutting_parameters import create_dash
        from my_app.dashboards.wear import create_dash_wear, create_wear_on_info_experiments
        create_dash(application)
        create_dash_wear(application)
        create_wear_on_info_experiments(application)
    return application
