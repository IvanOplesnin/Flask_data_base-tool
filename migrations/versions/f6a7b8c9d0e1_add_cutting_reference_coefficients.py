"""Add Kienzle coefficients and base cutting regimes.

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-09-27
"""

from alembic import op
import sqlalchemy as sa


revision = 'f6a7b8c9d0e1'
down_revision = 'e5f6a7b8c9d0'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('coefficients') as batch_op:
        batch_op.add_column(sa.Column('kc1', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('mc', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('base_cutting_speed', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('base_feed_per_tooth', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('base_feed_per_revolution', sa.Float(), nullable=True))

    # Первичные значения для уже существующих материалов из групп, которые
    # есть в справочнике проекта. Значения можно уточнить для конкретной
    # марки/инструмента через новые поля коэффициента.
    op.execute(
        """
        UPDATE coefficients
        SET kc1 = 1400, mc = 0.23
        WHERE kc1 IS NULL
          AND material_id IN (
              SELECT materials.id
              FROM materials
              JOIN material_type ON material_type.id = materials.type_id
              WHERE material_type.name LIKE '%Титан%'
                 OR materials.name LIKE 'ВТ%'
          )
        """
    )
    op.execute(
        """
        UPDATE coefficients
        SET kc1 = 2150, mc = 0.21
        WHERE kc1 IS NULL
          AND material_id IN (
              SELECT materials.id
              FROM materials
              JOIN material_type ON material_type.id = materials.type_id
              WHERE material_type.name LIKE '%Хромоникел%'
                 OR material_type.name LIKE '%Нержав%'
          )
        """
    )


def downgrade():
    with op.batch_alter_table('coefficients') as batch_op:
        batch_op.drop_column('base_feed_per_revolution')
        batch_op.drop_column('base_feed_per_tooth')
        batch_op.drop_column('base_cutting_speed')
        batch_op.drop_column('mc')
        batch_op.drop_column('kc1')
