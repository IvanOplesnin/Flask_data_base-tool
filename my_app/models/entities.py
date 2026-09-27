import math
from datetime import datetime

import sqlalchemy as sa
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from my_app.extensions import db


class Material(db.Model):
    __tablename__ = 'materials'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(sa.String(64), index=True, unique=True)
    prop_physics = db.Column(sa.String(64))
    structure = db.Column(sa.Text)
    properties = db.Column(sa.String(120))
    gost = db.Column(sa.String(64))
    type_id = db.Column(db.Integer, db.ForeignKey('material_type.id'), nullable=False)

    experiments = db.relationship('Experiment', back_populates='material')
    recommendations = db.relationship('RecommendationParameter', back_populates='material')
    adhesives = db.relationship('Adhesive', back_populates='material')
    material_type = db.relationship('MaterialType', back_populates='materials')

    def __repr__(self):
        return '<Material {}>'.format(self.name)


class Tool(db.Model):
    __tablename__ = 'tools'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(sa.String(64), index=True, unique=True)
    name_easy = db.Column(sa.String(64), default='')
    tool_type = db.Column(sa.String(64))  # 'milling', 'turning', 'drill', 'drill_center'
    processing_type = db.Column(sa.String(32), nullable=False, default='milling', index=True)
    material_tool = db.Column(sa.String(64))
    is_indexable = db.Column(sa.Boolean, default=False)

    milling_geometry = db.relationship('MillingGeometry', back_populates='tool', uselist=False)
    turning_geometry = db.relationship('TurningGeometry', back_populates='tool', uselist=False)
    drill_geometry = db.relationship('DrillGeometry', back_populates='tool', uselist=False)
    tap_geometry = db.relationship('TapGeometry', back_populates='tool', uselist=False)
    insert = db.relationship('Insert', back_populates='tool')

    experiments = db.relationship('Experiment', back_populates='tool')
    recommendations = db.relationship('RecommendationParameter', back_populates='tool')

    def __repr__(self):
        return f'<Tool {self.name}>'


class MillingGeometry(db.Model):
    __tablename__ = 'milling_geometry'

    id = db.Column(db.Integer, primary_key=True)
    tool_id = db.Column(db.Integer, db.ForeignKey('tools.id'), unique=True, nullable=False)

    type_milling = db.Column(sa.String(64))
    diameter = db.Column(sa.Float)
    diameter_shank = db.Column(sa.Float)
    length = db.Column(sa.Float)
    length_work = db.Column(sa.Float)
    number_teeth = db.Column(sa.Integer)
    type_shank = db.Column(sa.String(64))  # cylindrical, weldone
    spiral_angle = db.Column(sa.Float)

    tool = db.relationship('Tool', back_populates='milling_geometry')


class TurningGeometry(db.Model):
    __tablename__ = 'turning_geometry'

    id = db.Column(db.Integer, primary_key=True)
    tool_id = db.Column(db.Integer, db.ForeignKey('tools.id'), unique=True, nullable=False)

    turning_type = db.Column(sa.String(64))
    front_angle = db.Column(sa.Float)
    main_rear_angle = db.Column(sa.Float)
    sharpening_angle = db.Column(sa.Float)
    cutting_angle = db.Column(sa.Float)
    aux_rear_angle = db.Column(sa.Float)

    tool = db.relationship('Tool', back_populates='turning_geometry')


class DrillGeometry(db.Model):
    __tablename__ = 'drill_geometry'

    id = db.Column(db.Integer, primary_key=True)
    tool_id = db.Column(db.Integer, db.ForeignKey('tools.id'), unique=True, nullable=False)

    drill_type = db.Column(sa.String(64))
    diameter = db.Column(sa.Float)

    top_angle = db.Column(sa.Float)
    screw_angle = db.Column(sa.Float)
    front_angle = db.Column(sa.Float)
    rear_angle = db.Column(sa.Float)
    transverse_edge_angle = db.Column(sa.Float)

    tool = db.relationship('Tool', back_populates='drill_geometry')


