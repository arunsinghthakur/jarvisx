from enum import Enum
from typing import Set, Dict, Optional


class Resource(str, Enum):
    WORKSPACES = "workspaces"
    WORKFLOWS = "workflows"
    AGENTS = "agents"
    MCPS = "mcps"
    TEAMS = "teams"
    USERS = "users"
    LLM_CONFIGS = "llm_configs"
    INTEGRATIONS = "integrations"
    SSO_CONFIGS = "sso_configs"
    COMPLIANCE = "compliance"
    ENCRYPTION_KEYS = "encryption_keys"
    KNOWLEDGE_BASE = "knowledge_base"
    BILLING = "billing"
    ORGANIZATIONS = "organizations"
    CONVERSATIONS = "conversations"
    TRACING = "tracing"
    DASHBOARD = "dashboard"


class Action(str, Enum):
    VIEW = "view"
    CREATE = "create"
    EDIT = "edit"
    DELETE = "delete"
    EXECUTE = "execute"
    MANAGE = "manage"


class Role(str, Enum):
    PLATFORM_ADMIN = "platform_admin"
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


ROLE_PRIORITY = {
    Role.PLATFORM_ADMIN: 5,
    Role.OWNER: 4,
    Role.ADMIN: 3,
    Role.MEMBER: 2,
    Role.VIEWER: 1,
}


PERMISSION_MATRIX: Dict[Resource, Dict[Action, Set[Role]]] = {
    Resource.WORKSPACES: {
        Action.VIEW: {Role.VIEWER, Role.MEMBER, Role.ADMIN, Role.OWNER, Role.PLATFORM_ADMIN},
        Action.CREATE: {Role.ADMIN, Role.OWNER, Role.PLATFORM_ADMIN},
        Action.EDIT: {Role.ADMIN, Role.OWNER, Role.PLATFORM_ADMIN},
        Action.DELETE: {Role.OWNER, Role.PLATFORM_ADMIN},
    },
    Resource.WORKFLOWS: {
        Action.VIEW: {Role.VIEWER, Role.MEMBER, Role.ADMIN, Role.OWNER, Role.PLATFORM_ADMIN},
        Action.CREATE: {Role.MEMBER, Role.ADMIN, Role.OWNER, Role.PLATFORM_ADMIN},
        Action.EDIT: {Role.MEMBER, Role.ADMIN, Role.OWNER, Role.PLATFORM_ADMIN},
        Action.DELETE: {Role.MEMBER, Role.ADMIN, Role.OWNER, Role.PLATFORM_ADMIN},
        Action.EXECUTE: {Role.MEMBER, Role.ADMIN, Role.OWNER, Role.PLATFORM_ADMIN},
    },
    Resource.AGENTS: {
        Action.VIEW: {Role.VIEWER, Role.MEMBER, Role.ADMIN, Role.OWNER, Role.PLATFORM_ADMIN},
        Action.CREATE: {Role.MEMBER, Role.ADMIN, Role.OWNER, Role.PLATFORM_ADMIN},
        Action.EDIT: {Role.ADMIN, Role.OWNER, Role.PLATFORM_ADMIN},
        Action.DELETE: {Role.ADMIN, Role.OWNER, Role.PLATFORM_ADMIN},
    },
    Resource.MCPS: {
        Action.VIEW: {Role.VIEWER, Role.MEMBER, Role.ADMIN, Role.OWNER, Role.PLATFORM_ADMIN},
        Action.CREATE: {Role.MEMBER, Role.ADMIN, Role.OWNER, Role.PLATFORM_ADMIN},
        Action.EDIT: {Role.ADMIN, Role.OWNER, Role.PLATFORM_ADMIN},
        Action.DELETE: {Role.ADMIN, Role.OWNER, Role.PLATFORM_ADMIN},
    },
    Resource.TEAMS: {
        Action.VIEW: {Role.ADMIN, Role.OWNER, Role.PLATFORM_ADMIN},
        Action.CREATE: {Role.ADMIN, Role.OWNER, Role.PLATFORM_ADMIN},
        Action.EDIT: {Role.ADMIN, Role.OWNER, Role.PLATFORM_ADMIN},
        Action.DELETE: {Role.OWNER, Role.PLATFORM_ADMIN},
        Action.MANAGE: {Role.ADMIN, Role.OWNER, Role.PLATFORM_ADMIN},
    },
    Resource.USERS: {
        Action.VIEW: {Role.ADMIN, Role.OWNER, Role.PLATFORM_ADMIN},
        Action.CREATE: {Role.ADMIN, Role.OWNER, Role.PLATFORM_ADMIN},
        Action.EDIT: {Role.ADMIN, Role.OWNER, Role.PLATFORM_ADMIN},
        Action.DELETE: {Role.OWNER, Role.PLATFORM_ADMIN},
    },
    Resource.LLM_CONFIGS: {
        Action.VIEW: {Role.ADMIN, Role.OWNER, Role.PLATFORM_ADMIN},
        Action.CREATE: {Role.ADMIN, Role.OWNER, Role.PLATFORM_ADMIN},
        Action.EDIT: {Role.ADMIN, Role.OWNER, Role.PLATFORM_ADMIN},
        Action.DELETE: {Role.ADMIN, Role.OWNER, Role.PLATFORM_ADMIN},
    },
    Resource.INTEGRATIONS: {
        Action.VIEW: {Role.ADMIN, Role.OWNER, Role.PLATFORM_ADMIN},
        Action.CREATE: {Role.ADMIN, Role.OWNER, Role.PLATFORM_ADMIN},
        Action.EDIT: {Role.ADMIN, Role.OWNER, Role.PLATFORM_ADMIN},
        Action.DELETE: {Role.ADMIN, Role.OWNER, Role.PLATFORM_ADMIN},
    },
    Resource.SSO_CONFIGS: {
        Action.VIEW: {Role.ADMIN, Role.OWNER, Role.PLATFORM_ADMIN},
        Action.CREATE: {Role.ADMIN, Role.OWNER, Role.PLATFORM_ADMIN},
        Action.EDIT: {Role.ADMIN, Role.OWNER, Role.PLATFORM_ADMIN},
        Action.DELETE: {Role.ADMIN, Role.OWNER, Role.PLATFORM_ADMIN},
    },
    Resource.COMPLIANCE: {
        Action.VIEW: {Role.VIEWER, Role.MEMBER, Role.ADMIN, Role.OWNER, Role.PLATFORM_ADMIN},
        Action.CREATE: {Role.ADMIN, Role.OWNER, Role.PLATFORM_ADMIN},
        Action.EDIT: {Role.ADMIN, Role.OWNER, Role.PLATFORM_ADMIN},
        Action.DELETE: {Role.ADMIN, Role.OWNER, Role.PLATFORM_ADMIN},
    },
    Resource.ENCRYPTION_KEYS: {
        Action.VIEW: {Role.PLATFORM_ADMIN},
        Action.CREATE: {Role.PLATFORM_ADMIN},
        Action.EDIT: {Role.PLATFORM_ADMIN},
        Action.DELETE: {Role.PLATFORM_ADMIN},
    },
    Resource.KNOWLEDGE_BASE: {
        Action.VIEW: {Role.VIEWER, Role.MEMBER, Role.ADMIN, Role.OWNER, Role.PLATFORM_ADMIN},
        Action.CREATE: {Role.MEMBER, Role.ADMIN, Role.OWNER, Role.PLATFORM_ADMIN},
        Action.EDIT: {Role.MEMBER, Role.ADMIN, Role.OWNER, Role.PLATFORM_ADMIN},
        Action.DELETE: {Role.ADMIN, Role.OWNER, Role.PLATFORM_ADMIN},
    },
    Resource.BILLING: {
        Action.VIEW: {Role.ADMIN, Role.OWNER, Role.PLATFORM_ADMIN},
        Action.EDIT: {Role.OWNER, Role.PLATFORM_ADMIN},
    },
    Resource.ORGANIZATIONS: {
        Action.VIEW: {Role.VIEWER, Role.MEMBER, Role.ADMIN, Role.OWNER, Role.PLATFORM_ADMIN},
        Action.EDIT: {Role.OWNER, Role.PLATFORM_ADMIN},
        Action.CREATE: {Role.PLATFORM_ADMIN},
        Action.DELETE: {Role.PLATFORM_ADMIN},
    },
    Resource.CONVERSATIONS: {
        Action.VIEW: {Role.VIEWER, Role.MEMBER, Role.ADMIN, Role.OWNER, Role.PLATFORM_ADMIN},
        Action.CREATE: {Role.VIEWER, Role.MEMBER, Role.ADMIN, Role.OWNER, Role.PLATFORM_ADMIN},
        Action.DELETE: {Role.MEMBER, Role.ADMIN, Role.OWNER, Role.PLATFORM_ADMIN},
    },
    Resource.TRACING: {
        Action.VIEW: {Role.VIEWER, Role.MEMBER, Role.ADMIN, Role.OWNER, Role.PLATFORM_ADMIN},
    },
    Resource.DASHBOARD: {
        Action.VIEW: {Role.VIEWER, Role.MEMBER, Role.ADMIN, Role.OWNER, Role.PLATFORM_ADMIN},
    },
}


