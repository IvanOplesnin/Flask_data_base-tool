"""Make username index match the User model.

Revision ID: c3e8d5f1a7b9
Revises: b8d3a1f4e6c2
Create Date: 2026-08-29
"""

from alembic import op


revision = 'c3e8d5f1a7b9'
down_revision = 'b8d3a1f4e6c2'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_index('ix_users_username', table_name='users')
    op.create_index('ix_users_username', 'users', ['username'], unique=True)


def downgrade():
    op.drop_index('ix_users_username', table_name='users')
    op.create_index('ix_users_username', 'users', ['username'], unique=False)
