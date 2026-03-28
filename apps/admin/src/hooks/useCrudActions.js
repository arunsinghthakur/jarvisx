import { useState, useCallback } from 'react'

export function createCrudActions(api, entityName, refreshCallbacks = []) {
  return function useCrudActions() {
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState(null)

    const executeAction = useCallback(async (action, actionName) => {
      setLoading(true)
      setError(null)
      try {
        const result = await action()
        for (const callback of refreshCallbacks) {
          if (typeof callback === 'function') {
            await callback()
          }
        }
        return { success: true, data: result }
      } catch (err) {
        const errorMessage = `Failed to ${actionName} ${entityName}: ${err.response?.data?.detail || err.message}`
        setError(errorMessage)
        return { success: false, error: errorMessage }
      } finally {
        setLoading(false)
      }
    }, [])

    const create = useCallback(async (data) => {
      return executeAction(() => api.create(data), 'create')
    }, [executeAction])

    const update = useCallback(async (id, data) => {
      return executeAction(() => api.update(id, data), 'update')
    }, [executeAction])

    const remove = useCallback(async (id) => {
      return executeAction(() => api.delete(id), 'delete')
    }, [executeAction])

    const clearError = useCallback(() => {
      setError(null)
    }, [])

    return {
      loading,
      error,
      create,
      update,
      remove,
      clearError,
      executeAction,
    }
  }
}

export function useCrudActionsWithValidation(api, entityName, validator, refreshCallbacks = []) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const executeAction = useCallback(async (action, actionName) => {
    setLoading(true)
    setError(null)
    try {
      const result = await action()
      for (const callback of refreshCallbacks) {
        if (typeof callback === 'function') {
          await callback()
        }
      }
      return { success: true, data: result }
    } catch (err) {
      const errorMessage = `Failed to ${actionName} ${entityName}: ${err.response?.data?.detail || err.message}`
      setError(errorMessage)
      return { success: false, error: errorMessage }
    } finally {
      setLoading(false)
    }
  }, [entityName, refreshCallbacks])

  const create = useCallback(async (data) => {
    const validationError = validator?.create?.(data)
    if (validationError) {
      setError(validationError)
      return { success: false, error: validationError }
    }
    return executeAction(() => api.create(data), 'create')
  }, [executeAction, validator])

  const update = useCallback(async (id, data) => {
    const validationError = validator?.update?.(data)
    if (validationError) {
      setError(validationError)
      return { success: false, error: validationError }
    }
    return executeAction(() => api.update(id, data), 'update')
  }, [executeAction, validator])

  const remove = useCallback(async (id) => {
    return executeAction(() => api.delete(id), 'delete')
  }, [executeAction])

  const clearError = useCallback(() => {
    setError(null)
  }, [])

  return {
    loading,
    error,
    create,
    update,
    remove,
    clearError,
    executeAction,
  }
}

