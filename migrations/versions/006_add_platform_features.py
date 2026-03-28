"""Add dead_letters, workflow_versions, usage_metrics, workflow_templates tables

Revision ID: 006
Revises: 005
Create Date: 2026-02-21

"""
from alembic import op
import sqlalchemy as sa

revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'workflow_dead_letters',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('execution_id', sa.String(), nullable=False),
        sa.Column('workflow_id', sa.String(), nullable=False),
        sa.Column('node_id', sa.String(), nullable=False),
        sa.Column('node_type', sa.String(), nullable=False),
        sa.Column('error', sa.Text(), nullable=False),
        sa.Column('input_data', sa.JSON(), nullable=True),
        sa.Column('retry_count', sa.Integer(), server_default='0'),
        sa.Column('status', sa.String(), server_default='pending', nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['execution_id'], ['workflow_executions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_dead_letters_execution', 'workflow_dead_letters', ['execution_id'])
    op.create_index('ix_dead_letters_workflow', 'workflow_dead_letters', ['workflow_id'])
    op.create_index('ix_dead_letters_status', 'workflow_dead_letters', ['status'])

    op.create_table(
        'workflow_versions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('workflow_id', sa.String(), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('definition', sa.JSON(), nullable=False),
        sa.Column('trigger_config', sa.JSON(), nullable=True),
        sa.Column('change_summary', sa.String(), nullable=True),
        sa.Column('created_by', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('workflow_id', 'version_number', name='uq_workflow_version_number'),
    )
    op.create_index('ix_workflow_versions_workflow', 'workflow_versions', ['workflow_id'])

    op.create_table(
        'usage_metrics',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('organization_id', sa.String(), nullable=False),
        sa.Column('workspace_id', sa.String(), nullable=True),
        sa.Column('workflow_id', sa.String(), nullable=True),
        sa.Column('execution_id', sa.String(), nullable=True),
        sa.Column('agent_name', sa.String(), nullable=True),
        sa.Column('model_name', sa.String(), nullable=True),
        sa.Column('input_tokens', sa.Integer(), server_default='0'),
        sa.Column('output_tokens', sa.Integer(), server_default='0'),
        sa.Column('total_tokens', sa.Integer(), server_default='0'),
        sa.Column('estimated_cost_usd', sa.JSON(), server_default='0.0'),
        sa.Column('recorded_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_usage_metrics_org', 'usage_metrics', ['organization_id'])
    op.create_index('ix_usage_metrics_recorded', 'usage_metrics', ['recorded_at'])
    op.create_index('ix_usage_metrics_org_recorded', 'usage_metrics', ['organization_id', 'recorded_at'])

    op.create_table(
        'workflow_templates',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(), nullable=False),
        sa.Column('definition', sa.JSON(), nullable=False),
        sa.Column('trigger_type', sa.String(), server_default='manual', nullable=False),
        sa.Column('trigger_config', sa.JSON(), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('is_system', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('organization_id', sa.String(), nullable=True),
        sa.Column('created_by', sa.String(), nullable=True),
        sa.Column('use_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_workflow_templates_category', 'workflow_templates', ['category'])


def downgrade() -> None:
    op.drop_table('workflow_templates')
    op.drop_table('usage_metrics')
    op.drop_table('workflow_versions')
    op.drop_table('workflow_dead_letters')
