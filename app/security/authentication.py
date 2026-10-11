"""Authentication module - JWT tokens, Argon2id password hashing, session management."""

from __future__ import annotations

import hashlib
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from passlib.context import CryptContext
from jose import jwt, JWTError
from fastapi import HTTPException, status, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.security.config import get_security_settings


settings = get_security_settings()

# Argon2id password hashing context
pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
    argon2__time_cost=settings.argon2_time_cost,
    argon2__memory_cost=settings.argon2_memory_cost,
    argon2__parallelism=settings.argon2_parallelism,
    argon2__hash_len=settings.argon2_hash_len,
    argon2__salt_size=settings.argon2_salt_len,
)

# HTTP Bearer token scheme for API authentication
security_scheme = HTTPBearer(auto_error=False)


class TokenPayload:
    """JWT token payload structure."""
    sub: str  # user_id
    email: str
    role: str
    tenant_id: str
    permissions: list[str]
    exp: int
    iat: int
    jti: str  # token ID for revocation


class UserContext:
    """Authenticated user context for request."""
    user_id: str
    email: str
    role: str
    tenant_id: str
    permissions: list[str]
    mfa_verified: bool = False
    session_id: Optional[str] = None

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions

    def has_role(self, role: str) -> bool:
        return self.role == role

    def is_admin(self) -> bool:
        return self.role == "ADMIN"


def hash_password(password: str) -> str:
    """Hash a password using Argon2id."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its Argon2id hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    user_id: str,
    email: str,
    role: str,
    tenant_id: str,
    permissions: list[str],
    mfa_verified: bool = False,
    session_id: Optional[str] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a JWT access token."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    
    jti = secrets.token_urlsafe(16)
    
    to_encode = {
        "sub": user_id,
        "email": email,
        "role": role,
        "tenant_id": tenant_id,
        "permissions": permissions,
        "mfa_verified": mfa_verified,
        "session_id": session_id,
        "exp": int(expire.timestamp()),
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "jti": jti,
        "type": "access",
    }
    
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(
    user_id: str,
    tenant_id: str,
    session_id: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a JWT refresh token."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_token_expire_days)
    
    jti = secrets.token_urlsafe(16)
    
    to_encode = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "session_id": session_id,
        "exp": int(expire.timestamp()),
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "jti": jti,
        "type": "refresh",
    }
    
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError:
        return None


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate an access token specifically."""
    payload = decode_token(token)
    if payload and payload.get("type") == "access":
        return payload
    return None


def decode_refresh_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a refresh token specifically."""
    payload = decode_token(token)
    if payload and payload.get("type") == "refresh":
        return payload
    return None


# In-memory session store (replace with Redis in production)
_session_store: Dict[str, Dict[str, Any]] = {}
_revoked_tokens: set = set()


def create_session(
    user_id: str,
    email: str,
    role: str,
    tenant_id: str,
    permissions: list[str],
    mfa_verified: bool = False,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> str:
    """Create a new server-side session."""
    session_id = secrets.token_urlsafe(32)
    now = time.time()
    
    _session_store[session_id] = {
        "user_id": user_id,
        "email": email,
        "role": role,
        "tenant_id": tenant_id,
        "permissions": permissions,
        "mfa_verified": mfa_verified,
        "created_at": now,
        "last_activity": now,
        "ip_address": ip_address,
        "user_agent": user_agent,
        "revoked": False,
    }
    
    return session_id


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Get session data if valid and not expired."""
    session = _session_store.get(session_id)
    if not session:
        return None
    
    if session.get("revoked", False):
        return None
    
    now = time.time()
    
    # Check idle timeout
    if now - session["last_activity"] > settings.session_idle_timeout_seconds:
        revoke_session(session_id)
        return None
    
    # Check max age
    if now - session["created_at"] > settings.session_max_age_seconds:
        revoke_session(session_id)
        return None
    
    # Update last activity
    session["last_activity"] = now
    return session


def revoke_session(session_id: str) -> bool:
    """Revoke a session."""
    if session_id in _session_store:
        _session_store[session_id]["revoked"] = True
        return True
    return False


