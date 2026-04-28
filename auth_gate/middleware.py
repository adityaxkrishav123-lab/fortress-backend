"""
auth_gate/middleware.py
FastAPI JWT Middleware — The Bouncer.

Responsibilities (per spec):
  - Extract Firebase JWT from Authorization header.
  - Decode and verify it (using PyJWT + Firebase public keys).
  - Attach uid, role, and ngo_id to request.state for downstream use.
  - Block requests missing a valid token (401).
  - The logistics engine (main.py, dispatch/, citizen_pipeline/) is NOT touched.
    This middleware runs IN FRONT of those systems.

Note: Role-level access control (403) is enforced in individual route handlers,
      not here, to keep the middleware lean and the logic explicit.
"""

import os
import httpx
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import jwt

# ---------------------------------------------------------------------------
# Firebase public key endpoint
# ---------------------------------------------------------------------------
FIREBASE_PUBLIC_KEYS_URL = (
    "https://www.googleapis.com/robot/v1/metadata/x509/"
    "securetoken@system.gserviceaccount.com"
)

# Project ID from environment — set via FIREBASE_PROJECT_ID env var
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "")

# Routes that do NOT require a Firebase JWT (public endpoints)
PUBLIC_PATHS = {
    "/api/v1/auth/register/preflight",
    "/api/v1/auth/verify/ngo",
    "/api/v1/auth/ngo/validate-referral",   # referral check happens before sign-in
    "/docs",
    "/openapi.json",
    "/redoc",
}


async def _fetch_firebase_public_keys() -> dict:
    """Fetch current Firebase RSA public keys."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(FIREBASE_PUBLIC_KEYS_URL)
        resp.raise_for_status()
        return resp.json()


def _decode_firebase_token(token: str, public_keys: dict) -> dict:
    """
    Decode and verify a Firebase ID token.

    Args:
        token:       Raw JWT string from Authorization header.
        public_keys: Dict of kid → PEM certificate strings.

    Returns:
        Decoded payload dict containing uid, email, etc.

    Raises:
        HTTPException 401 on any verification failure.
    """
    try:
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        if kid not in public_keys:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Firebase token key ID not recognized",
            )
        public_key = public_keys[kid]
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=FIREBASE_PROJECT_ID,
            issuer=f"https://securetoken.google.com/{FIREBASE_PROJECT_ID}",
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Firebase token expired"
        )
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Firebase token: {exc}",
        )


class AuthGateMiddleware(BaseHTTPMiddleware):
    """
    Middleware that validates Firebase JWTs and injects uid, role, ngo_id
    into request.state for use in route handlers.
    """

    async def dispatch(self, request: Request, call_next):
        # Allow public paths through without a token
        if request.url.path in PUBLIC_PATHS or request.method == "OPTIONS":
            return await call_next(request)

        # Extract token
        auth_header: str = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Authorization header missing or malformed"},
            )
        token = auth_header[len("Bearer "):]

        try:
            # Fetch current public keys (in production, cache these with TTL)
            public_keys = await _fetch_firebase_public_keys()
            payload = _decode_firebase_token(token, public_keys)
        except HTTPException as exc:
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

        # Attach decoded claims to request state
        request.state.uid = payload.get("uid") or payload.get("sub")
        # Custom claims set by Cloud Functions / Admin SDK
        request.state.role = payload.get("role")
        request.state.ngo_id = payload.get("ngo_id")

        return await call_next(request)
