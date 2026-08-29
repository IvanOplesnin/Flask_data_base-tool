"""Add experiment import batches.

Revision ID: b8d3a1f4e6c2
Revises: 9f12b4c7d8e9
Create Date: 2026-08-29
"""

from alembic import op
import sqlalchemy as sa


revision = 'b8d3a1f4e6c2'
down_revision = '9f12b4c7d8e9'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'import_batches',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('uploader_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('experiments_filename', sa.String(length=255), nullable=False),
        sa.Column('wear_filename', sa.String(length=255), nullable=True),
        sa.Column('experiments_path', sa.String(length=512), nullable=False),
        sa.Column('wear_path', sa.String(length=512), nullable=True),
        sa.Column('checksum', sa.String(length=64), nullable=False),
        sa.Column('experiment_rows', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('wear_rows', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('imported_experiments', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('imported_wear', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('errors_summary', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['uploader_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('experiments_path'),
        sa.UniqueConstraint('wear_path'),
    )
    op.create_index('ix_import_batches_status', 'import_batches', ['status'])

    with op.batch_alter_table('experiments') as batch_op:
        batch_op.add_column(sa.Column('external_id', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('import_batch_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_experiments_import_batch_id', 'import_batches', ['import_batch_id'], ['id'], ondelete='SET NULL')
        batch_op.create_index('ix_experiments_external_id', ['external_id'], unique=True)


def downgrade():
    with op.batch_alter_table('experiments') as batch_op:
        batch_op.drop_index('ix_experiments_external_id')
        batch_op.drop_constraint('fk_experiments_import_batch_id', type_='foreignkey')
        batch_op.drop_column('import_batch_id')
        batch_op.drop_column('external_id')
    op.drop_index('ix_import_batches_status', table_name='import_batches')
    op.drop_table('import_batches')
