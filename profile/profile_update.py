"""
profile/profile_update.py
==========================
Module 4: The Profile Update Service.

Allows users to edit their "soft" profile fields at any time.
These are NOT identity/auth fields — they are personal preferences and info.

Editable fields (by role):
  - All roles  : about, phone, email, theme, language
  - Citizen    : address (also editable)

Permanently locked fields (NOT in this file):
  - region, ngo_type, profession, ngo_tags
  → These are only changeable via /auth/admin/change-locked-field (Admin + PIN + OTP).
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, EmailStr

router = APIRouter(prefix="/api/v1/profile", tags=["Profile Update"])


# ---------------------------------------------------------------------------
# Request Model
# ---------------------------------------------------------------------------

class ProfileUpdateRequest(BaseModel):
    """
    All fields are optional — user updates only what they want to change.
    The backend will only write fields that are present (not None).
    """
    about:    Optional[str]      = None   # Bio / About Me
    phone:    Optional[str]      = None   # New phone number (uniqueness enforced)
    email:    Optional[EmailStr] = None   # New email (uniqueness enforced)
    theme:    Optional[str]      = None   # "DARK" or "LIGHT"
    language: Optional[str]      = None   # Language code e.g. "en", "hi", "mr"
    address:  Optional[str]      = None   # Citizen only

    # --- Locked Fields (rejected if submitted) ---
    region:     Optional[str] = None
    ngo_type:   Optional[str] = None
    profession: Optional[str] = None
    ngo_tags:   Optional[list] = None

ALLOWED_THEMES    = {"DARK", "LIGHT"}
ALLOWED_LANGUAGES = {"en", "hi", "mr", "gu", "ta", "te", "kn", "bn", "pa", "ur"}


# ---------------------------------------------------------------------------
# ENDPOINT: Update Profile
# PUT /profile/update
# ---------------------------------------------------------------------------

@router.put("/update")
async def update_profile(payload: ProfileUpdateRequest, request: Request):
    """
    Updates the caller's own profile with any of the soft fields.
    Locked fields (region, ngo_type, profession) are REJECTED if submitted.
    Phone/email uniqueness is enforced if they are being changed.
    """
    db  = request.app.state.db
    uid = request.state.uid

    # --- Reject any attempt to change locked fields ---
    locked_attempts = []
    if payload.region     is not None: locked_attempts.append("region")
    if payload.ngo_type   is not None: locked_attempts.append("ngo_type")
    if payload.profession is not None: locked_attempts.append("profession")
    if payload.ngo_tags   is not None: locked_attempts.append("ngo_tags")

    if locked_attempts:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"The following fields are permanently locked and can only be changed "
                   f"by an Admin via the secure field-change process: {locked_attempts}"
        )

    # --- Validate theme and language if provided ---
    if payload.theme and payload.theme.upper() not in ALLOWED_THEMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid theme '{payload.theme}'. Must be one of: {ALLOWED_THEMES}"
        )
    if payload.language and payload.language.lower() not in ALLOWED_LANGUAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid language code. Supported: {ALLOWED_LANGUAGES}"
        )

    # --- Uniqueness check for phone and email ---
    if payload.phone:
        phone_query = await db.collection("users").where("phone", "==", payload.phone).limit(1).get()
        if phone_query and phone_query[0].to_dict().get("uid") != uid:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This phone number is already registered to another account."
            )

    if payload.email:
        email_query = await db.collection("users").where("email", "==", str(payload.email)).limit(1).get()
        if email_query and email_query[0].to_dict().get("uid") != uid:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This email is already registered to another account."
            )

    # --- Build the update dict (only include fields that were provided) ---
    update_data = {}
    if payload.about    is not None: update_data["about"]    = payload.about
    if payload.phone    is not None: update_data["phone"]    = payload.phone
    if payload.email    is not None: update_data["email"]    = str(payload.email)
    if payload.theme    is not None: update_data["theme"]    = payload.theme.upper()
    if payload.language is not None: update_data["language"] = payload.language.lower()
    if payload.address  is not None: update_data["address"]  = payload.address

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid fields provided to update."
        )

    # --- Apply the update ---
    user_ref = db.collection("users").document(uid)
    if not (await user_ref.get()).exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    await user_ref.update(update_data)

    return {
        "uid":     uid,
        "updated": list(update_data.keys()),
        "status":  "PROFILE_UPDATED",
    }


# ---------------------------------------------------------------------------
# ENDPOINT: Get Public Profile of Any User
# GET /profile/{uid}
# ---------------------------------------------------------------------------

@router.get("/{uid}")
async def get_public_profile(uid: str, request: Request):
    """
    Returns the PUBLIC profile of any user (name, contact, about, region).
    Everyone can see everyone's profile — but NOT their dashboard data or logs.
    Private fields (pin_hash, is_verified flags) are stripped.
    """
    db = request.app.state.db

    user_doc = await db.collection("users").document(uid).get()
    if not user_doc.exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    data = user_doc.to_dict()

    # Strip all private / sensitive fields (The "Locked Vault")
    PRIVATE_FIELDS = {
        "pin_hash", "is_verified", "nationality_cert_url",
        "skill_cert_url", "fcm_token", "encrypted_vault_url",
        "phone", "email", "address"  # Hidden until Handshake (Accept)
    }

    public_profile = {k: v for k, v in data.items() if k not in PRIVATE_FIELDS}

    return public_profile
