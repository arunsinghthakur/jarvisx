"""Seed data - consolidated migration

Revision ID: 002
Revises: 001
Create Date: 2026-01-25

This migration seeds initial data for JarvisX platform including:
- Default organization (JarvisX Platform Admin)
- System agents (Orchestrator, Developer, Browser, Voice, Researcher, Knowledge, Compliance agents)
- System MCP servers (Shell, Playwright, Tavily)
- Default admin user and team
- Default workspace
- Agent-MCP mappings
- Default PII patterns and policy rules
"""
from typing import Sequence, Union
import sys
import os
from pathlib import Path
import uuid
import json
from datetime import datetime

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "packages" / "core"))

from jarvisx.config.constants import SystemAgentCodes, SystemMCPCodes
from jarvisx.common.id_utils import agent_uuid, mcp_uuid, org_uuid, workspace_uuid

npmrc_path = str(project_root / ".npmrc")
uv_path = os.environ.get("UV_PATH", "uv")

revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


DEFAULT_PII_PATTERNS = [
    {
        "name": "Email Address",
        "pattern_regex": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        "category": "contact",
        "sensitivity": "medium",
        "mask_char": "*",
        "mask_style": "partial"
    },
    {
        "name": "Phone Number (US)",
        "pattern_regex": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
        "category": "contact",
        "sensitivity": "medium",
        "mask_char": "*",
        "mask_style": "partial"
    },
    {
        "name": "Social Security Number",
        "pattern_regex": r"\b\d{3}-\d{2}-\d{4}\b",
        "category": "government_id",
        "sensitivity": "high",
        "mask_char": "*",
        "mask_style": "full"
    },
    {
        "name": "Credit Card Number",
        "pattern_regex": r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
        "category": "financial",
        "sensitivity": "high",
        "mask_char": "*",
        "mask_style": "partial"
    },
    {
        "name": "IP Address",
        "pattern_regex": r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
        "category": "technical",
        "sensitivity": "low",
        "mask_char": "*",
        "mask_style": "partial"
    },
    {
        "name": "Date of Birth",
        "pattern_regex": r"\b(0?[1-9]|1[0-2])[-/](0?[1-9]|[12]\d|3[01])[-/](19|20)\d{2}\b",
        "category": "personal",
        "sensitivity": "medium",
        "mask_char": "*",
        "mask_style": "full"
    },
    {
        "name": "Passport Number",
        "pattern_regex": r"\b[A-Z]{1,2}\d{6,9}\b",
        "category": "government_id",
        "sensitivity": "high",
        "mask_char": "*",
        "mask_style": "full"
    },
]

DEFAULT_POLICY_RULES = [
    {
        "name": "No PII in Logs",
        "description": "Mask all detected PII before logging to audit trail",
        "rule_type": "data_protection",
        "rule_config": {
            "action": "mask_pii",
            "applies_to": ["audit_logs", "agent_logs"],
            "enforcement": "automatic"
        },
        "priority": 100
    },
    {
        "name": "Rate Limit",
        "description": "Limit API requests to 100 per minute per user",
        "rule_type": "access_control",
        "rule_config": {
            "max_requests": 100,
            "window_seconds": 60,
            "scope": "user"
        },
        "priority": 50
    },
    {
        "name": "Data Retention",
        "description": "Auto-delete conversation data older than 90 days",
        "rule_type": "governance",
        "rule_config": {
            "retention_days": 90,
            "applies_to": ["chatbot_conversations", "workflow_executions"],
            "action": "delete"
        },
        "priority": 10
    },
]