def has_permission(
    role: str,
    resource: Resource,
    action: Action,
    is_platform_admin: bool = False
) -> bool:
    if is_platform_admin:
        return True
    
    if resource not in PERMISSION_MATRIX:
        return False
    
    resource_permissions = PERMISSION_MATRIX[resource]
    if action not in resource_permissions:
        return False
    
    allowed_roles = resource_permissions[action]
    
    try:
        role_enum = Role(role)
    except ValueError:
        return False
    
    return role_enum in allowed_roles


def get_user_permissions(role: str, is_platform_admin: bool = False) -> Dict[str, Dict[str, bool]]:
    permissions = {}
    
    for resource in Resource:
        resource_perms = {}
        for action in Action:
            resource_perms[action.value] = has_permission(
                role, resource, action, is_platform_admin
            )
        permissions[resource.value] = resource_perms
    
    return permissions


def check_permission(
    role: str,
    resource: Resource,
    action: Action,
    is_platform_admin: bool = False,
    resource_owner_id: Optional[str] = None,
    current_user_id: Optional[str] = None
) -> bool:
    if is_platform_admin:
        return True
    
    if resource == Resource.WORKFLOWS and action in [Action.EDIT, Action.DELETE]:
        if role == Role.MEMBER.value and resource_owner_id and current_user_id:
            if resource_owner_id == current_user_id:
                return True
            return False
    
    return has_permission(role, resource, action, is_platform_admin)
