from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, String, Boolean, Integer, DateTime, Text, 
    ForeignKey, JSON, UniqueConstraint, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
import enum

Base = declarative_base()


class ChatMode(str, enum.Enum):
    TEXT = "text"
    VOICE = "voice"
    BOTH = "both"


class SSOProvider(str, enum.Enum):
    GOOGLE = "google"
    MICROSOFT = "microsoft"
    OKTA = "okta"
    SAML = "saml"


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    slug = Column(String, nullable=True, unique=True, index=True)  # URL-safe identifier for multi-tenant SSO
    primary_domain = Column(String, nullable=True)  # Primary email domain for this organization
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_platform_admin = Column(Boolean, default=False, nullable=False)
    delete_protection = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    workspaces = relationship("Workspace", back_populates="organization", cascade="all, delete-orphan")
    sso_configs = relationship("SSOConfig", back_populates="organization", cascade="all, delete-orphan")
    encryption_keys = relationship("EncryptionKey", back_populates="organization", cascade="all, delete-orphan")


class SSOConfig(Base):
    """SSO Configuration for organizations"""
    __tablename__ = "sso_configs"

    id = Column(String, primary_key=True)
    organization_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String, nullable=False)  # SSOProvider enum value
    is_enabled = Column(Boolean, default=True, nullable=False)

    # OAuth2/OIDC fields
    client_id = Column(String, nullable=True)
    client_secret = Column(String, nullable=True)  # Encrypted with org-specific key
    client_secret_key_version = Column(Integer, nullable=True)  # Track which key version encrypted this
    client_secret_key_id = Column(String, nullable=True)  # Track which key ID encrypted this
    tenant_id = Column(String, nullable=True)  # For Azure AD/Microsoft

    # SAML fields
    idp_entity_id = Column(String, nullable=True)  # SAML IdP Entity ID
    idp_sso_url = Column(String, nullable=True)  # SAML IdP SSO URL
    idp_x509_cert = Column(Text, nullable=True)  # SAML IdP X.509 certificate
    sp_entity_id = Column(String, nullable=True)  # SAML SP Entity ID (this app)

    # Provider-specific configuration (JSON)
    provider_config = Column(JSON, nullable=True, default=dict)

    # Settings
    allowed_domains = Column(JSON, nullable=True, default=list)  # List of allowed email domains
    auto_provision_users = Column(Boolean, default=True, nullable=False)  # Auto-create users on SSO login
    default_team_id = Column(String, ForeignKey("teams.id", ondelete="SET NULL"), nullable=True)  # Default team for SSO users

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    organization = relationship("Organization", back_populates="sso_configs")

    __table_args__ = (UniqueConstraint("organization_id", "provider", name="uq_org_sso_provider"),)


class EncryptionKey(Base):
    """Encryption key management for organizations"""
    __tablename__ = "encryption_keys"

    id = Column(String, primary_key=True)
    organization_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)  # NULL = global/platform key
    key_name = Column(String, nullable=False)
    key_purpose = Column(String, nullable=False)  # 'sso', 'data', 'backup', etc.
    encrypted_key = Column(Text, nullable=False)  # Key encrypted with master key
    key_version = Column(Integer, nullable=False, default=1)
    is_active = Column(Boolean, nullable=False, default=True)
    is_primary = Column(Boolean, nullable=False, default=False)  # Current active key
    key_metadata = Column("metadata", JSON, nullable=True)  # Key metadata
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    rotated_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)

    organization = relationship("Organization", back_populates="encryption_keys")


class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(String, primary_key=True)
    organization_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_system_workspace = Column(Boolean, default=False, nullable=False)
    delete_protection = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    chat_mode = Column(String, default=ChatMode.BOTH.value, nullable=False)
    ui_base_url = Column(String, nullable=True)
    voice_agent_name = Column(String, nullable=False)
    
    organization = relationship("Organization", back_populates="workspaces")


