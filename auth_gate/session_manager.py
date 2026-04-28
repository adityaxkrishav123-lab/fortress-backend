"""
auth_gate/session_manager.py
=============================
Handles the PERSISTENCE layer for Project Powerhouse.

The "Dream Vision" Flow:
  1. FIRST EVER OPEN → Show Signup (once in a lifetime)
  2. Every subsequent open → Show PIN Login (6-digit gate)
  3. After PIN success → Issue access_token (short) + refresh_token (long)
  4. App in background or phone restart → access_token dies, but
     refresh_token (stored securely in device local storage) is used to
     silently get a new access_token without asking for PIN again
     (ONLY while the session is still within the refresh window).
  5. Session completely expired (30 days) or user logs out →
     refresh_token revoked → User sees PIN page again (NOT signup).

KEY DESIGN DECISIONS:
  - Signup marker stored in LOCAL device storage (frontend).
  - Refresh tokens stored in Firestore for server-side revocation (logout/security).
  - Access tokens are short-lived (30 min) — they live only in memory.
  - Raw refresh token is NEVER stored; only its hash is in Firestore.
  - User profile is cached locally (in device storage) to reduce server reads.
"""

from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timedelta
from typing import Optional


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ACCESS_TOKEN_EXPIRY_MINUTES  = 30       # Short-lived: 30 minutes
REFRESH_TOKEN_EXPIRY_DAYS    = 30       # Long-lived: 30 days
REFRESH_TOKEN_BYTES          = 64       # Cryptographically secure random bytes


# ---------------------------------------------------------------------------
# Token Generation
# ---------------------------------------------------------------------------

def generate_access_token(uid: str, role: str, ngo_id: Optional[str] = None) -> dict:
    """
    Generates a short-lived access token (JWT-like structure).
    In production, this would be a signed JWT.
    For now, it is a securely random token + metadata stored in Firestore.

    Returns a dict with the token string + expiry info.
    """
    token = secrets.token_urlsafe(48)
    expires_at = (datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRY_MINUTES)).isoformat()

    return {
        "access_token": token,
        "token_type":   "Bearer",
        "expires_at":   expires_at,
        "uid":          uid,
        "role":         role,
        "ngo_id":       ngo_id,
    }


def generate_refresh_token() -> tuple[str, str]:
    """
    Generates a cryptographically secure refresh token.
    Returns (raw_token, hashed_token).
    raw_token → sent to device, stored in local storage.
    hashed_token → stored in Firestore (so we never store the raw secret).
    """
    raw_token    = secrets.token_urlsafe(REFRESH_TOKEN_BYTES)
    hashed_token = _hash_token(raw_token)
    return raw_token, hashed_token


def _hash_token(token: str) -> str:
    """One-way hash a token using SHA-256. Never store raw refresh tokens."""
    return hashlib.sha256(token.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Firestore Operations
# ---------------------------------------------------------------------------

async def store_refresh_token(
    db,
    uid: str,
    role: str,
    ngo_id: Optional[str],
    hashed_token: str,
    device_info: Optional[str] = None,
) -> None:
    """
    Stores the HASHED refresh token in Firestore.
    One user can have multiple refresh tokens (one per device).
    Each device gets its own entry so logout on one device
    does NOT log out all other devices.
    """
    expires_at = (datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRY_DAYS)).isoformat()

    # Each token is its own document — keyed by its hash
    await db.collection("refresh_tokens").document(hashed_token).set({
        "uid":          uid,
        "role":         role,
        "ngo_id":       ngo_id,
        "hashed_token": hashed_token,
        "device_info":  device_info or "unknown",
        "created_at":   datetime.utcnow().isoformat(),
        "expires_at":   expires_at,
        "is_revoked":   False,
    })


async def validate_refresh_token(db, raw_token: str) -> Optional[dict]:
    """
    Validates a raw refresh token sent from the device.
    Returns the token record (with uid, role, ngo_id) if valid.
    Returns None if expired, revoked, or not found.
    """
    hashed = _hash_token(raw_token)
    doc    = await db.collection("refresh_tokens").document(hashed).get()

    if not doc.exists:
        return None

    record = doc.to_dict()

    # Check if revoked
    if record.get("is_revoked"):
        return None

    # Check if expired
    expires_at = record.get("expires_at")
    if expires_at and datetime.fromisoformat(expires_at) < datetime.utcnow():
        # Auto-revoke expired tokens
        await db.collection("refresh_tokens").document(hashed).update({"is_revoked": True})
        return None

    return record


