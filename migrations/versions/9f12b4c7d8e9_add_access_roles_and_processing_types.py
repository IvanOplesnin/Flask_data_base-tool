"""Add access roles and processing types.

Revision ID: 9f12b4c7d8e9
Revises: 268bfcbce998
Create Date: 2026-08-29
"""

from alembic import op
import sqlalchemy as sa


revision = '9f12b4c7d8e9'
down_revision = '268bfcbce998'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('tools') as batch_op:
        batch_op.add_column(sa.Column('processing_type', sa.String(length=32), nullable=True))
    op.execute("UPDATE tools SET processing_type = CASE "
               "WHEN tool_type = 'turning' THEN 'turning' "
               "WHEN tool_type IN ('drilling', 'drill') THEN 'threading' "
               "ELSE 'milling' END")
    with op.batch_alter_table('tools') as batch_op:
        batch_op.alter_column('processing_type', nullable=False, server_default='milling')
        batch_op.create_index('ix_tools_processing_type', ['processing_type'])

    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=64), nullable=False),
        sa.Column('password_hash', sa.String(length=256), nullable=False),
        sa.Column('role', sa.String(length=16), nullable=False, server_default='reader'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username'),
    )
    op.create_index('ix_users_username', 'users', ['username'])
    op.create_index('ix_users_role', 'users', ['role'])

    op.create_table(
        'tap_geometry',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tool_id', sa.Integer(), nullable=False),
        sa.Column('thread_standard', sa.String(length=64), nullable=False),
        sa.Column('thread_diameter', sa.Float(), nullable=False),
        sa.Column('pitch', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['tool_id'], ['tools.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tool_id'),
    )


def downgrade():
    op.drop_table('tap_geometry')
    op.drop_index('ix_users_role', table_name='users')
    op.drop_index('ix_users_username', table_name='users')
    op.drop_table('users')
    with op.batch_alter_table('tools') as batch_op:
        batch_op.drop_index('ix_tools_processing_type')
        batch_op.drop_column('processing_type')
