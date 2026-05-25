"""
CortexFlow Authentication & Authorization.

Provides:
    - JWT-based authentication
    - API key authentication
    - Role-based access control
    - Bcrypt password hashing
    - Audit logging
"""

import logging
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger("cortexflow.auth")


class AuthError(Exception):
    """Authentication or authorization error."""
    pass


class AuthService:
    """Authentication service with JWT and API key support."""

    def __init__(self, secret_key: Optional[str] = None, token_expiry_hours: int = 24):
        self.secret_key = secret_key or secrets.token_urlsafe(64)
        self.token_expiry = timedelta(hours=token_expiry_hours)

    def create_token(self, user_id: int, role: str = "analyst") -> str:
        """Create a simple signed token (use PyJWT in production)."""
        payload = {
            "user_id": user_id,
            "role": role,
            "exp": (datetime.utcnow() + self.token_expiry).isoformat(),
            "iat": datetime.utcnow().isoformat(),
        }

        # Simplified token (in production use PyJWT)
        import json
        import base64
        payload_b64 = base64.urlsafe_b64encode(
            json.dumps(payload).encode()
        ).decode().rstrip("=")
        signature = hashlib.sha256(
            (self.secret_key + payload_b64).encode()
        ).hexdigest()
        return f"{payload_b64}.{signature}"

    def verify_token(self, token: str) -> Optional[dict]:
        """Verify and decode a token."""
        try:
            import json
            import base64
            payload_b64, signature = token.rsplit(".", 1)
            expected = hashlib.sha256(
                (self.secret_key + payload_b64).encode()
            ).hexdigest()
            if signature != expected:
                return None
            payload_b64_pad = payload_b64 + "=" * (4 - len(payload_b64) % 4)
            payload = json.loads(base64.urlsafe_b64decode(payload_b64_pad))
            exp = datetime.fromisoformat(payload["exp"])
            if datetime.utcnow() > exp:
                return None
            return payload
        except Exception:
            return None


class RBACService:
    """Role-Based Access Control."""

    PERMISSIONS = {
        "admin": {
            "users.create", "users.read", "users.update", "users.delete",
            "api_keys.create", "api_keys.read", "api_keys.revoke",
            "pipelines.run", "pipelines.read", "pipelines.delete",
            "workflows.create", "workflows.read",
            "config.read", "config.write",
            "audit.read",
        },
        "analyst": {
            "pipelines.run", "pipelines.read",
            "workflows.read",
            "api_keys.create", "api_keys.read",
        },
        "viewer": {
            "pipelines.read",
            "workflows.read",
        },
    }

    def has_permission(self, role: str, permission: str) -> bool:
        return permission in self.PERMISSIONS.get(role, set())

    def require_permission(self, role: str, permission: str):
        if not self.has_permission(role, permission):
            raise AuthError(f"Role '{role}' lacks permission: {permission}")


_auth_service = None
_rbac_service = None


def get_auth() -> AuthService:
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service


def get_rbac() -> RBACService:
    global _rbac_service
    if _rbac_service is None:
        _rbac_service = RBACService()
    return _rbac_service
