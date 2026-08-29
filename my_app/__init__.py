"""Фабрика Flask-приложения."""

import os

from flask import Flask

from config import Config, TestConfig
from my_app.extensions import db, migrate


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

    from my_app.web import web_bp
    application.register_blueprint(web_bp)

    if not application.config.get('DISABLE_DASHBOARDS', False):
        from my_app.dashboards.cutting_parameters import create_dash
        from my_app.dashboards.wear import create_dash_wear, create_wear_on_info_experiments
        create_dash(application)
        create_dash_wear(application)
        create_wear_on_info_experiments(application)
    return application
