"""
auth_gate/models.py
Pydantic schemas for Identity Shield Auth Gate.
Strict validation per spec — no extra fields.
"""

import re
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, EmailStr, field_validator, model_validator

from .catalog import (
    is_valid_ngo_type,
    is_valid_subtype,
    get_subtypes_for_type,
)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Role(str, Enum):
    NGO_ADMIN   = "NGO_ADMIN"
    NGO_MEMBER  = "NGO_MEMBER"
    VOLUNTEER   = "VOLUNTEER"
    CITIZEN     = "CITIZEN"


class VolunteerType(str, Enum):
    GENERAL = "GENERAL"
    PRO     = "PRO"


class NGOTier(int, Enum):
    TIER_1 = 1
    TIER_2 = 2


class MemberRank(str, Enum):
    POWER_GROUP = "POWER_GROUP"  # Level 4 — Accept/Reject cards, Dispatch rights
    MEMBER      = "MEMBER"       # Level 3 — Watch-only, no action buttons


class ManageMemberAction(str, Enum):
    ADD         = "add"
    REMOVE      = "remove"
    ASSIGN_RANK = "assign_rank"


# ---------------------------------------------------------------------------
# Shared validators (reused across schemas)
# ---------------------------------------------------------------------------

PHONE_REGEX   = re.compile(r"^\+91[6-9]\d{9}$")
NGO_REG_REGEX = re.compile(r"^[A-Z0-9\-]{5,20}$")
PIN_REGEX     = re.compile(r"^\d{6}$")
OTP_REGEX     = re.compile(r"^\d{6}$")


def validate_phone(v: str) -> str:
    if not PHONE_REGEX.match(v):
        raise ValueError("Phone must be a valid Indian mobile number: +91XXXXXXXXXX")
    return v


def validate_pin(v: str) -> str:
    if not PIN_REGEX.match(v):
        raise ValueError("PIN must be exactly 6 digits")
    return v


def validate_otp(v: str) -> str:
    if not OTP_REGEX.match(v):
        raise ValueError("OTP must be exactly 6 digits")
    return v


def validate_ngo_reg(v: str) -> str:
    if not NGO_REG_REGEX.match(v):
        raise ValueError("NGO Registration No must be 5-20 uppercase alphanumeric characters")
    return v


# ---------------------------------------------------------------------------
# Registration / Preflight
# ---------------------------------------------------------------------------

class PreflightRequest(BaseModel):
    """POST /register/preflight — check email/phone uniqueness across all roles."""
    email: EmailStr
    phone: str

    @field_validator("phone")
    @classmethod
    def phone_valid(cls, v: str) -> str:
        return validate_phone(v)


class PreflightResponse(BaseModel):
    email_available: bool
    phone_available: bool
    conflict_role: Optional[Role] = None    # which role already owns the credential


# ---------------------------------------------------------------------------
# NGO Admin Registration
# ---------------------------------------------------------------------------

class NGOAdminRegisterRequest(BaseModel):
    """Full profile submitted after Google Sign-In for NGO_ADMIN."""
    uid:        str         # Firebase UID
    name:       str
    email:      EmailStr
    phone:      str
    ngo_reg_no: str
    region:     str
    tier:       NGOTier
    ngo_type:   str         # SINGLE selection from NGO_CATALOG (permanent)
    ngo_tags:   List[str]   # MULTI-SELECT subtypes from catalog (permanent)

    @field_validator("phone")
    @classmethod
    def phone_valid(cls, v: str) -> str:
        return validate_phone(v)

    @field_validator("ngo_reg_no")
    @classmethod
    def ngo_reg_valid(cls, v: str) -> str:
        return validate_ngo_reg(v)

    @field_validator("ngo_type")
    @classmethod
    def ngo_type_valid(cls, v: str) -> str:
        if not is_valid_ngo_type(v):
            raise ValueError(f"Invalid NGO type: '{v}'. Must be one of the catalog keys.")
        return v

    @model_validator(mode="after")
    def ngo_tags_valid(self) -> "NGOAdminRegisterRequest":
        """Ensure every tag belongs to the chosen ngo_type's subtype list."""
        valid_subtypes = get_subtypes_for_type(self.ngo_type)
        for tag in self.ngo_tags:
            if tag not in valid_subtypes:
                raise ValueError(
                    f"Invalid tag '{tag}' for NGO type '{self.ngo_type}'. "
                    f"Valid subtypes: {valid_subtypes}"
                )
        if not self.ngo_tags:
            raise ValueError("At least one ngo_tag (subtype) must be selected.")
        return self


