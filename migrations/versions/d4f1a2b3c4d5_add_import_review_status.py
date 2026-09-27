"""Add publication and import review statuses.

Revision ID: d4f1a2b3c4d5
Revises: c3e8d5f1a7b9
Create Date: 2026-09-27
"""

from alembic import op
import sqlalchemy as sa


revision = 'd4f1a2b3c4d5'
down_revision = 'c3e8d5f1a7b9'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('experiments') as batch_op:
        batch_op.add_column(sa.Column('publication_status', sa.String(length=16), nullable=False, server_default='published'))
        batch_op.create_index('ix_experiments_publication_status', ['publication_status'], unique=False)

    with op.batch_alter_table('import_batches') as batch_op:
        batch_op.add_column(sa.Column('review_status', sa.String(length=16), nullable=False, server_default='published'))
        batch_op.add_column(sa.Column('reviewed_by_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('reviewed_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('review_comment', sa.Text(), nullable=True))
        batch_op.create_index('ix_import_batches_review_status', ['review_status'], unique=False)
        batch_op.create_foreign_key(
            'fk_import_batches_reviewed_by_id', 'users', ['reviewed_by_id'], ['id'], ondelete='SET NULL'
        )

    # Уже существующие импорты были подтверждены прежним workflow и считаются
    # опубликованными. Новые записи писателя будут переведены в draft кодом
    # маршрута подтверждения.
    op.execute("UPDATE import_batches SET review_status = 'published' WHERE status = 'completed'")


def downgrade():
    with op.batch_alter_table('import_batches') as batch_op:
        batch_op.drop_constraint('fk_import_batches_reviewed_by_id', type_='foreignkey')
        batch_op.drop_index('ix_import_batches_review_status')
        batch_op.drop_column('review_comment')
        batch_op.drop_column('reviewed_at')
        batch_op.drop_column('reviewed_by_id')
        batch_op.drop_column('review_status')
    with op.batch_alter_table('experiments') as batch_op:
        batch_op.drop_index('ix_experiments_publication_status')
        batch_op.drop_column('publication_status')