class AgentMCP(Base):
    __tablename__ = "agent_mcps"
    
    id = Column(String, primary_key=True)
    agent_id = Column(String, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    mcp_server_id = Column(String, ForeignKey("mcp_servers.id", ondelete="CASCADE"), nullable=False)
    is_enabled = Column(Boolean, default=True, nullable=False)
    mcp_config = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    __table_args__ = (UniqueConstraint("agent_id", "mcp_server_id", name="uq_agent_mcp"),)


class Agent(Base):
    __tablename__ = "agents"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    default_url = Column(String, nullable=True)
    health_endpoint = Column(String, nullable=True)
    is_system_agent = Column(Boolean, default=True, nullable=False)
    is_dynamic_agent = Column(Boolean, default=False, nullable=False)
    system_prompt = Column(Text, nullable=True)
    llm_config_id = Column(String, ForeignKey("organization_llm_configs.id", ondelete="SET NULL"), nullable=True, index=True)
    delete_protection = Column(Boolean, default=False, nullable=False)
    owner_organization_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    owner_organization = relationship("Organization", foreign_keys=[owner_organization_id])
    llm_config = relationship("OrganizationLLMConfig", foreign_keys=[llm_config_id])
    mcp_assignments = relationship("AgentMCP", cascade="all, delete-orphan")


class MCPServer(Base):
    __tablename__ = "mcp_servers"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    default_config = Column(JSON, nullable=True)
    is_system_server = Column(Boolean, default=False, nullable=False)
    delete_protection = Column(Boolean, default=False, nullable=False)
    owner_organization_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    owner_organization = relationship("Organization", foreign_keys=[owner_organization_id])


class UserRole(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class Team(Base):
    __tablename__ = "teams"
    
    id = Column(String, primary_key=True)
    organization_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    role = Column(String, default=UserRole.MEMBER.value, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    scope_all_workspaces = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    organization = relationship("Organization")
    members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")
    workspace_scopes = relationship("TeamWorkspace", back_populates="team", cascade="all, delete-orphan")
    
    __table_args__ = (UniqueConstraint("organization_id", "name", name="uq_team_org_name"),)


class TeamWorkspace(Base):
    __tablename__ = "team_workspaces"
    
    id = Column(String, primary_key=True)
    team_id = Column(String, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id = Column(String, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    team = relationship("Team", back_populates="workspace_scopes")
    workspace = relationship("Workspace")
    
    __table_args__ = (UniqueConstraint("team_id", "workspace_id", name="uq_team_workspace"),)


class User(Base):
    __tablename__ = "users"
    
    ROLE_PRIORITY = {
        UserRole.OWNER.value: 4,
        UserRole.ADMIN.value: 3,
        UserRole.MEMBER.value: 2,
        UserRole.VIEWER.value: 1,
    }
    
    id = Column(String, primary_key=True)
    organization_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    email = Column(String, nullable=False, unique=True)
    password_hash = Column(String, nullable=False)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    last_login_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    organization = relationship("Organization")
    team_memberships = relationship("TeamMember", back_populates="user", cascade="all, delete-orphan")
    
    @property
    def effective_role(self) -> str:
        if not self.team_memberships:
            return UserRole.VIEWER.value
        highest_role = UserRole.VIEWER.value
        highest_priority = 0
        for membership in self.team_memberships:
            if membership.is_active and membership.team and membership.team.is_active:
                team_role = membership.team.role
                priority = self.ROLE_PRIORITY.get(team_role, 0)
                if priority > highest_priority:
                    highest_priority = priority
                    highest_role = team_role
        return highest_role
    
    def is_owner_or_admin(self) -> bool:
        role = self.effective_role
        return role in (UserRole.OWNER.value, UserRole.ADMIN.value)


class TeamMember(Base):
    __tablename__ = "team_members"
    
    id = Column(String, primary_key=True)
    team_id = Column(String, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    team = relationship("Team", back_populates="members")
    user = relationship("User", back_populates="team_memberships")
    
    __table_args__ = (UniqueConstraint("team_id", "user_id", name="uq_team_member"),)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String, nullable=False, unique=True)
    expires_at = Column(DateTime, nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    user = relationship("User")


class EmailVerification(Base):
    __tablename__ = "email_verifications"
    
    id = Column(String, primary_key=True)
    organization_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    otp_hash = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False, nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    organization = relationship("Organization")
    user = relationship("User")


class BillingPlan(str, enum.Enum):
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class UsageRecord(Base):
    __tablename__ = "usage_records"
    
    id = Column(String, primary_key=True)
    organization_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id = Column(String, ForeignKey("workspaces.id", ondelete="SET NULL"), nullable=True, index=True)
    usage_type = Column(String, nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    unit_cost = Column(Integer, default=0, nullable=False)
    usage_metadata = Column(JSON, nullable=True)
    recorded_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Invoice(Base):
    __tablename__ = "invoices"
    
    id = Column(String, primary_key=True)
    organization_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    invoice_number = Column(String, nullable=False, unique=True)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    subtotal = Column(Integer, default=0, nullable=False)
    tax = Column(Integer, default=0, nullable=False)
    total = Column(Integer, default=0, nullable=False)
    currency = Column(String, default="USD", nullable=False)
    status = Column(String, default="draft", nullable=False)
    paid_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class Subscription(Base):
    __tablename__ = "subscriptions"
    
    id = Column(String, primary_key=True)
    organization_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, unique=True)
    plan = Column(String, default=BillingPlan.FREE.value, nullable=False)
    status = Column(String, default="active", nullable=False)
    current_period_start = Column(DateTime, nullable=False)
    current_period_end = Column(DateTime, nullable=False)
    cancel_at_period_end = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class LLMProvider(str, enum.Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE_OPENAI = "azure_openai"
    GOOGLE_VERTEX = "google_vertex"
    LITELLM = "litellm"
    CUSTOM = "custom"


class OrganizationLLMConfig(Base):
    __tablename__ = "organization_llm_configs"
    
    id = Column(String, primary_key=True)
    organization_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    provider = Column(String, default=LLMProvider.OPENAI.value, nullable=False)
    api_base_url = Column(String, nullable=True)
    api_key_encrypted = Column(String, nullable=True)
    model_name = Column(String, nullable=False)
    max_tokens = Column(Integer, default=4096, nullable=False)
    temperature = Column(Integer, default=7, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    additional_config = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    organization = relationship("Organization")
    
    __table_args__ = (UniqueConstraint("organization_id", "name", name="uq_organization_llm_name"),)


class IntegrationType(str, enum.Enum):
    EMAIL = "email"
    SLACK = "slack"
    TEAMS = "teams"


class OrganizationIntegration(Base):
    __tablename__ = "organization_integrations"
    
    id = Column(String, primary_key=True)
    organization_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    integration_type = Column(String, nullable=False)
    name = Column(String, nullable=False)
    config_encrypted = Column(JSON, nullable=True)
    config_encrypted_key_version = Column(Integer, nullable=True)  # Track encryption key version
    config_encrypted_key_id = Column(String, nullable=True)  # Track encryption key ID
    config = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    organization = relationship("Organization")
    
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_organization_integration_name"),
        Index("ix_org_integration_type", "organization_id", "integration_type"),
    )


class KnowledgeBaseEntryType(str, enum.Enum):
    DOCUMENT = "document"
    SNIPPET = "snippet"
    URL = "url"


class KnowledgeBaseEntry(Base):
    __tablename__ = "knowledge_base_entries"
    
    id = Column(String, primary_key=True)
    organization_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    entry_type = Column(String, default=KnowledgeBaseEntryType.SNIPPET.value, nullable=False)
    title = Column(String, nullable=False)
    source_filename = Column(String, nullable=True)
    content_preview = Column(Text, nullable=True)
    chunk_count = Column(Integer, default=0, nullable=False)
    file_size = Column(Integer, nullable=True)
    entry_metadata = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    organization = relationship("Organization")
    chunks = relationship("KnowledgeBaseChunk", back_populates="entry", cascade="all, delete-orphan")


class KnowledgeBaseChunk(Base):
    __tablename__ = "knowledge_base_chunks"
    
    id = Column(String, primary_key=True)
    entry_id = Column(String, ForeignKey("knowledge_base_entries.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    token_count = Column(Integer, nullable=True)
    embedding = Column(Vector(1536), nullable=True)
    chunk_metadata = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    entry = relationship("KnowledgeBaseEntry", back_populates="chunks")
    
    __table_args__ = (
        Index("ix_kb_chunks_org_embedding", "organization_id", postgresql_using="ivfflat", postgresql_with={"lists": 100}, postgresql_ops={"embedding": "vector_cosine_ops"}),
    )


class WorkflowTriggerType(str, enum.Enum):
    MANUAL = "manual"
    SCHEDULE = "schedule"
    WEBHOOK = "webhook"
    AGENT_EVENT = "agent_event"
    CHATBOT = "chatbot"


class WorkflowExecutionStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Workflow(Base):
    __tablename__ = "workflows"
    
    id = Column(String, primary_key=True)
    workspace_id = Column(String, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    definition = Column(JSON, nullable=False, default=dict)
    trigger_type = Column(String, default=WorkflowTriggerType.MANUAL.value, nullable=False)
    trigger_config = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_by = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    workspace = relationship("Workspace")
    creator = relationship("User")
    executions = relationship("WorkflowExecution", back_populates="workflow", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint("workspace_id", "name", name="uq_workflow_workspace_name"),
        Index("ix_workflows_workspace_active", "workspace_id", "is_active"),
    )


class WorkflowExecution(Base):
    __tablename__ = "workflow_executions"
    
    id = Column(String, primary_key=True)
    workflow_id = Column(String, ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String, default=WorkflowExecutionStatus.PENDING.value, nullable=False)
    trigger_type = Column(String, nullable=False)
    trigger_data = Column(JSON, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    execution_metadata = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    workflow = relationship("Workflow", back_populates="executions")
    logs = relationship("WorkflowExecutionLog", back_populates="execution", cascade="all, delete-orphan", order_by="WorkflowExecutionLog.started_at")
    
    __table_args__ = (
        Index("ix_workflow_executions_status", "workflow_id", "status"),
        Index("ix_workflow_executions_created", "workflow_id", "created_at"),
    )


class WorkflowExecutionLog(Base):
    __tablename__ = "workflow_execution_logs"
    
    id = Column(String, primary_key=True)
    execution_id = Column(String, ForeignKey("workflow_executions.id", ondelete="CASCADE"), nullable=False, index=True)
    node_id = Column(String, nullable=False)
    node_type = Column(String, nullable=False)
    status = Column(String, default=WorkflowExecutionStatus.PENDING.value, nullable=False)
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    execution = relationship("WorkflowExecution", back_populates="logs")


class ComplianceConfig(Base):
    __tablename__ = "compliance_configs"
    
    id = Column(String, primary_key=True)
    organization_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    pii_detection_enabled = Column(Boolean, default=True, nullable=False)
    pii_sensitivity_level = Column(String, default="medium", nullable=False)
    pii_mask_in_logs = Column(Boolean, default=True, nullable=False)
    pii_mask_in_responses = Column(Boolean, default=False, nullable=False)
    audit_enabled = Column(Boolean, default=True, nullable=False)
    audit_retention_days = Column(Integer, default=90, nullable=False)
    audit_log_level = Column(String, default="standard", nullable=False)
    policy_enforcement_enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    organization = relationship("Organization", backref="compliance_config")


class PIIPattern(Base):
    __tablename__ = "pii_patterns"
    
    id = Column(String, primary_key=True)
    organization_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)
    name = Column(String, nullable=False)
    pattern_regex = Column(String, nullable=False)
    category = Column(String, nullable=False, index=True)
    sensitivity = Column(String, default="medium", nullable=False)
    mask_char = Column(String(1), default="*", nullable=False)
    mask_style = Column(String, default="partial", nullable=False)
    is_system_pattern = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    organization = relationship("Organization", backref="pii_patterns")


class PolicyRule(Base):
    __tablename__ = "policy_rules"
    
    id = Column(String, primary_key=True)
    organization_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    rule_type = Column(String, nullable=False, index=True)
    rule_config = Column(JSON, nullable=False)
    is_system_rule = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    priority = Column(Integer, default=50, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    organization = relationship("Organization", backref="policy_rules")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(String, primary_key=True)
    organization_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id = Column(String, ForeignKey("workspaces.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    event_type = Column(String, nullable=False, index=True)
    event_category = Column(String, nullable=False, index=True)
    event_data = Column(JSON, nullable=True)
    agent_id = Column(String, nullable=True)
    resource_type = Column(String, nullable=True)
    resource_id = Column(String, nullable=True)
    action = Column(String, nullable=True)
    outcome = Column(String, nullable=True)
    pii_detected = Column(Boolean, default=False, nullable=False)
    pii_categories = Column(JSON, nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    organization = relationship("Organization", backref="audit_logs")
    workspace = relationship("Workspace", backref="audit_logs")
    user = relationship("User", backref="audit_logs")


class ChatbotConversation(Base):
    __tablename__ = "chatbot_conversations"
    
    id = Column(String, primary_key=True)
    workflow_id = Column(String, ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    organization_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(String, nullable=False, index=True)
    title = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    workflow = relationship("Workflow", backref="chatbot_conversations")
    user = relationship("User", backref="chatbot_conversations")
    organization = relationship("Organization", backref="chatbot_conversations")
    messages = relationship("ChatbotMessage", back_populates="conversation", cascade="all, delete-orphan", order_by="ChatbotMessage.created_at")
    
    __table_args__ = (
        Index("ix_chatbot_conv_tenant_user", "organization_id", "user_id"),
        Index("ix_chatbot_conv_workflow_user", "workflow_id", "user_id"),
        Index("ix_chatbot_conv_session", "workflow_id", "session_id"),
    )


class WorkflowDeadLetter(Base):
    __tablename__ = "workflow_dead_letters"

    id = Column(String, primary_key=True)
    execution_id = Column(String, ForeignKey("workflow_executions.id", ondelete="CASCADE"), nullable=False, index=True)
    workflow_id = Column(String, ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False, index=True)
    node_id = Column(String, nullable=False)
    node_type = Column(String, nullable=False)
    error = Column(Text, nullable=False)
    input_data = Column(JSON, nullable=True)
    retry_count = Column(Integer, default=0)
    status = Column(String, default="pending", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime, nullable=True)

    execution = relationship("WorkflowExecution")
    workflow = relationship("Workflow")


class WorkflowVersion(Base):
    __tablename__ = "workflow_versions"

    id = Column(String, primary_key=True)
    workflow_id = Column(String, ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    definition = Column(JSON, nullable=False)
    trigger_config = Column(JSON, nullable=True)
    change_summary = Column(String, nullable=True)
    created_by = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    workflow = relationship("Workflow")
    creator = relationship("User")

    __table_args__ = (
        UniqueConstraint("workflow_id", "version_number", name="uq_workflow_version_number"),
    )


class UsageMetric(Base):
    __tablename__ = "usage_metrics"

    id = Column(String, primary_key=True)
    organization_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id = Column(String, nullable=True)
    workflow_id = Column(String, nullable=True)
    execution_id = Column(String, nullable=True)
    agent_name = Column(String, nullable=True)
    model_name = Column(String, nullable=True)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    estimated_cost_usd = Column(JSON, default=0.0)
    recorded_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class WorkflowTemplate(Base):
    __tablename__ = "workflow_templates"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String, nullable=False, index=True)
    definition = Column(JSON, nullable=False)
    trigger_type = Column(String, nullable=False, default="manual")
    trigger_config = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=True)
    is_system = Column(Boolean, default=False, nullable=False)
    organization_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True)
    created_by = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    use_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class PlatformSetting(Base):
    __tablename__ = "platform_settings"

    id = Column(String, primary_key=True)
    category = Column(String, nullable=False, index=True)
    key = Column(String, nullable=False)
    value = Column(JSON, nullable=False)
    value_type = Column(String, nullable=False, default="string")
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(String, ForeignKey("users.id"), nullable=True)

    __table_args__ = (
        UniqueConstraint("category", "key", name="uq_platform_setting_category_key"),
    )


class ChatbotMessage(Base):
    __tablename__ = "chatbot_messages"
    
    id = Column(String, primary_key=True)
    conversation_id = Column(String, ForeignKey("chatbot_conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    message_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    conversation = relationship("ChatbotConversation", back_populates="messages")