# ---------------------------------------------------------------------------
# NGO Member (Staff) Registration
# ---------------------------------------------------------------------------

class ValidateReferralRequest(BaseModel):
    """Validate referral code BEFORE Google Sign-In (Step 1 of member flow)."""
    referral_code: str


class ValidateReferralResponse(BaseModel):
    valid:    bool
    ngo_id:   Optional[str] = None
    ngo_name: Optional[str] = None


class NGOMemberRegisterRequest(BaseModel):
    """Profile submitted by NGO member after Google Sign-In."""
    uid:           str
    name:          str
    email:         EmailStr
    phone:         str
    region:        str
    referral_code: str      # Used to link to parent NGO

    @field_validator("phone")
    @classmethod
    def phone_valid(cls, v: str) -> str:
        return validate_phone(v)


# ---------------------------------------------------------------------------
# Volunteer Registration
# ---------------------------------------------------------------------------

class VolunteerRegisterRequest(BaseModel):
    uid:            str
    name:           str
    about:          Optional[str] = None
    email:          EmailStr
    phone:          str
    region:         str
    profession:     str
    volunteer_type: VolunteerType   # GENERAL | PRO
    adhar_no:       str
    adhar_cert_url: Optional[str] = None


# ---------------------------------------------------------------------------
# Citizen Registration
# ---------------------------------------------------------------------------

class CitizenRegisterRequest(BaseModel):
    uid:     str
    name:    str
    about:   Optional[str] = None
    profession: Optional[str] = None
    email:   EmailStr
    phone:   str
    region:  str
    address: str
    adhar_no:       str
    adhar_cert_url: Optional[str] = None

    @field_validator("phone")
    @classmethod
    def phone_valid(cls, v: str) -> str:
        return validate_phone(v)


# ---------------------------------------------------------------------------
# PIN (Security Anchor)
# ---------------------------------------------------------------------------

class SetPINRequest(BaseModel):
    uid: str
    pin: str

    @field_validator("pin")
    @classmethod
    def pin_valid(cls, v: str) -> str:
        return validate_pin(v)


class ValidatePINRequest(BaseModel):
    uid: str
    pin: str

    @field_validator("pin")
    @classmethod
    def pin_valid(cls, v: str) -> str:
        return validate_pin(v)


class ValidatePINResponse(BaseModel):
    valid:               bool
    encrypted_vault_url: Optional[str] = None   # Returned only on success


# ---------------------------------------------------------------------------
# PIN Reset (Forgot PIN — Firebase OTP based)
# ---------------------------------------------------------------------------

class RequestPINResetRequest(BaseModel):
    """
    POST /auth/reset-pin/request
    Step 1: User provides their UID and registered phone/email.
    The backend triggers a Firebase OTP to their phone.
    """
    uid:   str
    phone: str

    @field_validator("phone")
    @classmethod
    def phone_valid(cls, v: str) -> str:
        return validate_phone(v)


class ConfirmPINResetRequest(BaseModel):
    """
    POST /auth/reset-pin/confirm
    Step 2: User provides the OTP they received and their new 6-digit PIN.
    Backend verifies OTP via Firebase, then sets the new PIN hash.
    """
    uid:     str
    otp:     str    # 6-digit OTP from Firebase phone auth
    new_pin: str    # New 6-digit Fortress PIN

    @field_validator("otp")
    @classmethod
    def otp_valid(cls, v: str) -> str:
        return validate_otp(v)

    @field_validator("new_pin")
    @classmethod
    def new_pin_valid(cls, v: str) -> str:
        return validate_pin(v)


