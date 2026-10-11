"""Admin authentication endpoints for the admin frontend.

Provides login, session verification, and logout endpoints that match
the admin frontend's expected API contract:
- POST /api/admin/auth/login
- GET /api/admin/auth/me
- POST /api/admin/auth/logout

Uses environment-configured credentials with Argon2id password hashing
and signed/expiring JWT sessions.
"""

from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field

from app.security.authentication import (
    TokenPayload,
    UserContext,
    create_access_token,
    create_refresh_token,
    get_current_user,
    hash_password,
    verify_password,
    decode_token,
)
from app.security.authorization import Permission, Role
from app.security.config import get_security_settings


router = APIRouter(prefix="/api/admin/auth", tags=["admin-auth"])

security_scheme = HTTPBearer(auto_error=False)

settings = get_security_settings()


# ---------------------------------------------------------------------------
# Request/Response Models (matching frontend expectations)
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)


class LoginResponse(BaseModel):
    user: dict
    session_token: str
    refresh_token: str
    expires_in: int


class MeResponse(BaseModel):
    user: dict


class ErrorResponse(BaseModel):
    detail: str


# ---------------------------------------------------------------------------
# Admin User Configuration (from environment)
# ---------------------------------------------------------------------------

def _get_admin_credentials() -> tuple[str, str, str]:
    """Get admin credentials from environment variables.
    
    Returns:
        Tuple of (email, password_hash, role)
        
    Raises:
        RuntimeError: If required environment variables are not set.
    """
    email = os.getenv("ADMIN_EMAIL")
    password = os.getenv("ADMIN_PASSWORD")
    role = os.getenv("ADMIN_ROLE", "ADMIN")
    
    if not email or not password:
        raise RuntimeError(
            "Admin credentials not configured. "
            "Set ADMIN_EMAIL and ADMIN_PASSWORD environment variables. "
            "For local development, copy .env.example to .env and configure values."
        )
    
    return email, password, role


