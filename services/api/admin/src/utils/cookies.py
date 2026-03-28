from fastapi import Response, Request
from typing import Optional
import secrets

from jarvisx.config.configs import (
    COOKIE_DOMAIN,
    SECURE_COOKIES,
    ACCESS_TOKEN_MAX_AGE,
    REFRESH_TOKEN_MAX_AGE,
    CSRF_TOKEN_MAX_AGE,
    COOKIE_SAMESITE_ACCESS,
    COOKIE_SAMESITE_REFRESH,
    COOKIE_SAMESITE_CSRF,
)


def set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str,
    csrf_token: Optional[str] = None
) -> None:
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=SECURE_COOKIES,
        samesite="lax",
        max_age=ACCESS_TOKEN_MAX_AGE,
        path="/",
        domain=COOKIE_DOMAIN
    )
    
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=SECURE_COOKIES,
        samesite="lax",
        max_age=REFRESH_TOKEN_MAX_AGE,
        path="/",
        domain=COOKIE_DOMAIN
    )
    
    if csrf_token:
        response.set_cookie(
            key="csrf_token",
            value=csrf_token,
            httponly=False,
            secure=SECURE_COOKIES,
            samesite="lax",
            max_age=CSRF_TOKEN_MAX_AGE,
            path="/",
            domain=COOKIE_DOMAIN
        )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(
        key="access_token",
        path="/",
        domain=COOKIE_DOMAIN
    )
    response.delete_cookie(
        key="refresh_token",
        path="/",
        domain=COOKIE_DOMAIN
    )
    response.delete_cookie(
        key="csrf_token",
        path="/",
        domain=COOKIE_DOMAIN
    )


def get_access_token_from_request(request: Request) -> Optional[str]:
    token = request.cookies.get("access_token")
    if token:
        return token
    
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.replace("Bearer ", "")
    
    return None


def get_refresh_token_from_request(request: Request) -> Optional[str]:
    return request.cookies.get("refresh_token")


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def get_csrf_token_from_request(request: Request) -> Optional[str]:
    csrf_header = request.headers.get("x-csrf-token")
    if csrf_header:
        return csrf_header
    return None


def validate_csrf_token(request: Request) -> bool:
    cookie_csrf = request.cookies.get("csrf_token")
    header_csrf = get_csrf_token_from_request(request)
    
    if not cookie_csrf or not header_csrf:
        return False
    
    return secrets.compare_digest(cookie_csrf, header_csrf)
