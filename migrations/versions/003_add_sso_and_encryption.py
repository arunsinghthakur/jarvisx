"""Add SSO configs, encryption keys, and versioning

Revision ID: 003
Revises: 002
Create Date: 2026-01-31

Combined migration that adds:
1. SSO configs table for OAuth2/OIDC and SAML providers
2. Organization slug and primary_domain for multi-tenancy
3. Encryption keys table for per-organization key management
4. Key version tracking on encrypted data fields
"""
from typing import Sequence, Union
import re

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def slugify(text: str) -> str:
    """Convert text to URL-safe slug"""
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    text = text.strip('-')
    return text


def upgrade() -> None:
    # ========================================================================
    # 1. Add organization slug and primary_domain
    # ========================================================================
    op.add_column('organizations', sa.Column('slug', sa.String(), nullable=True))
    op.add_column('organizations', sa.Column('primary_domain', sa.String(), nullable=True))
    op.create_index('ix_organizations_slug', 'organizations', ['slug'], unique=True)

    # Generate slugs for existing organizations
    conn = op.get_bind()
    organizations = conn.execute(sa.text("SELECT id, name FROM organizations")).fetchall()

    for org in organizations:
        slug = slugify(org.name)
        # Ensure uniqueness
        counter = 1
        original_slug = slug
        while True:
            existing = conn.execute(
                sa.text("SELECT id FROM organizations WHERE slug = :slug"),
                {"slug": slug}
            ).fetchone()

            if not existing:
                break

            slug = f"{original_slug}-{counter}"
            counter += 1

        conn.execute(
            sa.text("UPDATE organizations SET slug = :slug WHERE id = :id"),
            {"slug": slug, "id": org.id}
        )

    # Make slug non-nullable after populating
    op.alter_column('organizations', 'slug', nullable=False)

    # ========================================================================
    # 2. Create SSO configs table
    # ========================================================================
    op.create_table('sso_configs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('organization_id', sa.String(), nullable=False),
        sa.Column('provider', sa.String(), nullable=False),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='true'),

        # OAuth2/OIDC fields
        sa.Column('client_id', sa.String(), nullable=True),
        sa.Column('client_secret', sa.String(), nullable=True),
        sa.Column('client_secret_key_version', sa.Integer(), nullable=True),  # Version tracking
        sa.Column('client_secret_key_id', sa.String(), nullable=True),  # Key ID tracking
        sa.Column('tenant_id', sa.String(), nullable=True),

        # SAML fields
        sa.Column('idp_entity_id', sa.String(), nullable=True),
        sa.Column('idp_sso_url', sa.String(), nullable=True),
        sa.Column('idp_x509_cert', sa.Text(), nullable=True),
        sa.Column('sp_entity_id', sa.String(), nullable=True),

        # Provider-specific configuration
        sa.Column('provider_config', postgresql.JSON(astext_type=sa.Text()), nullable=True),

        # Settings
        sa.Column('allowed_domains', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('auto_provision_users', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('default_role', sa.String(), nullable=True),

        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),

        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'provider', name='uq_org_sso_provider')
    )
    op.create_index('ix_sso_configs_organization_id', 'sso_configs', ['organization_id'])
    op.create_index('ix_sso_configs_key_version', 'sso_configs', ['client_secret_key_version'])

    # ========================================================================
    # 3. Create encryption keys table
    # ========================================================================
    op.create_table('encryption_keys',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('organization_id', sa.String(), nullable=True),  # NULL = global/platform key
        sa.Column('key_name', sa.String(), nullable=False),
        sa.Column('key_purpose', sa.String(), nullable=False),  # 'sso', 'data', 'backup', etc.
        sa.Column('encrypted_key', sa.Text(), nullable=False),  # Key encrypted with master key
        sa.Column('key_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default='false'),  # Current active key
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),  # Key metadata
        sa.Column('created_by', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('rotated_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),

        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_encryption_keys_org_id', 'encryption_keys', ['organization_id'])
    op.create_index('ix_encryption_keys_purpose', 'encryption_keys', ['key_purpose'])
    op.create_index('ix_encryption_keys_active', 'encryption_keys', ['is_active', 'is_primary'])
    op.create_index('ix_encryption_keys_org_purpose', 'encryption_keys', ['organization_id', 'key_purpose'])

    # ========================================================================
    # 4. Add version tracking to organization_integrations (if exists)
    # ========================================================================
    # Check if organization_integrations table exists
    inspector = sa.inspect(conn)
    if 'organization_integrations' in inspector.get_table_names():
        op.add_column('organization_integrations', sa.Column('config_encrypted_key_version', sa.Integer(), nullable=True))
        op.add_column('organization_integrations', sa.Column('config_encrypted_key_id', sa.String(), nullable=True))
        op.create_index('ix_org_integrations_key_version', 'organization_integrations', ['config_encrypted_key_version'])


def downgrade() -> None:
    # Drop version tracking from organization_integrations
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if 'organization_integrations' in inspector.get_table_names():
        op.drop_index('ix_org_integrations_key_version', table_name='organization_integrations')
        op.drop_column('organization_integrations', 'config_encrypted_key_id')
        op.drop_column('organization_integrations', 'config_encrypted_key_version')

    # Drop encryption_keys table
    op.drop_index('ix_encryption_keys_org_purpose', table_name='encryption_keys')
    op.drop_index('ix_encryption_keys_active', table_name='encryption_keys')
    op.drop_index('ix_encryption_keys_purpose', table_name='encryption_keys')
    op.drop_index('ix_encryption_keys_org_id', table_name='encryption_keys')
    op.drop_table('encryption_keys')

    # Drop sso_configs table
    op.drop_index('ix_sso_configs_key_version', table_name='sso_configs')
    op.drop_index('ix_sso_configs_organization_id', table_name='sso_configs')
    op.drop_table('sso_configs')

    # Drop organization columns
    op.drop_index('ix_organizations_slug', table_name='organizations')
    op.drop_column('organizations', 'primary_domain')
    op.drop_column('organizations', 'slug')
