from functools import wraps
from fastapi import HTTPException
from typing import Optional
from services.api.admin.src.permissions import Resource, Action


def require_permission(resource: Resource, action: Action):
    """
    Decorator for route-level permission checks.
    Similar to Spring Boot's @PreAuthorize.
    
    Usage:
        @router.post("")
        @require_permission(Resource.WORKFLOWS, Action.CREATE)
        def create_workflow(..., current_user: CurrentUser = Depends(get_current_user)):
            # Permission already checked by decorator
            ...
    
    Note: The decorated function MUST have a 'current_user' parameter
    that is injected via FastAPI's Depends(get_current_user).
    """
    def decorator(func):
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            if current_user is None:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required"
                )
            
            if not current_user.has_permission(resource, action):
                raise HTTPException(
                    status_code=403,
                    detail=f"Permission denied: {action.value} on {resource.value}"
                )
            return func(*args, **kwargs)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            if current_user is None:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required"
                )
            
            if not current_user.has_permission(resource, action):
                raise HTTPException(
                    status_code=403,
                    detail=f"Permission denied: {action.value} on {resource.value}"
                )
            return await func(*args, **kwargs)
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def require_permission_with_owner(
    resource: Resource,
    action: Action,
    owner_id_param: str = "resource_owner_id"
):
    """
    Decorator for permission checks that also consider resource ownership.
    Used for Member role who can edit/delete their own resources.
    
    Usage:
        @router.put("/{workflow_id}")
        @require_permission_with_owner(Resource.WORKFLOWS, Action.EDIT)
        def update_workflow(..., current_user: CurrentUser = Depends(get_current_user)):
            # For Members: only allowed if they own the resource
            # For Admin/Owner: always allowed
            ...
    
    Note: The route handler must set kwargs[owner_id_param] before the check,
    or this decorator should be used with middleware that sets owner info.
    For complex ownership checks, use inline checks in the route handler.
    """
    def decorator(func):
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            if current_user is None:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required"
                )
            
            resource_owner_id = kwargs.get(owner_id_param)
            
            if not current_user.check_permission(resource, action, resource_owner_id):
                raise HTTPException(
                    status_code=403,
                    detail=f"Permission denied: {action.value} on {resource.value}"
                )
            return func(*args, **kwargs)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            if current_user is None:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required"
                )
            
            resource_owner_id = kwargs.get(owner_id_param)
            
            if not current_user.check_permission(resource, action, resource_owner_id):
                raise HTTPException(
                    status_code=403,
                    detail=f"Permission denied: {action.value} on {resource.value}"
                )
            return await func(*args, **kwargs)
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator
