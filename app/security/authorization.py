"""Authorization module - RBAC permissions and roles."""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Set


class Permission(str, Enum):
    """Fine-grained permissions for the system."""

    # Dashboard permissions
    DASHBOARD_READ = "dashboard:read"
    DASHBOARD_WRITE = "dashboard:write"

    # Research permissions
    RESEARCH_READ = "research:read"
    RESEARCH_WRITE = "research:write"
    RESEARCH_EXECUTE = "research:execute"
    RESEARCH_DELETE = "research:delete"

    # Evidence permissions
    EVIDENCE_READ = "evidence:read"
    EVIDENCE_WRITE = "evidence:write"
    EVIDENCE_DELETE = "evidence:delete"
    EVIDENCE_UPLOAD = "evidence:upload"

    # Dataset permissions
    DATASET_READ = "dataset:read"
    DATASET_WRITE = "dataset:write"
    DATASET_DELETE = "dataset:delete"
    DATASET_UPLOAD = "dataset:upload"

    # Model permissions
    MODEL_READ = "model:read"
    MODEL_WRITE = "model:write"
    MODEL_DELETE = "model:delete"
    MODEL_DEPLOY = "model:deploy"
    MODEL_BACKTEST = "model:backtest"

    # Admin permissions
    ADMIN_USERS = "admin:users"
    ADMIN_TENANTS = "admin:tenants"
    ADMIN_SYSTEM = "admin:system"
    ADMIN_AUDIT = "admin:audit"
    ADMIN_SECURITY = "admin:security"

    # Tenant permissions
    TENANT_READ = "tenant:read"
    TENANT_WRITE = "tenant:write"
    TENANT_DELETE = "tenant:delete"
    TENANT_MEMBERS = "tenant:members"

    # System permissions
    SYSTEM_CONFIG = "system:config"
    SYSTEM_MONITORING = "system:monitoring"
    SYSTEM_LOGS = "system:logs"

    # Audit permissions
    AUDIT_READ = "audit:read"
    AUDIT_EXPORT = "audit:export"

    # Security permissions
    SECURITY_MFA = "security:mfa"
    SECURITY_SESSIONS = "security:sessions"
    SECURITY_API_KEYS = "security:api_keys"


class Role(str, Enum):
    """System roles with hierarchical permissions."""

    # Tenant-scoped roles
    VIEWER = "VIEWER"
class Role(str, Enum):
    """System roles with hierarchical permissions."""

    # Tenant-scoped roles
    VIEWER = "VIEWER"
    ANALYST = "ANALYST"
    RESEARCHER = "RESEARCHER"
    DATA_ENGINEER = "DATA_ENGINEER"
    MODEL_ENGINEER = "MODEL_ENGINEER"
    TENANT_ADMIN = "TENANT_ADMIN"

    # System-wide roles
    ADMIN = "ADMIN"
    SUPER_ADMIN = "SUPER_ADMIN"


