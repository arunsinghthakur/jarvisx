from fastapi import Header, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional, Callable

from jarvisx.database.models import Organization, User
from jarvisx.database.session import get_db
from services.api.admin.src.auth import decode_access_token
from services.api.admin.src.utils.cookies import get_access_token_from_request
from services.api.admin.src.permissions import (
    Resource, Action, has_permission, get_user_permissions, check_permission
)

security = HTTPBearer(auto_error=False)


class AuthContext:
    
    def __init__(self, organization: Organization, is_platform_admin: bool):
        self.organization = organization
        self.organization_id = organization.id
        self.is_platform_admin = is_platform_admin

    def can_access_organization(self, org_id: str) -> bool:
        if self.is_platform_admin:
            return True
        return self.organization_id == org_id

    def can_manage_system_resources(self) -> bool:
        return self.is_platform_admin

    def can_access_resource(self, owner_org_id: Optional[str], is_system: bool) -> bool:
        if self.is_platform_admin:
            return True
        if is_system:
            return True
        if owner_org_id is None:
            return True
        return owner_org_id == self.organization_id

    def can_modify_resource(self, owner_org_id: Optional[str], is_system: bool) -> bool:
        if self.is_platform_admin:
            return True
        if is_system:
            return False
        if owner_org_id is None:
            return False
        return owner_org_id == self.organization_id


class CurrentUser(AuthContext):
    
    def __init__(self, user: User, organization: Organization, is_platform_admin: bool):
        super().__init__(organization, is_platform_admin)
        self.user = user
        self.user_id = user.id
        self.role = user.effective_role
        self._permissions = None

    def is_owner_or_admin(self) -> bool:
        return self.role in ["owner", "admin"]

    def has_permission(self, resource: Resource, action: Action) -> bool:
        return has_permission(self.role, resource, action, self.is_platform_admin)

    def check_permission(
        self,
        resource: Resource,
        action: Action,
        resource_owner_id: Optional[str] = None
    ) -> bool:
        return check_permission(
            self.role, resource, action, self.is_platform_admin,
            resource_owner_id, self.user_id
        )

    def require_permission(self, resource: Resource, action: Action) -> None:
        if not self.has_permission(resource, action):
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied: {action.value} on {resource.value} requires higher privileges"
            )

    def require_permission_with_owner(
        self,
        resource: Resource,
        action: Action,
        resource_owner_id: Optional[str] = None
    ) -> None:
        if not self.check_permission(resource, action, resource_owner_id):
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied: {action.value} on {resource.value} requires ownership or higher privileges"
            )

    def get_permissions(self) -> dict:
        if self._permissions is None:
            self._permissions = get_user_permissions(self.role, self.is_platform_admin)
        return self._permissions


class OrganizationContext(AuthContext):
    
    def __init__(self, organization: Organization, is_platform_admin: bool, user: Optional[User] = None):
        super().__init__(organization, is_platform_admin)
        self.user = user


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> CurrentUser:
    token = get_access_token_from_request(request)
    
    if not token and credentials:
        token = credentials.credentials
    
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    payload = decode_access_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User account is disabled")
    
    organization = db.query(Organization).filter(Organization.id == user.organization_id).first()
    
    if not organization:
        raise HTTPException(status_code=403, detail="Organization not found")
    
    if not organization.is_active:
        raise HTTPException(status_code=403, detail="Organization is not active")
    
    return CurrentUser(
        user=user,
        organization=organization,
        is_platform_admin=organization.is_platform_admin
    )


async def get_optional_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[CurrentUser]:
    token = get_access_token_from_request(request)
    
    if not token and not credentials:
        return None
    
    try:
        return await get_current_user(request, credentials, db)
    except HTTPException:
        return None


async def get_organization_context(
    current_user: CurrentUser = Depends(get_current_user)
) -> OrganizationContext:
    return OrganizationContext(
        organization=current_user.organization,
        is_platform_admin=current_user.is_platform_admin,
        user=current_user.user
    )


async def get_optional_organization_context(
    current_user: Optional[CurrentUser] = Depends(get_optional_current_user)
) -> Optional[OrganizationContext]:
    if not current_user:
        return None

    return OrganizationContext(
        organization=current_user.organization,
        is_platform_admin=current_user.is_platform_admin,
        user=current_user.user
    )


async def require_admin(
    current_user: CurrentUser = Depends(get_current_user)
) -> User:
    """
    Dependency that requires user to be admin or owner
    """
    if not current_user.is_owner_or_admin():
        raise HTTPException(
            status_code=403,
            detail="Admin or owner role required"
        )
    return current_user.user


async def require_platform_admin(
    current_user: CurrentUser = Depends(get_current_user)
) -> User:
    if not current_user.is_platform_admin:
        raise HTTPException(
            status_code=403,
            detail="Platform administrator access required"
        )
    return current_user.user


def require_permission(resource: Resource, action: Action) -> Callable:
    async def permission_checker(
        current_user: CurrentUser = Depends(get_current_user)
    ) -> CurrentUser:
        current_user.require_permission(resource, action)
        return current_user
    return permission_checker


def require_view_permission(resource: Resource) -> Callable:
    return require_permission(resource, Action.VIEW)


def require_create_permission(resource: Resource) -> Callable:
    return require_permission(resource, Action.CREATE)


def require_edit_permission(resource: Resource) -> Callable:
    return require_permission(resource, Action.EDIT)


def require_delete_permission(resource: Resource) -> Callable:
    return require_permission(resource, Action.DELETE)
