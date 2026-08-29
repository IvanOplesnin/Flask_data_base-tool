import os

from flask import Flask
from config import Config, TestConfig
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

app = Flask(__name__)
app.config.from_object(TestConfig if os.environ.get('FLASK_CONFIG') == 'testing' else Config)
db = SQLAlchemy(app)
migrate = Migrate(app, db)

from my_app import routes, models
from my_app.dash_pack import create_dash
from my_app.dash_wear_plot import create_dash_wear, create_wear_on_info_experiments

create_dash(app)
create_dash_wear(app)
create_wear_on_info_experiments(app)