def revoke_all_user_sessions(user_id: str) -> int:
    """Revoke all sessions for a user. Returns count of revoked sessions."""
    count = 0
    for session_id, session in _session_store.items():
        if session["user_id"] == user_id and not session.get("revoked", False):
            session["revoked"] = True
            count += 1
    return count


def revoke_token(jti: str) -> None:
    """Add token to revocation list."""
    _revoked_tokens.add(jti)


def is_token_revoked(jti: str) -> bool:
    """Check if a token is revoked."""
    return jti in _revoked_tokens


def cleanup_expired_sessions() -> int:
    """Clean up expired sessions and revoked tokens. Returns count cleaned."""
    now = time.time()
    cleaned = 0

    # Clean expired sessions
    expired_sessions = [
        sid for sid, sess in _session_store.items()
        if sess.get("revoked", False)
        or (now - sess["last_activity"] > settings.session_idle_timeout_seconds)
        or (now - sess["created_at"] > settings.session_max_age_seconds)
    ]
    for sid in expired_sessions:
        del _session_store[sid]
        cleaned += 1

    return cleaned


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> UserContext:
    """Get current authenticated user from JWT token or session cookie."""
    token = None
    
    # Try Authorization header first
    if credentials:
        token = credentials.credentials
    
    # Try session cookie
    if not token:
        token = request.cookies.get(settings.session_cookie_name)
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check token revocation
    jti = payload.get("jti")
    if jti and is_token_revoked(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify session if session_id present
    session_id = payload.get("session_id")
    if session_id:
        session = get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired or revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    return UserContext(
        user_id=payload["sub"],
        email=payload["email"],
        role=payload["role"],
        tenant_id=payload["tenant_id"],
        permissions=payload["permissions"],
        mfa_verified=payload.get("mfa_verified", False),
        session_id=session_id,
    )


def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> Optional[UserContext]:
    """Get current user if authenticated, otherwise return None."""
    try:
        return get_current_user(request, credentials)
    except HTTPException:
        return None


def require_admin(user: UserContext = Depends(get_current_user)) -> UserContext:
    """Require ADMIN role."""
    if not user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


def require_role(*roles: str):
    """Dependency factory for role requirements."""
    def _require_role(user: UserContext = Depends(get_current_user)) -> UserContext:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Requires one of roles: " + ", ".join(roles),
            )
        return user
    return _require_role


def require_mfa_verified(user: UserContext = Depends(get_current_user)) -> UserContext:
    """Require MFA verification for sensitive operations."""
    if not user.mfa_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="MFA verification required",
        )
    return user


def set_auth_cookies(response, access_token: str, refresh_token: str) -> None:
    """Set secure HttpOnly cookies for authentication."""
    response.set_cookie(
        key=settings.session_cookie_name,
        value=access_token,
        max_age=settings.session_max_age_seconds,
        httponly=settings.session_cookie_httponly,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        domain=settings.session_cookie_domain,
        path=settings.session_cookie_path,
    )
    
    response.set_cookie(
        key=settings.session_cookie_name + "_refresh",
        value=refresh_token,
        max_age=settings.jwt_refresh_token_expire_days * 86400,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        domain=settings.session_cookie_domain,
        path=settings.session_cookie_path,
    )


def clear_auth_cookies(response) -> None:
    """Clear authentication cookies."""
    response.delete_cookie(
        key=settings.session_cookie_name,
        domain=settings.session_cookie_domain,
        path=settings.session_cookie_path,
    )
    response.delete_cookie(
        key=settings.session_cookie_name + "_refresh",
        domain=settings.session_cookie_domain,
        path=settings.session_cookie_path,
    )


def generate_csrf_token() -> str:
    """Generate a CSRF token."""
    return secrets.token_urlsafe(32)


def verify_csrf_token(token: str, stored_token: str) -> bool:
    """Verify a CSRF token using constant-time comparison."""
    return secrets.compare_digest(token, stored_token)