# Role-to-permission mapping
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.VIEWER: {
        Permission.DASHBOARD_READ,
        Permission.RESEARCH_READ,
        Permission.EVIDENCE_READ,
        Permission.DATASET_READ,
        Permission.MODEL_READ,
        Permission.TENANT_READ,
        Permission.AUDIT_READ,
    },
    Role.ANALYST: {
        Permission.DASHBOARD_READ,
        Permission.DASHBOARD_WRITE,
        Permission.RESEARCH_READ,
        Permission.RESEARCH_WRITE,
        Permission.EVIDENCE_READ,
        Permission.EVIDENCE_WRITE,
        Permission.DATASET_READ,
        Permission.DATASET_WRITE,
        Permission.MODEL_READ,
        Permission.TENANT_READ,
        Permission.AUDIT_READ,
    },
    Role.RESEARCHER: {
        Permission.DASHBOARD_READ,
        Permission.DASHBOARD_WRITE,
        Permission.RESEARCH_READ,
        Permission.RESEARCH_WRITE,
        Permission.RESEARCH_EXECUTE,
        Permission.EVIDENCE_READ,
        Permission.EVIDENCE_WRITE,
        Permission.EVIDENCE_UPLOAD,
        Permission.DATASET_READ,
        Permission.DATASET_WRITE,
        Permission.DATASET_UPLOAD,
        Permission.MODEL_READ,
        Permission.MODEL_WRITE,
        Permission.MODEL_BACKTEST,
        Permission.TENANT_READ,
        Permission.AUDIT_READ,
    },
    Role.DATA_ENGINEER: {
        Permission.DASHBOARD_READ,
        Permission.DASHBOARD_WRITE,
        Permission.RESEARCH_READ,
        Permission.RESEARCH_WRITE,
        Permission.EVIDENCE_READ,
        Permission.EVIDENCE_WRITE,
        Permission.EVIDENCE_UPLOAD,
        Permission.EVIDENCE_DELETE,
        Permission.DATASET_READ,
        Permission.DATASET_WRITE,
        Permission.DATASET_UPLOAD,
        Permission.DATASET_DELETE,
        Permission.MODEL_READ,
        Permission.TENANT_READ,
        Permission.AUDIT_READ,
    },
    Role.MODEL_ENGINEER: {
        Permission.DASHBOARD_READ,
        Permission.DASHBOARD_WRITE,
        Permission.RESEARCH_READ,
        Permission.RESEARCH_WRITE,
        Permission.RESEARCH_EXECUTE,
        Permission.EVIDENCE_READ,
        Permission.DATASET_READ,
        Permission.DATASET_WRITE,
        Permission.MODEL_READ,
        Permission.MODEL_WRITE,
        Permission.MODEL_DEPLOY,
        Permission.MODEL_BACKTEST,
        Permission.TENANT_READ,
        Permission.AUDIT_READ,
    },
    Role.TENANT_ADMIN: {
        Permission.DASHBOARD_READ,
        Permission.DASHBOARD_WRITE,
        Permission.RESEARCH_READ,
        Permission.RESEARCH_WRITE,
        Permission.RESEARCH_EXECUTE,
        Permission.RESEARCH_DELETE,
        Permission.EVIDENCE_READ,
        Permission.EVIDENCE_WRITE,
        Permission.EVIDENCE_UPLOAD,
        Permission.EVIDENCE_DELETE,
        Permission.DATASET_READ,
        Permission.DATASET_WRITE,
        Permission.DATASET_UPLOAD,
        Permission.DATASET_DELETE,
        Permission.MODEL_READ,
        Permission.MODEL_WRITE,
        Permission.MODEL_DEPLOY,
        Permission.MODEL_BACKTEST,
        Permission.TENANT_READ,
        Permission.TENANT_WRITE,
        Permission.TENANT_MEMBERS,
        Permission.ADMIN_USERS,
        Permission.AUDIT_READ,
        Permission.AUDIT_EXPORT,
    },
    Role.ADMIN: {
        Permission.DASHBOARD_READ,
        Permission.DASHBOARD_WRITE,
        Permission.RESEARCH_READ,
        Permission.RESEARCH_WRITE,
        Permission.RESEARCH_EXECUTE,
        Permission.RESEARCH_DELETE,
        Permission.EVIDENCE_READ,
        Permission.EVIDENCE_WRITE,
        Permission.EVIDENCE_UPLOAD,
        Permission.EVIDENCE_DELETE,
        Permission.DATASET_READ,
        Permission.DATASET_WRITE,
        Permission.DATASET_UPLOAD,
        Permission.DATASET_DELETE,
        Permission.MODEL_READ,
        Permission.MODEL_WRITE,
        Permission.MODEL_DEPLOY,
        Permission.MODEL_BACKTEST,
        Permission.ADMIN_USERS,
        Permission.ADMIN_TENANTS,
        Permission.ADMIN_SYSTEM,
        Permission.ADMIN_AUDIT,
        Permission.ADMIN_SECURITY,
        Permission.TENANT_READ,
        Permission.TENANT_WRITE,
        Permission.TENANT_DELETE,
        Permission.TENANT_MEMBERS,
        Permission.SYSTEM_CONFIG,
        Permission.SYSTEM_MONITORING,
        Permission.SYSTEM_LOGS,
        Permission.AUDIT_READ,
        Permission.AUDIT_EXPORT,
        Permission.SECURITY_MFA,
        Permission.SECURITY_SESSIONS,
        Permission.SECURITY_API_KEYS,
    },
    Role.SUPER_ADMIN: {
        *Permission.__members__.values(),
    },
}


def get_permissions_for_role(role: Role) -> Set[Permission]:
    """Get all permissions for a given role."""
    return ROLE_PERMISSIONS.get(role, set())


def check_permission(user_permissions: List[str], required_permission: Permission) -> bool:
    """Check if user has the required permission."""
    return required_permission.value in user_permissions


def check_any_permission(user_permissions: List[str], required_permissions: List[Permission]) -> bool:
    """Check if user has any of the required permissions."""
    user_perms = set(user_permissions)
    return any(p.value in user_perms for p in required_permissions)


def check_all_permissions(user_permissions: List[str], required_permissions: List[Permission]) -> bool:
    """Check if user has all required permissions."""
    user_perms = set(user_permissions)
    return all(p.value in user_perms for p in required_permissions)


def get_role_hierarchy() -> Dict[Role, int]:
    """Get role hierarchy levels (higher = more permissions)."""
    return {
        Role.VIEWER: 10,
        Role.ANALYST: 20,
        Role.DATA_ENGINEER: 30,
        Role.RESEARCHER: 30,
        Role.MODEL_ENGINEER: 35,
        Role.TENANT_ADMIN: 50,
        Role.ADMIN: 80,
        Role.SUPER_ADMIN: 100,
    }


def role_has_minimum_level(user_role: Role, minimum_role: Role) -> bool:
    """Check if user's role meets minimum required role level."""
    hierarchy = get_role_hierarchy()
    return hierarchy.get(user_role, 0) >= hierarchy.get(minimum_role, 0)


def expand_permissions(permissions: List[str]) -> List[str]:
    """Expand wildcard permissions (e.g., 'research:*')."""
    expanded = []
    for perm in permissions:
        if perm.endswith(":*"):
            prefix = perm[:-1]
            for p in Permission:
                if p.value.startswith(prefix):
                    expanded.append(p.value)
        else:
            expanded.append(perm)
    return list(set(expanded))