class TapGeometry(db.Model):
    __tablename__ = 'tap_geometry'

    id = db.Column(db.Integer, primary_key=True)
    tool_id = db.Column(db.Integer, db.ForeignKey('tools.id'), unique=True, nullable=False)
    thread_standard = db.Column(sa.String(64), nullable=False)
    thread_diameter = db.Column(sa.Float, nullable=False)
    pitch = db.Column(sa.Float, nullable=False)

    tool = db.relationship('Tool', back_populates='tap_geometry')


class Insert(db.Model):
    __tablename__ = 'inserts'

    id = db.Column(db.Integer, primary_key=True)
    tool_id = db.Column(db.Integer, db.ForeignKey('tools.id'))
    name = db.Column(sa.String(64))
    material = db.Column(sa.String(64))
    geometry = db.Column(sa.String(128))
    rake_angle = db.Column(sa.Float)
    relief_angle = db.Column(sa.Float)

    tool = db.relationship('Tool', back_populates='insert')

    def __repr__(self):
        return f'<Insert {self.id} for Tool {self.tool.name}>'


class Coating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(sa.String(64), index=True, unique=True)
    material_coating = db.Column(sa.String(64))
    color_coating = db.Column(sa.String(32))
    type_application = db.Column(sa.String(64))
    max_thickness = db.Column(sa.String(32))
    nano_hardness = db.Column(sa.String(32))
    temperature_resistance = db.Column(sa.Float)
    coefficient_friction = db.Column(sa.Float)

    experiments = db.relationship('Experiment', back_populates='coating')
    recommendations = db.relationship('RecommendationParameter', back_populates='coating')
    adhesives = db.relationship('Adhesive', back_populates='coating')

    def __repr__(self):
        return '<coating {}>'.format(self.id)


class CsvFile(db.Model):
    __tablename__ = 'csv_files'

    id = db.Column(db.Integer, primary_key=True)
    filename_strength = db.Column(sa.String(128), nullable=False, unique=True)
    filename_temperature = db.Column(sa.String(128), nullable=False, unique=True)
    path = db.Column(sa.String(256), nullable=False, unique=True)
    path_graphic_s = db.Column(sa.String(256))
    path_graphic_t = db.Column(sa.String(256))

    experiment = db.relationship('Experiment', back_populates='csv_file', uselist=False)


class WearMeasurement(db.Model):
    __tablename__ = 'wear_tables'

    id = db.Column(db.Integer, primary_key=True)
    experiment_id = db.Column(db.Integer, db.ForeignKey('experiments.id'), nullable=False)
    length = db.Column(db.Float)
    wear = db.Column(db.Float)

    experiment = db.relationship('Experiment', back_populates='wear_tables')

    __table_args__ = (
        sa.UniqueConstraint('experiment_id', 'length', 'wear', name='unique_wear_table'),
    )

    @property
    def time_(self):
        return self.length / self.experiment.feed_table


