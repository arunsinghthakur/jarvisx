export const RESOURCES = {
  WORKSPACES: 'workspaces',
  WORKFLOWS: 'workflows',
  AGENTS: 'agents',
  MCPS: 'mcps',
  TEAMS: 'teams',
  USERS: 'users',
  LLM_CONFIGS: 'llm_configs',
  INTEGRATIONS: 'integrations',
  SSO_CONFIGS: 'sso_configs',
  COMPLIANCE: 'compliance',
  ENCRYPTION_KEYS: 'encryption_keys',
  KNOWLEDGE_BASE: 'knowledge_base',
  BILLING: 'billing',
  ORGANIZATIONS: 'organizations',
  CONVERSATIONS: 'conversations',
  TRACING: 'tracing',
  DASHBOARD: 'dashboard',
}

export const ACTIONS = {
  VIEW: 'view',
  CREATE: 'create',
  EDIT: 'edit',
  DELETE: 'delete',
  EXECUTE: 'execute',
  MANAGE: 'manage',
}

export const ROLES = {
  PLATFORM_ADMIN: 'platform_admin',
  OWNER: 'owner',
  ADMIN: 'admin',
  MEMBER: 'member',
  VIEWER: 'viewer',
}

export const ROLE_PRIORITY = {
  [ROLES.PLATFORM_ADMIN]: 5,
  [ROLES.OWNER]: 4,
  [ROLES.ADMIN]: 3,
  [ROLES.MEMBER]: 2,
  [ROLES.VIEWER]: 1,
}

export const hasPermission = (permissions, resource, action) => {
  if (!permissions) return false
  const resourcePerms = permissions[resource]
  if (!resourcePerms) return false
  return resourcePerms[action] === true
}

export const canView = (permissions, resource) => hasPermission(permissions, resource, ACTIONS.VIEW)
export const canCreate = (permissions, resource) => hasPermission(permissions, resource, ACTIONS.CREATE)
export const canEdit = (permissions, resource) => hasPermission(permissions, resource, ACTIONS.EDIT)
export const canDelete = (permissions, resource) => hasPermission(permissions, resource, ACTIONS.DELETE)
export const canExecute = (permissions, resource) => hasPermission(permissions, resource, ACTIONS.EXECUTE)
export const canManage = (permissions, resource) => hasPermission(permissions, resource, ACTIONS.MANAGE)
