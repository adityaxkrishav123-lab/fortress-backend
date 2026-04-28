"""
auth_gate/dependencies.py
FastAPI dependency factories for role-based access control.

Usage in route handlers:
    @router.get("/ngo/members")
    async def list_members(request: Request, _=Depends(require_role(Role.NGO_ADMIN))):
        ...
"""

from fastapi import Depends, HTTPException, Request, status
from .models import Role


def require_role(*allowed_roles: Role):
    """
    Dependency that blocks the request with 403 if the caller's role
    (injected by AuthGateMiddleware) is not in `allowed_roles`.
    """
    async def _check(request: Request):
        caller_role = getattr(request.state, "role", None)
        if caller_role not in [r.value for r in allowed_roles]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role(s): {[r.value for r in allowed_roles]}",
            )
        return caller_role
    return _check


def require_self_or_admin():
    """
    Dependency that allows the request only if:
      - The caller is an NGO_ADMIN, OR
      - The caller's uid matches the target uid in the path.
    """
    async def _check(request: Request, uid: str):
        caller_uid = getattr(request.state, "uid", None)
        caller_role = getattr(request.state, "role", None)
        if caller_role != Role.NGO_ADMIN.value and caller_uid != uid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only access your own profile.",
            )
    return _check
