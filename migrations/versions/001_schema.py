"""Database schema - consolidated migration

Revision ID: 001
Revises: None
Create Date: 2026-01-25

This migration creates all database tables for JarvisX platform.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    
    op.create_table('organizations',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_platform_admin', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('delete_protection', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('teams',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('organization_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('role', sa.String(), nullable=False, server_default='member'),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('scope_all_workspaces', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'name', name='uq_team_org_name')
    )
    op.create_index('ix_teams_organization_id', 'teams', ['organization_id'])
    
    op.create_table('users',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('organization_id', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('password_hash', sa.String(), nullable=False),
        sa.Column('first_name', sa.String(), nullable=True),
        sa.Column('last_name', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('last_login_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email', name='uq_user_email')
    )
    op.create_index('ix_users_organization_id', 'users', ['organization_id'])
    
    op.create_table('team_members',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('team_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('team_id', 'user_id', name='uq_team_member')
    )
    op.create_index('ix_team_members_team_id', 'team_members', ['team_id'])
    op.create_index('ix_team_members_user_id', 'team_members', ['user_id'])
    
    op.create_table('refresh_tokens',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('token_hash', sa.String(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('is_revoked', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash', name='uq_refresh_token_hash')
    )
    op.create_index('ix_refresh_tokens_user_id', 'refresh_tokens', ['user_id'])
    
    op.create_table('email_verifications',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('organization_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('otp_hash', sa.String(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('is_used', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_email_verifications_organization_id', 'email_verifications', ['organization_id'])
    op.create_index('ix_email_verifications_user_id', 'email_verifications', ['user_id'])
    
    op.create_table('workspaces',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('organization_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_system_workspace', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('delete_protection', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('chat_mode', sa.String(), nullable=False, server_default='both'),
        sa.Column('ui_base_url', sa.String(), nullable=True),
        sa.Column('voice_agent_name', sa.String(), nullable=False, server_default="'JarvisX'"),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_workspaces_organization_id', 'workspaces', ['organization_id'])
    
    op.create_table('team_workspaces',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('team_id', sa.String(), nullable=False),
        sa.Column('workspace_id', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('team_id', 'workspace_id', name='uq_team_workspace')
    )
    op.create_index('ix_team_workspaces_team_id', 'team_workspaces', ['team_id'])
    op.create_index('ix_team_workspaces_workspace_id', 'team_workspaces', ['workspace_id'])
    
    op.create_table('organization_llm_configs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('organization_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('provider', sa.String(), nullable=False, server_default='openai'),
        sa.Column('api_base_url', sa.String(), nullable=True),
        sa.Column('api_key_encrypted', sa.String(), nullable=True),
        sa.Column('model_name', sa.String(), nullable=False),
        sa.Column('max_tokens', sa.Integer(), nullable=False, server_default='4096'),
        sa.Column('temperature', sa.Integer(), nullable=False, server_default='7'),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('additional_config', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'name', name='uq_organization_llm_name')
    )
    op.create_index('ix_organization_llm_configs_organization_id', 'organization_llm_configs', ['organization_id'])
    
    op.create_table('organization_integrations',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('organization_id', sa.String(), nullable=False),
        sa.Column('integration_type', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('config_encrypted', sa.JSON(), nullable=True),
        sa.Column('config', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'name', name='uq_organization_integration_name')
    )
    op.create_index('ix_organization_integrations_organization_id', 'organization_integrations', ['organization_id'])
    op.create_index('ix_org_integration_type', 'organization_integrations', ['organization_id', 'integration_type'])
    
    op.create_table('agents',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('default_url', sa.String(), nullable=True),
        sa.Column('health_endpoint', sa.String(), nullable=True),
        sa.Column('is_system_agent', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_dynamic_agent', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('system_prompt', sa.Text(), nullable=True),
        sa.Column('llm_config_id', sa.String(), nullable=True),
        sa.Column('delete_protection', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('owner_organization_id', sa.String(), nullable=True),
        sa.Column('created_by', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['owner_organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['llm_config_id'], ['organization_llm_configs.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_agents_owner_organization_id', 'agents', ['owner_organization_id'])
    op.create_index('ix_agents_llm_config_id', 'agents', ['llm_config_id'])
    
    op.create_table('mcp_servers',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('default_config', sa.JSON(), nullable=True),
        sa.Column('is_system_server', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('delete_protection', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('owner_organization_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['owner_organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_mcp_servers_owner_organization_id', 'mcp_servers', ['owner_organization_id'])
    
    op.create_table('agent_mcps',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('agent_id', sa.String(), nullable=False),
        sa.Column('mcp_server_id', sa.String(), nullable=False),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('mcp_config', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['mcp_server_id'], ['mcp_servers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('agent_id', 'mcp_server_id', name='uq_agent_mcp')
    )
    
    op.create_table('subscriptions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('organization_id', sa.String(), nullable=False),
        sa.Column('plan', sa.String(), nullable=False, server_default='free'),
        sa.Column('status', sa.String(), nullable=False, server_default='active'),
        sa.Column('current_period_start', sa.DateTime(), nullable=False),
        sa.Column('current_period_end', sa.DateTime(), nullable=False),
        sa.Column('cancel_at_period_end', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', name='uq_subscription_org')
    )
    
    op.create_table('usage_records',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('organization_id', sa.String(), nullable=False),
        sa.Column('workspace_id', sa.String(), nullable=True),
        sa.Column('usage_type', sa.String(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('unit_cost', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('usage_metadata', sa.JSON(), nullable=True),
        sa.Column('recorded_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_usage_records_organization_id', 'usage_records', ['organization_id'])
    op.create_index('ix_usage_records_workspace_id', 'usage_records', ['workspace_id'])
    
    op.create_table('invoices',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('organization_id', sa.String(), nullable=False),
        sa.Column('invoice_number', sa.String(), nullable=False),
        sa.Column('period_start', sa.DateTime(), nullable=False),
        sa.Column('period_end', sa.DateTime(), nullable=False),
        sa.Column('subtotal', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('tax', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('currency', sa.String(), nullable=False, server_default="'USD'"),
        sa.Column('status', sa.String(), nullable=False, server_default="'draft'"),
        sa.Column('paid_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('invoice_number', name='uq_invoice_number')
    )
    op.create_index('ix_invoices_organization_id', 'invoices', ['organization_id'])
    
    op.create_table('knowledge_base_entries',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('organization_id', sa.String(), nullable=False),
        sa.Column('entry_type', sa.String(), nullable=False, server_default='snippet'),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('source_filename', sa.String(), nullable=True),
        sa.Column('content_preview', sa.Text(), nullable=True),
        sa.Column('chunk_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_kb_entries_organization_id', 'knowledge_base_entries', ['organization_id'])
    
    conn.execute(text("""
        CREATE TABLE knowledge_base_chunks (
            id VARCHAR NOT NULL,
            entry_id VARCHAR NOT NULL,
            organization_id VARCHAR NOT NULL,
            chunk_index INTEGER NOT NULL,
            content TEXT NOT NULL,
            token_count INTEGER,
            embedding vector(1536),
            metadata JSONB,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
            PRIMARY KEY (id),
            FOREIGN KEY (entry_id) REFERENCES knowledge_base_entries(id) ON DELETE CASCADE,
            FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
        )
    """))
    conn.execute(text("CREATE INDEX ix_kb_chunks_entry_id ON knowledge_base_chunks (entry_id)"))
    conn.execute(text("CREATE INDEX ix_kb_chunks_organization_id ON knowledge_base_chunks (organization_id)"))
    conn.execute(text("""
        CREATE INDEX ix_kb_chunks_embedding ON knowledge_base_chunks 
        USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)
    """))
    
    op.create_table('workflows',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('workspace_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('definition', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('trigger_type', sa.String(), nullable=False, server_default='manual'),
        sa.Column('trigger_config', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_by', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workspace_id', 'name', name='uq_workflow_workspace_name')
    )
    op.create_index('ix_workflows_workspace_id', 'workflows', ['workspace_id'])
    op.create_index('ix_workflows_workspace_active', 'workflows', ['workspace_id', 'is_active'])
    
    op.create_table('workflow_executions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('workflow_id', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('trigger_type', sa.String(), nullable=False),
        sa.Column('trigger_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_workflow_executions_workflow_id', 'workflow_executions', ['workflow_id'])
    op.create_index('ix_workflow_executions_status', 'workflow_executions', ['workflow_id', 'status'])
    op.create_index('ix_workflow_executions_created', 'workflow_executions', ['workflow_id', 'created_at'])
    
    op.create_table('workflow_execution_logs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('execution_id', sa.String(), nullable=False),
        sa.Column('node_id', sa.String(), nullable=False),
        sa.Column('node_type', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('input_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('output_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['execution_id'], ['workflow_executions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_workflow_execution_logs_execution_id', 'workflow_execution_logs', ['execution_id'])
    
    op.create_table('chatbot_conversations',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('workflow_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('organization_id', sa.String(), nullable=False),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_chatbot_conversations_workflow_id', 'chatbot_conversations', ['workflow_id'])
    op.create_index('ix_chatbot_conversations_user_id', 'chatbot_conversations', ['user_id'])
    op.create_index('ix_chatbot_conversations_organization_id', 'chatbot_conversations', ['organization_id'])
    op.create_index('ix_chatbot_conversations_session_id', 'chatbot_conversations', ['session_id'])
    op.create_index('ix_chatbot_conv_tenant_user', 'chatbot_conversations', ['organization_id', 'user_id'])
    op.create_index('ix_chatbot_conv_workflow_user', 'chatbot_conversations', ['workflow_id', 'user_id'])
    op.create_index('ix_chatbot_conv_session', 'chatbot_conversations', ['workflow_id', 'session_id'])
    
    op.create_table('chatbot_messages',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('conversation_id', sa.String(), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('message_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['chatbot_conversations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_chatbot_messages_conversation_id', 'chatbot_messages', ['conversation_id'])
    
    op.create_table('compliance_configs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('organization_id', sa.String(), nullable=False),
        sa.Column('pii_detection_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('pii_sensitivity_level', sa.String(), nullable=False, server_default='medium'),
        sa.Column('pii_mask_in_logs', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('pii_mask_in_responses', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('audit_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('audit_retention_days', sa.Integer(), nullable=False, server_default='90'),
        sa.Column('audit_log_level', sa.String(), nullable=False, server_default='standard'),
        sa.Column('policy_enforcement_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', name='uq_compliance_config_org')
    )
    op.create_index('ix_compliance_configs_organization_id', 'compliance_configs', ['organization_id'])
    
    op.create_table('pii_patterns',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('organization_id', sa.String(), nullable=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('pattern_regex', sa.String(), nullable=False),
        sa.Column('category', sa.String(), nullable=False),
        sa.Column('sensitivity', sa.String(), nullable=False, server_default='medium'),
        sa.Column('mask_char', sa.String(1), nullable=False, server_default='*'),
        sa.Column('mask_style', sa.String(), nullable=False, server_default='partial'),
        sa.Column('is_system_pattern', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_pii_patterns_organization_id', 'pii_patterns', ['organization_id'])
    op.create_index('ix_pii_patterns_category', 'pii_patterns', ['category'])
    
    op.create_table('policy_rules',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('organization_id', sa.String(), nullable=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('rule_type', sa.String(), nullable=False),
        sa.Column('rule_config', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('is_system_rule', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='50'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_policy_rules_organization_id', 'policy_rules', ['organization_id'])
    op.create_index('ix_policy_rules_rule_type', 'policy_rules', ['rule_type'])
    
    op.create_table('audit_logs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('organization_id', sa.String(), nullable=False),
        sa.Column('workspace_id', sa.String(), nullable=True),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('event_category', sa.String(), nullable=False),
        sa.Column('event_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('agent_id', sa.String(), nullable=True),
        sa.Column('resource_type', sa.String(), nullable=True),
        sa.Column('resource_id', sa.String(), nullable=True),
        sa.Column('action', sa.String(), nullable=True),
        sa.Column('outcome', sa.String(), nullable=True),
        sa.Column('pii_detected', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('pii_categories', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('ip_address', sa.String(), nullable=True),
        sa.Column('user_agent', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_audit_logs_organization_id', 'audit_logs', ['organization_id'])
    op.create_index('ix_audit_logs_workspace_id', 'audit_logs', ['workspace_id'])
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_event_type', 'audit_logs', ['event_type'])
    op.create_index('ix_audit_logs_event_category', 'audit_logs', ['event_category'])
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])


def downgrade() -> None:
    conn = op.get_bind()
    
    op.drop_index('ix_audit_logs_created_at', table_name='audit_logs')
    op.drop_index('ix_audit_logs_event_category', table_name='audit_logs')
    op.drop_index('ix_audit_logs_event_type', table_name='audit_logs')
    op.drop_index('ix_audit_logs_user_id', table_name='audit_logs')
    op.drop_index('ix_audit_logs_workspace_id', table_name='audit_logs')
    op.drop_index('ix_audit_logs_organization_id', table_name='audit_logs')
    op.drop_table('audit_logs')
    
    op.drop_index('ix_policy_rules_rule_type', table_name='policy_rules')
    op.drop_index('ix_policy_rules_organization_id', table_name='policy_rules')
    op.drop_table('policy_rules')
    
    op.drop_index('ix_pii_patterns_category', table_name='pii_patterns')
    op.drop_index('ix_pii_patterns_organization_id', table_name='pii_patterns')
    op.drop_table('pii_patterns')
    
    op.drop_index('ix_compliance_configs_organization_id', table_name='compliance_configs')
    op.drop_table('compliance_configs')
    
    op.drop_index('ix_chatbot_messages_conversation_id', table_name='chatbot_messages')
    op.drop_table('chatbot_messages')
    
    op.drop_index('ix_chatbot_conv_session', table_name='chatbot_conversations')
    op.drop_index('ix_chatbot_conv_workflow_user', table_name='chatbot_conversations')
    op.drop_index('ix_chatbot_conv_tenant_user', table_name='chatbot_conversations')
    op.drop_index('ix_chatbot_conversations_session_id', table_name='chatbot_conversations')
    op.drop_index('ix_chatbot_conversations_organization_id', table_name='chatbot_conversations')
    op.drop_index('ix_chatbot_conversations_user_id', table_name='chatbot_conversations')
    op.drop_index('ix_chatbot_conversations_workflow_id', table_name='chatbot_conversations')
    op.drop_table('chatbot_conversations')
    
    op.drop_index('ix_workflow_execution_logs_execution_id', table_name='workflow_execution_logs')
    op.drop_table('workflow_execution_logs')
    
    op.drop_index('ix_workflow_executions_created', table_name='workflow_executions')
    op.drop_index('ix_workflow_executions_status', table_name='workflow_executions')
    op.drop_index('ix_workflow_executions_workflow_id', table_name='workflow_executions')
    op.drop_table('workflow_executions')
    
    op.drop_index('ix_workflows_workspace_active', table_name='workflows')
    op.drop_index('ix_workflows_workspace_id', table_name='workflows')
    op.drop_table('workflows')
    
    conn.execute(text("DROP INDEX IF EXISTS ix_kb_chunks_embedding"))
    conn.execute(text("DROP INDEX IF EXISTS ix_kb_chunks_organization_id"))
    conn.execute(text("DROP INDEX IF EXISTS ix_kb_chunks_entry_id"))
    op.drop_table('knowledge_base_chunks')
    
    op.drop_index('ix_kb_entries_organization_id', table_name='knowledge_base_entries')
    op.drop_table('knowledge_base_entries')
    
    op.drop_index('ix_invoices_organization_id', table_name='invoices')
    op.drop_table('invoices')
    
    op.drop_index('ix_usage_records_workspace_id', table_name='usage_records')
    op.drop_index('ix_usage_records_organization_id', table_name='usage_records')
    op.drop_table('usage_records')
    
    op.drop_table('subscriptions')
    op.drop_table('agent_mcps')
    
    op.drop_index('ix_mcp_servers_owner_organization_id', table_name='mcp_servers')
    op.drop_table('mcp_servers')
    
    op.drop_index('ix_agents_llm_config_id', table_name='agents')
    op.drop_index('ix_agents_owner_organization_id', table_name='agents')
    op.drop_table('agents')
    
    op.drop_index('ix_org_integration_type', table_name='organization_integrations')
    op.drop_index('ix_organization_integrations_organization_id', table_name='organization_integrations')
    op.drop_table('organization_integrations')
    
    op.drop_index('ix_organization_llm_configs_organization_id', table_name='organization_llm_configs')
    op.drop_table('organization_llm_configs')
    
    op.drop_index('ix_team_workspaces_workspace_id', table_name='team_workspaces')
    op.drop_index('ix_team_workspaces_team_id', table_name='team_workspaces')
    op.drop_table('team_workspaces')
    
    op.drop_index('ix_workspaces_organization_id', table_name='workspaces')
    op.drop_table('workspaces')
    
    op.drop_index('ix_email_verifications_user_id', table_name='email_verifications')
    op.drop_index('ix_email_verifications_organization_id', table_name='email_verifications')
    op.drop_table('email_verifications')
    
    op.drop_index('ix_refresh_tokens_user_id', table_name='refresh_tokens')
    op.drop_table('refresh_tokens')
    
    op.drop_index('ix_team_members_user_id', table_name='team_members')
    op.drop_index('ix_team_members_team_id', table_name='team_members')
    op.drop_table('team_members')
    
    op.drop_index('ix_users_organization_id', table_name='users')
    op.drop_table('users')
    
    op.drop_index('ix_teams_organization_id', table_name='teams')
    op.drop_table('teams')
    
    op.drop_table('organizations')
    
    conn.execute(text("DROP EXTENSION IF EXISTS vector"))