# ---------------------------------------------------------------------------
# Admin-Gated Field Change (Region / NGO Type / Profession — Admin only)
# ---------------------------------------------------------------------------

class AdminFieldChangeRequest(BaseModel):
    """
    POST /auth/admin/change-locked-field
    Allows Level 5 Admin to change a permanently-locked field.
    Requires: current PIN + OTP verification (2-step).
    Every change is written to the audit log.
    """
    admin_uid:   str
    target_uid:  str        # The user whose field is being changed
    field_name:  str        # e.g. "region", "ngo_type", "profession"
    new_value:   str        # The new value for that field
    pin:         str        # Admin's current Fortress PIN
    otp:         str        # OTP sent to Admin's registered phone

    @field_validator("pin")
    @classmethod
    def pin_valid(cls, v: str) -> str:
        return validate_pin(v)

    @field_validator("otp")
    @classmethod
    def otp_valid(cls, v: str) -> str:
        return validate_otp(v)

    @field_validator("field_name")
    @classmethod
    def field_name_valid(cls, v: str) -> str:
        allowed = {"region", "ngo_type", "profession", "ngo_tags"}
        if v not in allowed:
            raise ValueError(f"'{v}' is not a locked field. Allowed: {allowed}")
        return v


# ---------------------------------------------------------------------------
# NGO Tenant Management
# ---------------------------------------------------------------------------

class ManageMemberRequest(BaseModel):
    """POST /ngo/manage-member — admin only."""
    admin_uid:  str
    member_uid: str
    action:     ManageMemberAction
    rank:       Optional[MemberRank] = None     # Required only for assign_rank

    @model_validator(mode="after")
    def rank_required_for_assign(self) -> "ManageMemberRequest":
        if self.action == ManageMemberAction.ASSIGN_RANK and self.rank is None:
            raise ValueError("rank is required when action is assign_rank")
        return self


class ToggleTierRequest(BaseModel):
    """POST /ngo/toggle-tier — upgrade from Tier 1 → Tier 2."""
    admin_uid: str
    doc_urls:  List[str]    # Uploaded separately via /verify/ngo-docs


# ---------------------------------------------------------------------------
# NGO Verification
# ---------------------------------------------------------------------------

class VerifyNGORequest(BaseModel):
    """POST /verify/ngo — validate NGO Reg No against master list."""
    ngo_reg_no: str

    @field_validator("ngo_reg_no")
    @classmethod
    def ngo_reg_valid(cls, v: str) -> str:
        return validate_ngo_reg(v)


# ---------------------------------------------------------------------------
# User Profile Response
# ---------------------------------------------------------------------------

class UserProfileResponse(BaseModel):
    uid:    str
    name:   str
    email:  EmailStr
    phone:  str
    role:   Role
    region: str
    # NGO-specific (None for Volunteer/Citizen)
    ngo_id:               Optional[str]       = None
    rank:                 Optional[MemberRank] = None
    has_dispatch_rights:  Optional[bool]       = None
    ngo_type:             Optional[str]        = None   # Single type (from catalog)
    ngo_tags:             Optional[List[str]]  = None   # Subtype tags (from catalog)
    # Volunteer-specific
    volunteer_type:       Optional[VolunteerType] = None
    skill_cert_url:       Optional[str]           = None
    # Citizen-specific
    nationality_cert_url: Optional[str] = None
    profession:           Optional[str] = None  # Citizen optional, Volunteer mandatory
    is_verified:          bool          = False
    
    # Universal settings & UI states
    has_unread_updates:   bool          = False
    theme_mode:           str           = "light"
    language_preference:  str           = "en"

# ---------------------------------------------------------------------------
# Profile Editing (Screen 15, 19)
# ---------------------------------------------------------------------------

class UpdateProfileRequest(BaseModel):
    """Fields a user is allowed to edit on their profile page."""
    about:                Optional[str] = None
    email:                Optional[EmailStr] = None
    phone:                Optional[str] = None
    profession:           Optional[str] = None  # For Citizen only
    theme_mode:           Optional[str] = None
    language_preference:  Optional[str] = None
    ngo_email:            Optional[EmailStr] = None
    ngo_phone:            Optional[str] = None
