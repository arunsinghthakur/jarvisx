import { useCallback, useMemo } from 'react'
import { useAuth } from '../contexts'
import {
  RESOURCES,
  ACTIONS,
  hasPermission,
  canView,
  canCreate,
  canEdit,
  canDelete,
  canExecute,
  canManage,
} from '../constants/permissions'

export const usePermissions = () => {
  const { user } = useAuth()
  const permissions = user?.permissions || {}
  const isPlatformAdmin = user?.is_platform_admin || false
  const role = user?.role || 'viewer'

  const check = useCallback(
    (resource, action) => {
      if (isPlatformAdmin) return true
      return hasPermission(permissions, resource, action)
    },
    [permissions, isPlatformAdmin]
  )

  const checkView = useCallback(
    (resource) => {
      if (isPlatformAdmin) return true
      return canView(permissions, resource)
    },
    [permissions, isPlatformAdmin]
  )

  const checkCreate = useCallback(
    (resource) => {
      if (isPlatformAdmin) return true
      return canCreate(permissions, resource)
    },
    [permissions, isPlatformAdmin]
  )

  const checkEdit = useCallback(
    (resource) => {
      if (isPlatformAdmin) return true
      return canEdit(permissions, resource)
    },
    [permissions, isPlatformAdmin]
  )

  const checkDelete = useCallback(
    (resource) => {
      if (isPlatformAdmin) return true
      return canDelete(permissions, resource)
    },
    [permissions, isPlatformAdmin]
  )

  const checkExecute = useCallback(
    (resource) => {
      if (isPlatformAdmin) return true
      return canExecute(permissions, resource)
    },
    [permissions, isPlatformAdmin]
  )

  const checkManage = useCallback(
    (resource) => {
      if (isPlatformAdmin) return true
      return canManage(permissions, resource)
    },
    [permissions, isPlatformAdmin]
  )

  const workspaces = useMemo(
    () => ({
      canView: checkView(RESOURCES.WORKSPACES),
      canCreate: checkCreate(RESOURCES.WORKSPACES),
      canEdit: checkEdit(RESOURCES.WORKSPACES),
      canDelete: checkDelete(RESOURCES.WORKSPACES),
    }),
    [checkView, checkCreate, checkEdit, checkDelete]
  )

  const workflows = useMemo(
    () => ({
      canView: checkView(RESOURCES.WORKFLOWS),
      canCreate: checkCreate(RESOURCES.WORKFLOWS),
      canEdit: checkEdit(RESOURCES.WORKFLOWS),
      canDelete: checkDelete(RESOURCES.WORKFLOWS),
      canExecute: checkExecute(RESOURCES.WORKFLOWS),
    }),
    [checkView, checkCreate, checkEdit, checkDelete, checkExecute]
  )

  const agents = useMemo(
    () => ({
      canView: checkView(RESOURCES.AGENTS),
      canCreate: checkCreate(RESOURCES.AGENTS),
      canEdit: checkEdit(RESOURCES.AGENTS),
      canDelete: checkDelete(RESOURCES.AGENTS),
    }),
    [checkView, checkCreate, checkEdit, checkDelete]
  )

  const mcps = useMemo(
    () => ({
      canView: checkView(RESOURCES.MCPS),
      canCreate: checkCreate(RESOURCES.MCPS),
      canEdit: checkEdit(RESOURCES.MCPS),
      canDelete: checkDelete(RESOURCES.MCPS),
    }),
    [checkView, checkCreate, checkEdit, checkDelete]
  )

  const teams = useMemo(
    () => ({
      canView: checkView(RESOURCES.TEAMS),
      canCreate: checkCreate(RESOURCES.TEAMS),
      canEdit: checkEdit(RESOURCES.TEAMS),
      canDelete: checkDelete(RESOURCES.TEAMS),
      canManage: checkManage(RESOURCES.TEAMS),
    }),
    [checkView, checkCreate, checkEdit, checkDelete, checkManage]
  )

  const users = useMemo(
    () => ({
      canView: checkView(RESOURCES.USERS),
      canCreate: checkCreate(RESOURCES.USERS),
      canEdit: checkEdit(RESOURCES.USERS),
      canDelete: checkDelete(RESOURCES.USERS),
    }),
    [checkView, checkCreate, checkEdit, checkDelete]
  )

  const settings = useMemo(
    () => ({
      llmConfigs: {
        canView: checkView(RESOURCES.LLM_CONFIGS),
        canCreate: checkCreate(RESOURCES.LLM_CONFIGS),
        canEdit: checkEdit(RESOURCES.LLM_CONFIGS),
        canDelete: checkDelete(RESOURCES.LLM_CONFIGS),
      },
      integrations: {
        canView: checkView(RESOURCES.INTEGRATIONS),
        canCreate: checkCreate(RESOURCES.INTEGRATIONS),
        canEdit: checkEdit(RESOURCES.INTEGRATIONS),
        canDelete: checkDelete(RESOURCES.INTEGRATIONS),
      },
      ssoConfigs: {
        canView: checkView(RESOURCES.SSO_CONFIGS),
        canCreate: checkCreate(RESOURCES.SSO_CONFIGS),
        canEdit: checkEdit(RESOURCES.SSO_CONFIGS),
        canDelete: checkDelete(RESOURCES.SSO_CONFIGS),
      },
      compliance: {
        canView: checkView(RESOURCES.COMPLIANCE),
        canCreate: checkCreate(RESOURCES.COMPLIANCE),
        canEdit: checkEdit(RESOURCES.COMPLIANCE),
        canDelete: checkDelete(RESOURCES.COMPLIANCE),
      },
    }),
    [checkView, checkCreate, checkEdit, checkDelete]
  )

  const knowledgeBase = useMemo(
    () => ({
      canView: checkView(RESOURCES.KNOWLEDGE_BASE),
      canCreate: checkCreate(RESOURCES.KNOWLEDGE_BASE),
      canEdit: checkEdit(RESOURCES.KNOWLEDGE_BASE),
      canDelete: checkDelete(RESOURCES.KNOWLEDGE_BASE),
    }),
    [checkView, checkCreate, checkEdit, checkDelete]
  )

  const billing = useMemo(
    () => ({
      canView: checkView(RESOURCES.BILLING),
      canEdit: checkEdit(RESOURCES.BILLING),
    }),
    [checkView, checkEdit]
  )

  const organizations = useMemo(
    () => ({
      canView: checkView(RESOURCES.ORGANIZATIONS),
      canCreate: checkCreate(RESOURCES.ORGANIZATIONS),
      canEdit: checkEdit(RESOURCES.ORGANIZATIONS),
      canDelete: checkDelete(RESOURCES.ORGANIZATIONS),
    }),
    [checkView, checkCreate, checkEdit, checkDelete]
  )

  return {
    permissions,
    isPlatformAdmin,
    role,
    check,
    checkView,
    checkCreate,
    checkEdit,
    checkDelete,
    checkExecute,
    checkManage,
    workspaces,
    workflows,
    agents,
    mcps,
    teams,
    users,
    settings,
    knowledgeBase,
    billing,
    organizations,
    RESOURCES,
    ACTIONS,
  }
}

export default usePermissions
