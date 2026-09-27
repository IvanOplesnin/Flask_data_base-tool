"""Add normalized insert geometry fields.

Revision ID: e5f6a7b8c9d0
Revises: d4f1a2b3c4d5
Create Date: 2026-09-27
"""

from alembic import op
import sqlalchemy as sa


revision = 'e5f6a7b8c9d0'
down_revision = 'd4f1a2b3c4d5'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('inserts') as batch_op:
        batch_op.add_column(sa.Column('geometry', sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column('rake_angle', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('relief_angle', sa.Float(), nullable=True))


def downgrade():
    with op.batch_alter_table('inserts') as batch_op:
        batch_op.drop_column('relief_angle')
        batch_op.drop_column('rake_angle')
        batch_op.drop_column('geometry')

