import math
from datetime import datetime

import sqlalchemy as sa

from my_app import db


class Materials(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(sa.String(64), index=True, unique=True)
    prop_physics = db.Column(sa.String(64))
    structure = db.Column(sa.Text)
    properties = db.Column(sa.String(120))
    gost = db.Column(sa.String(64))
    type_id = db.Column(db.Integer, db.ForeignKey('material_type.id'), nullable=False)

    experiments = db.relationship('Experiments', back_populates='material')
    recommendations = db.relationship('RecommendationParameters', back_populates='material')
    adhesives = db.relationship('Adhesive', back_populates='material')
    material_type = db.relationship('MaterialType', back_populates='materials')

    def __repr__(self):
        return '<Materials {}>'.format(self.name)


class Tools(db.Model):
    __tablename__ = 'tools'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(sa.String(64), index=True, unique=True)
    name_easy = db.Column(sa.String(64), default='')
    tool_type = db.Column(sa.String(64))  # 'milling', 'turning', 'drill', 'drill_center'
    material_tool = db.Column(sa.String(64))
    is_indexable = db.Column(sa.Boolean, default=False)

    milling_geometry = db.relationship('MillingGeometry', back_populates='tool', uselist=False)
    turning_geometry = db.relationship('TurningGeometry', back_populates='tool', uselist=False)
    drill_geometry = db.relationship('DrillGeometry', back_populates='tool', uselist=False)
    insert = db.relationship('Insert', back_populates='tool')

    experiments = db.relationship('Experiments', back_populates='tool')
    recommendations = db.relationship('RecommendationParameters', back_populates='tool')

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

    tool = db.relationship('Tools', back_populates='milling_geometry')


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

    tool = db.relationship('Tools', back_populates='turning_geometry')


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

    tool = db.relationship('Tools', back_populates='drill_geometry')


class Insert(db.Model):
    __tablename__ = 'inserts'

    id = db.Column(db.Integer, primary_key=True)
    tool_id = db.Column(db.Integer, db.ForeignKey('tools.id'))
    name = db.Column(sa.String(64))
    material = db.Column(sa.String(64))

    tool = db.relationship('Tools', back_populates='insert')

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

    experiments = db.relationship('Experiments', back_populates='coating')
    recommendations = db.relationship('RecommendationParameters', back_populates='coating')
    adhesives = db.relationship('Adhesive', back_populates='coating')

    def __repr__(self):
        return '<coating {}>'.format(self.id)


class CsvFiles(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename_strength = db.Column(sa.String(128), nullable=False, unique=True)
    filename_temperature = db.Column(sa.String(128), nullable=False, unique=True)
    path = db.Column(sa.String(256), nullable=False, unique=True)
    path_graphic_s = db.Column(sa.String(256))
    path_graphic_t = db.Column(sa.String(256))

    experiment = db.relationship('Experiments', back_populates='csv_file', uselist=False)


class WearTables(db.Model):
    __tablename__ = 'wear_tables'

    id = db.Column(db.Integer, primary_key=True)
    experiment_id = db.Column(db.Integer, db.ForeignKey('experiments.id'), nullable=False)
    length = db.Column(db.Float)
    wear = db.Column(db.Float)

    experiment = db.relationship('Experiments', back_populates='wear_tables')

    __table_args__ = (
        sa.UniqueConstraint('experiment_id', 'length', 'wear', name='unique_wear_table'),
    )

    @property
    def time_(self):
        return self.length / self.experiment.feed_table


class Experiments(db.Model):
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
    csv_id = db.Column(db.Integer, db.ForeignKey(CsvFiles.id))
    data_experiment = db.Column(db.Date)
    date_recording = db.Column(db.DateTime, default=datetime.utcnow)

    tool = db.relationship('Tools', foreign_keys=[tool_id], back_populates='experiments')
    coating = db.relationship('Coating', foreign_keys=[coating_id], back_populates='experiments')
    material = db.relationship('Materials', foreign_keys=[material_id], back_populates='experiments')
    csv_file = db.relationship('CsvFiles', foreign_keys=[csv_id], back_populates='experiment', uselist=False)
    wear_tables = db.relationship('WearTables', back_populates='experiment')

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
        return '<Experiments {}>'.format(self.id)


class RecommendationParameters(db.Model):
    __tablename__ = 'recommendation_parameters'

    material_id = db.Column(db.Integer, db.ForeignKey('materials.id'), primary_key=True, nullable=False)
    tool_id = db.Column(db.Integer, db.ForeignKey('tools.id'), primary_key=True, nullable=False)
    coating_id = db.Column(db.Integer, db.ForeignKey('coating.id'), primary_key=True, nullable=False)
    spindle_speed = db.Column(db.Integer)
    feed_table = db.Column(db.Float)
    roughness = db.Column(db.Float)
    hardening = db.Column(db.Float)
    micro_hardness = db.Column(db.Float)

    tool = db.relationship('Tools', foreign_keys=[tool_id], back_populates='recommendations')
    coating = db.relationship('Coating', foreign_keys=[coating_id], back_populates='recommendations')
    material = db.relationship('Materials', foreign_keys=[material_id], back_populates='recommendations')

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
        return Coefficients.query.filter_by(
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

    material = db.relationship('Materials', foreign_keys=[material_id], back_populates='adhesives')
    coating = db.relationship('Coating', foreign_keys=[coating_id], back_populates='adhesives')

    @property
    def coefficient_shear(self):
        return self.bond_strength_adhesive / self.normal_shear_strength


class Coefficients(db.Model):
    __tablename__ = 'coefficients'

    material_id = db.Column(db.Integer, db.ForeignKey('materials.id'), primary_key=True, nullable=False)
    coating_id = db.Column(db.Integer, db.ForeignKey('coating.id'), primary_key=True, nullable=False)
    tool_id = db.Column(db.Integer, db.ForeignKey('tools.id'), primary_key=True, nullable=False)

    cutting_force_coefficient = db.Column(db.Float, nullable=False)
    cutting_temperature_coefficient = db.Column(db.Float, nullable=False)
    durability_coefficient = db.Column(db.Float, nullable=False)

    material = db.relationship('Materials', backref=db.backref('coefficients', lazy='dynamic'))
    tool = db.relationship('Tools', backref=db.backref('coefficients', lazy='dynamic'))
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
    materials = db.relationship('Materials', back_populates='material_type')  # Связь с материалами

    def __repr__(self):
        return f'<MaterialType {self.name}>'