async def revoke_refresh_token(db, raw_token: str) -> bool:
    """
    Revokes a specific refresh token (single-device logout).
    Returns True if found and revoked, False if not found.
    """
    hashed = _hash_token(raw_token)
    doc    = await db.collection("refresh_tokens").document(hashed).get()

    if not doc.exists:
        return False

    await db.collection("refresh_tokens").document(hashed).update({
        "is_revoked":  True,
        "revoked_at":  datetime.utcnow().isoformat(),
    })
    return True


async def revoke_all_refresh_tokens(db, uid: str) -> int:
    """
    Revokes ALL refresh tokens for a user (full logout from all devices).
    Returns the count of tokens revoked.
    Used when: user changes PIN, account is suspended, or user requests
    "Log out of all devices."
    """
    query = db.collection("refresh_tokens").where("uid", "==", uid).where("is_revoked", "==", False)
    docs  = await query.get()

    count = 0
    for doc in docs:
        await doc.reference.update({
            "is_revoked": True,
            "revoked_at": datetime.utcnow().isoformat(),
        })
        count += 1

    return count


async def rotate_refresh_token(
    db,
    raw_token: str,
) -> tuple[Optional[str], Optional[dict]]:
    """
    TOKEN ROTATION — The "Replay Attack Detector."

    Called during every silent session refresh (POST /session/refresh).
    This is the industry-standard pattern used by Google, GitHub, and Stripe.

    HOW IT WORKS:
      1. Validate the old token.
      2. Immediately revoke (delete) the old token — it is DEAD FOREVER.
      3. Generate a brand new token for the same device.
      4. Return (new_raw_token, original_record).

    WHY THIS IS POWERFUL:
      If a hacker steals a refresh_token and tries to use it AFTER the real
      app has already rotated it → they get a "None" back (already revoked).
      The caller (the endpoint) then treats this as a potential replay attack
      and revokes ALL tokens for that user — locking every device out.

    Returns:
      (new_raw_token, record)  → Success — use new_raw_token going forward.
      (None, None)             → Failure — expired, revoked, or replay attack.
    """
    hashed = _hash_token(raw_token)
    doc    = await db.collection("refresh_tokens").document(hashed).get()

    if not doc.exists:
        return None, None

    record = doc.to_dict()

    # Reject if already revoked — this is either expiry or a REPLAY ATTACK
    if record.get("is_revoked"):
        return None, None

    # Reject if expired
    expires_at = record.get("expires_at")
    if expires_at and datetime.fromisoformat(expires_at) < datetime.utcnow():
        # Auto-revoke and return None
        await db.collection("refresh_tokens").document(hashed).update({"is_revoked": True})
        return None, None

    # ✅ Token is valid — immediately revoke the OLD token (it's now dead)
    await db.collection("refresh_tokens").document(hashed).update({
        "is_revoked":    True,
        "rotated_at":    datetime.utcnow().isoformat(),
        "rotation_note": "Rotated — replaced by new token on refresh",
    })

    # Issue a brand new refresh token (same device_info, same uid/role/ngo_id)
    new_raw, new_hashed = generate_refresh_token()
    await store_refresh_token(
        db,
        uid          = record["uid"],
        role         = record["role"],
        ngo_id       = record.get("ngo_id"),
        hashed_token = new_hashed,
        device_info  = record.get("device_info"),
    )

    return new_raw, record


# ---------------------------------------------------------------------------
# Local Cache Definition
# ---------------------------------------------------------------------------

def build_local_cache_payload(user_data: dict, ngo_name: Optional[str] = None) -> dict:
    """
    Defines what gets stored in the DEVICE LOCAL STORAGE after a
    successful PIN login. This is a read-only cache — it is refreshed
    every time the user logs in. It reduces server reads for profile display.

    The frontend stores this in secure local storage (SharedPreferences on
    Flutter, localStorage on Web).

    What is included (safe to cache — no secrets):
      - uid, name, role, region
      - ngo_id, ngo_name (for NGO users)
      - profile display info

    What is NEVER cached locally:
      - PIN hash (stays only in Firestore)
      - Raw refresh token (stored securely, not in plain cache)
      - Access token (kept only in memory)
    """
    return {
        "uid":         user_data.get("uid"),
        "name":        user_data.get("name"),
        "role":        user_data.get("role"),
        "region":      user_data.get("region"),
        "phone":       user_data.get("phone"),
        "ngo_id":      user_data.get("ngo_id"),
        "ngo_name":    ngo_name,
        "ngo_type":    user_data.get("ngo_type"),
        "ngo_tags":    user_data.get("ngo_tags", []),
        "is_verified": user_data.get("is_verified", False),
        "cached_at":   datetime.utcnow().isoformat(),
    }