class Experiment(db.Model):
    __tablename__ = 'experiments'

    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(db.Integer, db.ForeignKey('materials.id'))
    tool_id = db.Column(db.Integer, db.ForeignKey('tools.id'))
    coating_id = db.Column(db.Integer, db.ForeignKey('coating.id'))
    spindle_speed = db.Column(db.Float)
    feed_table = db.Column(db.Float)
    depth_cut = db.Column(db.Float)
    width_cut = db.Column(db.Float)
    length_path = db.Column(db.Float)
    durability = db.Column(db.Float)
    csv_id = db.Column(db.Integer, db.ForeignKey(CsvFile.id))
    external_id = db.Column(sa.String(64), unique=True, index=True)
    import_batch_id = db.Column(db.Integer, db.ForeignKey('import_batches.id', ondelete='SET NULL'))
    # Ручные эксперименты считаются опубликованными. Импорт писателя сначала
    # получает статус draft и становится виден читателям только после решения
    # администратора.
    publication_status = db.Column(sa.String(16), nullable=False, default='published', index=True)
    data_experiment = db.Column(db.Date)
    date_recording = db.Column(db.DateTime, default=datetime.utcnow)

    tool = db.relationship('Tool', foreign_keys=[tool_id], back_populates='experiments')
    coating = db.relationship('Coating', foreign_keys=[coating_id], back_populates='experiments')
    material = db.relationship('Material', foreign_keys=[material_id], back_populates='experiments')
    csv_file = db.relationship('CsvFile', foreign_keys=[csv_id], back_populates='experiment', uselist=False)
    import_batch = db.relationship('ImportBatch', back_populates='experiments')
    wear_tables = db.relationship('WearMeasurement', back_populates='experiment')

    @property
    def cutter_speed(self):
        if self.tool:
            d = self.tool.milling_geometry.diameter
            return math.pi * d * self.spindle_speed / 1000
        else:
            return None

    @property
    def feed_of_teeth(self):
        if self.tool:
            z = self.tool.milling_geometry.number_teeth
            return self.feed_table / (z * self.spindle_speed)

    def __repr__(self):
        return '<Experiment {}>'.format(self.id)


class ImportBatch(db.Model):
    """Журнал одной попытки импорта файлов с результатами экспериментов."""

    __tablename__ = 'import_batches'

    id = db.Column(db.Integer, primary_key=True)
    uploader_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'))
    status = db.Column(sa.String(16), nullable=False, default='preview', index=True)
    review_status = db.Column(sa.String(16), nullable=False, default='published', index=True)
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'))
    reviewed_at = db.Column(db.DateTime)
    review_comment = db.Column(sa.Text)
    experiments_filename = db.Column(sa.String(255), nullable=False)
    wear_filename = db.Column(sa.String(255))
    experiments_path = db.Column(sa.String(512), nullable=False, unique=True)
    wear_path = db.Column(sa.String(512), unique=True)
    checksum = db.Column(sa.String(64), nullable=False)
    experiment_rows = db.Column(db.Integer, nullable=False, default=0)
    wear_rows = db.Column(db.Integer, nullable=False, default=0)
    imported_experiments = db.Column(db.Integer, nullable=False, default=0)
    imported_wear = db.Column(db.Integer, nullable=False, default=0)
    error_count = db.Column(db.Integer, nullable=False, default=0)
    errors_summary = db.Column(sa.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)

    uploaded_by = db.relationship('User', foreign_keys=[uploader_id], back_populates='import_batches')
    reviewed_by = db.relationship('User', foreign_keys=[reviewed_by_id])
    experiments = db.relationship('Experiment', back_populates='import_batch')


class RecommendationParameter(db.Model):
    __tablename__ = 'recommendation_parameters'

    __tablename__ = 'recommendation_parameters'

    material_id = db.Column(db.Integer, db.ForeignKey('materials.id'), primary_key=True, nullable=False)
    tool_id = db.Column(db.Integer, db.ForeignKey('tools.id'), primary_key=True, nullable=False)
    coating_id = db.Column(db.Integer, db.ForeignKey('coating.id'), primary_key=True, nullable=False)
    spindle_speed = db.Column(db.Integer)
    feed_table = db.Column(db.Float)
    roughness = db.Column(db.Float)
    hardening = db.Column(db.Float)
    micro_hardness = db.Column(db.Float)

    tool = db.relationship('Tool', foreign_keys=[tool_id], back_populates='recommendations')
    coating = db.relationship('Coating', foreign_keys=[coating_id], back_populates='recommendations')
    material = db.relationship('Material', foreign_keys=[material_id], back_populates='recommendations')

    @property
    def cutter_speed(self):
        if self.tool:
            d = self.tool.milling_geometry.diameter
            return math.pi * d * self.spindle_speed / 1000
        else:
            return None

    @property
    def feed_of_teeth(self):
        if self.tool:
            z = self.tool.milling_geometry.number_teeth
            return self.feed_table / (z * self.spindle_speed)

    @property
    def coefficients(self):
        return Coefficient.query.filter_by(
            material_id=self.material_id,
            tool_id=self.tool_id,
            coating_id=self.coating_id
        ).first()

    @property
    def Fz(self):
        coefficient = self.coefficients.cutting_force_coefficient
        return round(coefficient * (self.cutter_speed) ** -0.12 * (self.feed_of_teeth) ** 0.95, 2)

    @property
    def temperature(self):
        coefficient = self.coefficients.cutting_temperature_coefficient
        return round(coefficient * (self.cutter_speed) ** 0.4 * (self.feed_of_teeth) ** 0.24, 2)

    @property
    def durability_(self):
        coefficient = self.coefficients.durability_coefficient
        if coefficient:
            b_life = -0.15 if 'ВТ' in self.material.name else -0.1
            durability = coefficient * (self.cutter_speed) ** -0.2 * (self.feed_of_teeth) ** b_life
            return round(durability, 2)
        else:
            return 'Не найден коэффициент'


