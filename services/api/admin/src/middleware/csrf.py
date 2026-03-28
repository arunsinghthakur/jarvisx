from fastapi import Request, HTTPException
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
from services.api.admin.src.utils.cookies import validate_csrf_token
import logging

logger = logging.getLogger(__name__)

CSRF_SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}

CSRF_EXEMPT_PATHS = {
    "/api/auth/login",
    "/api/auth/refresh",
    "/api/auth/sso/initiate",
    "/api/auth/sso/callback",
    "/api/auth/sso/discover",
    "/api/auth/sso/saml/acs",
    "/api/auth/forgot-password",
    "/api/auth/reset-password",
    "/api/teams/forgot-password",
    "/api/teams/reset-password",
    "/health",
    "/",
}


def is_csrf_exempt(path: str) -> bool:
    if path in CSRF_EXEMPT_PATHS:
        return True
    
    for exempt_path in CSRF_EXEMPT_PATHS:
        if path.startswith(exempt_path):
            return True
    
    return False


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method in CSRF_SAFE_METHODS:
            return await call_next(request)
        
        if is_csrf_exempt(request.url.path):
            return await call_next(request)
        
        has_cookie_auth = request.cookies.get("access_token") is not None
        
        if has_cookie_auth:
            if not validate_csrf_token(request):
                logger.warning(f"CSRF validation failed for {request.method} {request.url.path}")
                raise HTTPException(status_code=403, detail="CSRF token validation failed")
        
        return await call_next(request)