def _create_admin_user(email: str, role: str) -> dict:
    """Create admin user dict matching frontend expectations."""
    return {
        "id": "admin-001",
        "email": email,
        "name": "System Administrator",
        "role": role,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "lastLogin": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Development-only bypass (evaluated at request time)
# ---------------------------------------------------------------------------

def _get_dev_bypass_config() -> tuple[bool, str, str]:
    """Get dev bypass configuration at request time.
    
    Returns:
        Tuple of (enabled, email, password)
    """
    security_settings = get_security_settings()
    enabled = os.getenv("ADMIN_DEV_BYPASS", "false").lower() == "true"
    email = os.getenv("ADMIN_DEV_BYPASS_EMAIL", "dev@example.com")
    password = os.getenv("ADMIN_DEV_BYPASS_PASSWORD", "dev-only-bypass-do-not-use-in-production")
    
    # Safety: never enable bypass in production
    if enabled and security_settings.environment == "production":
        import logging
        logging.getLogger(__name__).warning(
            "ADMIN_DEV_BYPASS ignored: bypass is disabled in production environment"
        )
        enabled = False
    
    return enabled, email, password


# ---------------------------------------------------------------------------
# Login Endpoint
# ---------------------------------------------------------------------------

@router.post(
    "/login",
    response_model=LoginResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid credentials"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def admin_login(
    request: Request,
    response: Response,
    credentials: LoginRequest,
) -> LoginResponse:
    """Authenticate admin user and create session tokens."""
    # Development bypass (only in non-production)
    dev_bypass_enabled, dev_bypass_email, dev_bypass_password = _get_dev_bypass_config()
    if dev_bypass_enabled and credentials.email == dev_bypass_email and credentials.password == dev_bypass_password:
        import logging
        logging.getLogger(__name__).warning(
            "DEVELOPMENT BYPASS USED: Admin login bypassed via ADMIN_DEV_BYPASS. "
            "This MUST NOT be enabled in production."
        )
        user = _create_admin_user(dev_bypass_email, "ADMIN")
        
        # Create server-side session
        from app.security.authentication import create_session
        session_id = create_session(
            user_id=user["id"],
            email=user["email"],
            role=user["role"],
            tenant_id="system",
            permissions=[p.value for p in Permission],
            mfa_verified=True,
        )
        
        access_token = create_access_token(
            user_id=user["id"],
            email=user["email"],
            role=user["role"],
            tenant_id="system",
            permissions=[p.value for p in Permission],
            mfa_verified=True,
            session_id=session_id,
        )
        refresh_token = create_refresh_token(
            user_id=user["id"],
            tenant_id="system",
            session_id=session_id,
        )
        from app.security.authentication import set_auth_cookies
        set_auth_cookies(response, access_token, refresh_token)
        return LoginResponse(
            user=user,
            session_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.session_max_age_seconds,
        )
    
    # Normal authentication flow
    try:
        admin_email, admin_password_hash, admin_role = _get_admin_credentials()
    except RuntimeError as e:
        import logging
        logging.getLogger(__name__).error("Admin auth configuration error: %s", e)
        if get_security_settings().environment == "development":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service not configured. Set ADMIN_EMAIL and ADMIN_PASSWORD in .env"
            )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable"
        )
    
    if credentials.email != admin_email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    if not verify_password(credentials.password, admin_password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    user = _create_admin_user(admin_email, admin_role)
    
    if admin_role == "ADMIN":
        permissions = [p.value for p in Permission]
    elif admin_role == "SUPER_ADMIN":
        permissions = [p.value for p in Permission]
    else:
        permissions = [
            Permission.DASHBOARD_READ.value,
            Permission.RESEARCH_READ.value,
            Permission.EVIDENCE_READ.value,
            Permission.DATASET_READ.value,
            Permission.MODEL_READ.value,
            Permission.TENANT_READ.value,
            Permission.AUDIT_READ.value,
        ]
    
    # Create server-side session
    from app.security.authentication import create_session
    session_id = create_session(
        user_id=user["id"],
        email=user["email"],
        role=user["role"],
        tenant_id="system",
        permissions=permissions,
        mfa_verified=True,
    )
    
    access_token = create_access_token(
        user_id=user["id"],
        email=user["email"],
        role=user["role"],
        tenant_id="system",
        permissions=permissions,
        mfa_verified=True,
        session_id=session_id,
    )
    refresh_token = create_refresh_token(
        user_id=user["id"],
        tenant_id="system",
        session_id=session_id,
    )
    
    from app.security.authentication import set_auth_cookies
    set_auth_cookies(response, access_token, refresh_token)
    
    return LoginResponse(
        user=user,
        session_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.session_max_age_seconds,
    )


# ---------------------------------------------------------------------------
# Session Verification Endpoint
# ---------------------------------------------------------------------------

@router.get(
    "/me",
    response_model=MeResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
)
async def admin_me(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> MeResponse:
    """Get current authenticated admin user."""
    try:
        user_context = get_current_user(request, credentials)
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if user_context.role not in ("ADMIN", "SUPER_ADMIN"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    user = _create_admin_user(user_context.email, user_context.role)
    return MeResponse(user=user)


# ---------------------------------------------------------------------------
# Logout Endpoint
# ---------------------------------------------------------------------------

@router.post(
    "/logout",
    responses={
        200: {"description": "Successfully logged out"},
    },
)
async def admin_logout(
    request: Request,
    response: Response,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> dict:
    """Invalidate admin session."""
    from app.security.authentication import clear_auth_cookies
    clear_auth_cookies(response)
    return {"message": "Logged out successfully"}


# ---------------------------------------------------------------------------
# Token Refresh Endpoint
# ---------------------------------------------------------------------------

@router.post(
    "/refresh",
    response_model=LoginResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid or expired refresh token"},
    },
)
async def admin_refresh(
    request: Request,
    response: Response,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> LoginResponse:
    """Refresh access token using refresh token."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        payload = decode_token(credentials.credentials)
        
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        user_id = payload.get("sub")
        tenant_id = payload.get("tenant_id")
        session_id = payload.get("session_id")
        
        if not user_id or not tenant_id or not session_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Get session data (contains user info)
        from app.security.authentication import get_session
        session = get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired or revoked"
            )
        
        # Use session data for user info
        user = _create_admin_user(session["email"], session["role"])
        permissions = session["permissions"]
        
        new_access_token = create_access_token(
            user_id=user_id,
            email=user["email"],
            role=user["role"],
            tenant_id=tenant_id,
            permissions=permissions,
            mfa_verified=True,
            session_id=session_id,
        )
        new_refresh_token = create_refresh_token(
            user_id=user_id,
            tenant_id=tenant_id,
            session_id=session_id,
        )
        
        from app.security.authentication import set_auth_cookies
        set_auth_cookies(response, new_access_token, new_refresh_token)
        
        return LoginResponse(
            user=user,
            session_token=new_access_token,
            refresh_token=new_refresh_token,
            expires_in=settings.session_max_age_seconds,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.getLogger(__name__).error("Token refresh failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )