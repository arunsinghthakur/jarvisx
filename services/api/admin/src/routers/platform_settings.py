from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from services.api.admin.src.dependencies import get_current_user, CurrentUser

router = APIRouter(prefix="/api/platform/settings", tags=["platform-settings"])


def _require_platform_admin(current_user: CurrentUser):
    if not current_user.is_platform_admin:
        raise HTTPException(status_code=403, detail="Platform admin access required")


class SettingUpdate(BaseModel):
    value: Any


class SettingResponse(BaseModel):
    id: str
    category: str
    key: str
    value: Any
    value_type: str
    description: Optional[str] = None
    updated_at: Optional[str] = None


@router.get("")
def get_all_settings(current_user: CurrentUser = Depends(get_current_user)):
    _require_platform_admin(current_user)
    from jarvisx.services.platform_settings import PlatformSettingsService
    return PlatformSettingsService.get_all()


@router.get("/{category}")
def get_category_settings(category: str, current_user: CurrentUser = Depends(get_current_user)):
    _require_platform_admin(current_user)
    from jarvisx.services.platform_settings import PlatformSettingsService
    return PlatformSettingsService.get_category(category)


@router.put("/{category}/{key}")
def update_setting(
    category: str,
    key: str,
    body: SettingUpdate,
    current_user: CurrentUser = Depends(get_current_user),
):
    _require_platform_admin(current_user)
    from jarvisx.services.platform_settings import PlatformSettingsService
    try:
        result = PlatformSettingsService.set(category, key, body.value, updated_by=current_user.user_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
