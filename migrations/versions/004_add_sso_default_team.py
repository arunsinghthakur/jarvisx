"""Add default_team_id and remove default_role from SSO configs

Revision ID: 004
Revises: 003
Create Date: 2026-02-01

"""
from alembic import op
import sqlalchemy as sa


revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('sso_configs', sa.Column('default_team_id', sa.String(), nullable=True))
    op.create_foreign_key(
        'fk_sso_configs_default_team_id',
        'sso_configs',
        'teams',
        ['default_team_id'],
        ['id'],
        ondelete='SET NULL'
    )
    op.drop_column('sso_configs', 'default_role')


def downgrade() -> None:
    op.add_column('sso_configs', sa.Column('default_role', sa.String(), nullable=True))
    op.drop_constraint('fk_sso_configs_default_team_id', 'sso_configs', type_='foreignkey')
    op.drop_column('sso_configs', 'default_team_id')