def hash_password_bcrypt(password: str) -> str:
    import bcrypt
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def upgrade() -> None:
    conn = op.get_bind()
    now = datetime.utcnow()
    
    jarvis_org_id = org_uuid("Default Organization - JarvisX")
    conn.execute(
        text("""
            INSERT INTO organizations (id, name, description, is_active, is_platform_admin, delete_protection, created_at, updated_at)
            VALUES (:id, :name, :description, :is_active, :is_platform_admin, :delete_protection, :created_at, :updated_at)
            ON CONFLICT (id) DO NOTHING
        """),
        {
            "id": jarvis_org_id,
            "name": "Default Organization - JarvisX",
            "description": "Platform administrator organization with full access to all resources",
            "is_active": True,
            "is_platform_admin": True,
            "delete_protection": True,
            "created_at": now,
            "updated_at": now
        }
    )
    
    system_agents = [
        {
            "code": SystemAgentCodes.ORCHESTRATOR,
            "name": "Central Orchestrator",
            "description": "Coordinates and delegates tasks across specialized agents",
        },
        {
            "code": SystemAgentCodes.DEVELOPER,
            "name": "Developer",
            "description": "Provides code generation, review, and debugging capabilities",
        },
        {
            "code": SystemAgentCodes.BROWSER,
            "name": "Browser",
            "description": "Automates web browser interactions and testing",
        },
        {
            "code": SystemAgentCodes.VOICE,
            "name": "Voice Gateway",
            "description": "Handles voice input/output and speech-to-text/text-to-speech",
        },
        {
            "code": SystemAgentCodes.RESEARCHER,
            "name": "Researcher",
            "description": "Performs real-time web searches and retrieves information",
        },
        {
            "code": SystemAgentCodes.KNOWLEDGE,
            "name": "Knowledge",
            "description": "Searches and retrieves information from the organization knowledge base",
        },
        {
            "code": SystemAgentCodes.PII_GUARDIAN,
            "name": "PII Guardian",
            "description": "Detects, classifies, and masks personally identifiable information (PII) in text to ensure data privacy and compliance",
        },
        {
            "code": SystemAgentCodes.AUDIT,
            "name": "Audit Agent",
            "description": "Logs and tracks all system activities, data access, and agent interactions for compliance auditing and reporting",
        },
        {
            "code": SystemAgentCodes.POLICY,
            "name": "Policy Evaluator",
            "description": "Evaluates requests and actions against organizational policies and compliance rules",
        },
        {
            "code": SystemAgentCodes.GOVERNANCE,
            "name": "Governance Agent",
            "description": "Enforces organizational governance policies including data retention, access control, and compliance reporting",
        },
    ]
    
    for agent_data in system_agents:
        agent_id = agent_uuid(agent_data["code"])
        conn.execute(
            text("""
                INSERT INTO agents (id, name, description, is_system_agent, is_dynamic_agent, delete_protection, created_by, created_at, updated_at)
                VALUES (:id, :name, :description, :is_system_agent, :is_dynamic_agent, :delete_protection, :created_by, :created_at, :updated_at)
                ON CONFLICT (id) DO NOTHING
            """),
            {
                "id": agent_id,
                "name": agent_data["name"],
                "description": agent_data["description"],
                "is_system_agent": True,
                "is_dynamic_agent": False,
                "delete_protection": True,
                "created_by": "system",
                "created_at": now,
                "updated_at": now
            }
        )
    
    mcp_servers = [
        {
            "code": SystemMCPCodes.SHELL,
            "name": "Shell",
            "description": "Provides secure command-line and shell execution capabilities",
            "default_config": {
                "command": uv_path,
                "args": [
                    "--directory",
                    "${workspace}",
                    "run",
                    "packages/core/jarvisx/mcp/servers/shell_server.py"
                ]
            },
        },
        {
            "code": SystemMCPCodes.PLAYWRIGHT,
            "name": "Playwright",
            "description": "Enables browser automation, navigation, and element interaction",
            "default_config": {
                "command": "npx",
                "args": [
                    "-y",
                    "@playwright/mcp@latest"
                ],
                "env": {
                    "NPM_CONFIG_USERCONFIG": npmrc_path
                }
            },
        },
        {
            "code": SystemMCPCodes.TAVILY,
            "name": "Tavily",
            "description": "Provides web search and content retrieval via Tavily API",
            "default_config": {
                "command": "npx",
                "args": [
                    "-y",
                    "tavily-mcp@latest"
                ],
                "env": {
                    "NPM_CONFIG_USERCONFIG": npmrc_path
                }
            },
        },
    ]
    
    for mcp_data in mcp_servers:
        mcp_id = mcp_uuid(mcp_data["code"])
        conn.execute(
            text("""
                INSERT INTO mcp_servers (id, name, description, default_config, is_system_server, delete_protection, created_at, updated_at)
                VALUES (:id, :name, :description, CAST(:default_config AS jsonb), :is_system_server, :delete_protection, :created_at, :updated_at)
                ON CONFLICT (id) DO NOTHING
            """),
            {
                "id": mcp_id,
                "name": mcp_data["name"],
                "description": mcp_data["description"],
                "default_config": json.dumps(mcp_data["default_config"]),
                "is_system_server": True,
                "delete_protection": True,
                "created_at": now,
                "updated_at": now
            }
        )
    
    admin_user_id = str(uuid.uuid4())
    admin_password_hash = hash_password_bcrypt("admin")
    
    existing_user = conn.execute(
        text("SELECT id FROM users WHERE email = :email"),
        {"email": "admin@default-organization-jarvisx.org"}
    ).fetchone()
    
    if existing_user:
        admin_user_id = str(existing_user[0])
    else:
        conn.execute(
            text("""
                INSERT INTO users (id, organization_id, email, password_hash, first_name, last_name, is_active, is_verified, created_at, updated_at)
                VALUES (:id, :organization_id, :email, :password_hash, :first_name, :last_name, :is_active, :is_verified, :created_at, :updated_at)
            """),
            {
                "id": admin_user_id,
                "organization_id": jarvis_org_id,
                "email": "admin@default-organization-jarvisx.org",
                "password_hash": admin_password_hash,
                "first_name": "Platform",
                "last_name": "Admin",
                "is_active": True,
                "is_verified": True,
                "created_at": now,
                "updated_at": now
            }
        )
    
    existing_team = conn.execute(
        text("SELECT id FROM teams WHERE organization_id = :org_id AND name = :name"),
        {"org_id": jarvis_org_id, "name": "Platform Admins"}
    ).fetchone()
    
    if existing_team:
        default_team_id = str(existing_team[0])
    else:
        default_team_id = str(uuid.uuid4())
        conn.execute(
            text("""
                INSERT INTO teams (id, organization_id, name, description, role, is_default, is_active, scope_all_workspaces, created_at, updated_at)
                VALUES (:id, :organization_id, :name, :description, :role, :is_default, :is_active, :scope_all_workspaces, :created_at, :updated_at)
            """),
            {
                "id": default_team_id,
                "organization_id": jarvis_org_id,
                "name": "Platform Admins",
                "description": "Default team for platform administrators",
                "role": "owner",
                "is_default": True,
                "is_active": True,
                "scope_all_workspaces": True,
                "created_at": now,
                "updated_at": now
            }
        )
    
    existing_member = conn.execute(
        text("SELECT id FROM team_members WHERE team_id = :team_id AND user_id = :user_id"),
        {"team_id": default_team_id, "user_id": admin_user_id}
    ).fetchone()
    
    if not existing_member:
        team_member_id = str(uuid.uuid4())
        conn.execute(
            text("""
                INSERT INTO team_members (id, team_id, user_id, is_active, created_at, updated_at)
                VALUES (:id, :team_id, :user_id, :is_active, :created_at, :updated_at)
            """),
            {
                "id": team_member_id,
                "team_id": default_team_id,
                "user_id": admin_user_id,
                "is_active": True,
                "created_at": now,
                "updated_at": now
            }
        )
    
    workspace_id = workspace_uuid(jarvis_org_id, "JarvisX")
    conn.execute(
        text("""
            INSERT INTO workspaces (id, organization_id, name, description, is_active, is_system_workspace, delete_protection, chat_mode, voice_agent_name, created_at, updated_at)
            VALUES (:id, :organization_id, :name, :description, :is_active, :is_system_workspace, :delete_protection, :chat_mode, :voice_agent_name, :created_at, :updated_at)
            ON CONFLICT (id) DO NOTHING
        """),
        {
            "id": workspace_id,
            "organization_id": jarvis_org_id,
            "name": "Default Workspace - JarvisX",
            "description": "Default workspace with access to all agents and MCP servers",
            "is_active": True,
            "is_system_workspace": True,
            "delete_protection": True,
            "chat_mode": "both",
            "voice_agent_name": "JarvisX",
            "created_at": now,
            "updated_at": now
        }
    )
    
    agent_mcp_matrix = {
        SystemAgentCodes.ORCHESTRATOR: [SystemMCPCodes.SHELL],
        SystemAgentCodes.VOICE: [],
        SystemAgentCodes.DEVELOPER: [SystemMCPCodes.SHELL],
        SystemAgentCodes.BROWSER: [SystemMCPCodes.PLAYWRIGHT],
        SystemAgentCodes.RESEARCHER: [SystemMCPCodes.TAVILY],
        SystemAgentCodes.KNOWLEDGE: [],
        SystemAgentCodes.PII_GUARDIAN: [],
        SystemAgentCodes.AUDIT: [],
        SystemAgentCodes.POLICY: [],
        SystemAgentCodes.GOVERNANCE: [],
    }
    
    for agent_code, mcp_codes in agent_mcp_matrix.items():
        agent_id = agent_uuid(agent_code)
        for mcp_code in mcp_codes:
            mcp_id = mcp_uuid(mcp_code)
            conn.execute(
                text("""
                    INSERT INTO agent_mcps (id, agent_id, mcp_server_id, is_enabled, mcp_config, created_at, updated_at)
                    VALUES (:id, :agent_id, :mcp_server_id, :is_enabled, CAST(:mcp_config AS jsonb), :created_at, :updated_at)
                    ON CONFLICT (id) DO NOTHING
                """),
                {
                    "id": workspace_uuid(agent_id, mcp_id),
                    "agent_id": agent_id,
                    "mcp_server_id": mcp_id,
                    "is_enabled": True,
                    "mcp_config": None,
                    "created_at": now,
                    "updated_at": now
                }
            )
    
    for pattern in DEFAULT_PII_PATTERNS:
        existing = conn.execute(
            text("SELECT id FROM pii_patterns WHERE name = :name AND organization_id IS NULL"),
            {"name": pattern["name"]}
        ).fetchone()
        if not existing:
            pattern_id = str(uuid.uuid4())
            conn.execute(text("""
                INSERT INTO pii_patterns (id, organization_id, name, pattern_regex, category, sensitivity, mask_char, mask_style, is_system_pattern, is_active, created_at, updated_at)
                VALUES (:id, NULL, :name, :pattern_regex, :category, :sensitivity, :mask_char, :mask_style, true, true, :now, :now)
            """), {
                "id": pattern_id,
                "name": pattern["name"],
                "pattern_regex": pattern["pattern_regex"],
                "category": pattern["category"],
                "sensitivity": pattern["sensitivity"],
                "mask_char": pattern["mask_char"],
                "mask_style": pattern["mask_style"],
                "now": now
            })
    
    for rule in DEFAULT_POLICY_RULES:
        existing = conn.execute(
            text("SELECT id FROM policy_rules WHERE name = :name AND organization_id IS NULL"),
            {"name": rule["name"]}
        ).fetchone()
        if not existing:
            rule_id = str(uuid.uuid4())
            conn.execute(text("""
                INSERT INTO policy_rules (id, organization_id, name, description, rule_type, rule_config, is_system_rule, is_active, priority, created_at, updated_at)
                VALUES (:id, NULL, :name, :description, :rule_type, CAST(:rule_config AS jsonb), true, true, :priority, :now, :now)
            """), {
                "id": rule_id,
                "name": rule["name"],
                "description": rule["description"],
                "rule_type": rule["rule_type"],
                "rule_config": json.dumps(rule["rule_config"]),
                "priority": rule["priority"],
                "now": now
            })
    
    conn.commit()


def downgrade() -> None:
    conn = op.get_bind()
    
    conn.execute(text("DELETE FROM policy_rules WHERE is_system_rule = true"))
    conn.execute(text("DELETE FROM pii_patterns WHERE is_system_pattern = true"))
    conn.execute(text("DELETE FROM agent_mcps"))
    conn.execute(text("DELETE FROM team_members"))
    conn.execute(text("DELETE FROM teams WHERE name = 'Platform Admins'"))
    conn.execute(text("DELETE FROM workspaces WHERE name = 'Default Workspace - JarvisX'"))
    conn.execute(text("DELETE FROM users WHERE email = 'admin@default-organization-jarvisx.org'"))
    conn.execute(text("DELETE FROM mcp_servers WHERE is_system_server = true"))
    conn.execute(text("DELETE FROM agents WHERE is_system_agent = true"))
    conn.execute(text("DELETE FROM organizations WHERE name = 'Default Organization - JarvisX'"))
