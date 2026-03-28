"""Add platform_settings table for runtime-configurable operational settings

Revision ID: 005
Revises: 004
Create Date: 2026-02-21

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None

SEED_SETTINGS = [
    ("tracing", "sample_rate", 0.1, "float", "Sampling rate for traces (0.0 to 1.0)"),
    ("tracing", "trace_llm", False, "bool", "Enable LLM call tracing via LiteLLM callbacks"),
    ("tracing", "trace_api", False, "bool", "Enable API request tracing via middleware"),
    ("tracing", "trace_workflows", True, "bool", "Enable workflow execution tracing"),
    ("tracing", "llm_input_limit", 500, "int", "Max characters logged for LLM inputs (0 = unlimited)"),
    ("tracing", "llm_output_limit", 500, "int", "Max characters logged for LLM outputs (0 = unlimited)"),
    ("tracing", "api_traced_prefixes", "", "string", "Comma-separated API path prefixes to trace (empty = all)"),
    ("performance", "agent_card_cache_ttl", 14400, "int", "Agent card cache TTL in seconds"),
    ("performance", "mcp_cache_ttl", 14400, "int", "MCP server cache TTL in seconds"),
    ("auth", "otp_expiry_minutes", 15, "int", "OTP expiration time in minutes"),
    ("auth", "otp_max_attempts", 3, "int", "Max OTP verification attempts"),
]


def upgrade() -> None:
    op.create_table(
        'platform_settings',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('category', sa.String(), nullable=False),
        sa.Column('key', sa.String(), nullable=False),
        sa.Column('value', sa.JSON(), nullable=False),
        sa.Column('value_type', sa.String(), nullable=False, server_default='string'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('updated_by', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id']),
        sa.UniqueConstraint('category', 'key', name='uq_platform_setting_category_key'),
    )
    op.create_index('ix_platform_settings_category', 'platform_settings', ['category'])

    settings_table = sa.table(
        'platform_settings',
        sa.column('id', sa.String),
        sa.column('category', sa.String),
        sa.column('key', sa.String),
        sa.column('value', sa.JSON),
        sa.column('value_type', sa.String),
        sa.column('description', sa.Text),
        sa.column('updated_at', sa.DateTime),
    )
    now = datetime.utcnow()
    rows = []
    for cat, key, val, vtype, desc in SEED_SETTINGS:
        rows.append({
            "id": f"ps_{cat}_{key}",
            "category": cat,
            "key": key,
            "value": val,
            "value_type": vtype,
            "description": desc,
            "updated_at": now,
        })
    if rows:
        op.bulk_insert(settings_table, rows)


def downgrade() -> None:
    op.drop_index('ix_platform_settings_category', table_name='platform_settings')
    op.drop_table('platform_settings')