class Adhesive(db.Model):
    __tablename__ = 'adhesive'

    material_id = db.Column(db.Integer, db.ForeignKey('materials.id'), primary_key=True, nullable=False)
    coating_id = db.Column(db.Integer, db.ForeignKey('coating.id'), primary_key=True, nullable=False)
    temperature = db.Column(sa.Integer, nullable=False, primary_key=True)
    bond_strength_adhesive = db.Column(sa.Float, nullable=False)
    normal_shear_strength = db.Column(sa.Float, nullable=False)

    material = db.relationship('Material', foreign_keys=[material_id], back_populates='adhesives')
    coating = db.relationship('Coating', foreign_keys=[coating_id], back_populates='adhesives')

    @property
    def coefficient_shear(self):
        return self.bond_strength_adhesive / self.normal_shear_strength


class Coefficient(db.Model):
    __tablename__ = 'coefficients'

    __tablename__ = 'coefficients'

    material_id = db.Column(db.Integer, db.ForeignKey('materials.id'), primary_key=True, nullable=False)
    coating_id = db.Column(db.Integer, db.ForeignKey('coating.id'), primary_key=True, nullable=False)
    tool_id = db.Column(db.Integer, db.ForeignKey('tools.id'), primary_key=True, nullable=False)

    cutting_force_coefficient = db.Column(db.Float, nullable=False)
    cutting_temperature_coefficient = db.Column(db.Float, nullable=False)
    durability_coefficient = db.Column(db.Float, nullable=False)

    # Коэффициенты и базовые режимы для модели Kienzle/Victor. Они отделены
    # от исторических эмпирических коэффициентов выше: смешивать эти модели
    # в одном расчёте нельзя.
    kc1 = db.Column(db.Float)
    mc = db.Column(db.Float)
    base_cutting_speed = db.Column(db.Float)
    base_feed_per_tooth = db.Column(db.Float)
    base_feed_per_revolution = db.Column(db.Float)

    material = db.relationship('Material', backref=db.backref('coefficients', lazy='dynamic'))
    tool = db.relationship('Tool', backref=db.backref('coefficients', lazy='dynamic'))
    coating = db.relationship('Coating', backref=db.backref('coefficients', lazy='dynamic'))

    def __repr__(self):
        return (f'{self.material.name}-'
                f'{self.tool.name}-'
                f'{self.coating.name}-'
                f'{self.cutting_force_coefficient};'
                f'{self.cutting_temperature_coefficient};'
                f'{self.durability_coefficient}')


class MaterialType(db.Model):
    __tablename__ = 'material_type'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(sa.String(64), unique=True, nullable=False)  # Название типа материала
    materials = db.relationship('Material', back_populates='material_type')  # Связь с материалами

    def __repr__(self):
        return f'<MaterialType {self.name}>'


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(sa.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(sa.String(256), nullable=False)
    role = db.Column(sa.String(16), nullable=False, default='reader', index=True)
    import_batches = db.relationship(
        'ImportBatch',
        foreign_keys='ImportBatch.uploader_id',
        back_populates='uploaded_by',
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)
