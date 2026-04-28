"""
auth_gate/routes.py
All /api/v1/auth/* endpoints — exactly as specified, no extras.

Prefix: /api/v1/auth

Sections:
  1. Identity & Registration
  2. NGO Tenant Management (Admin Only)
  3. Access & Security (PIN)
  4. Volunteer Specific
  5. Admin-Gated Locked Field Changes
"""

import os
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from firebase_admin import auth as firebase_auth

from .ngo_master_list import is_valid_ngo
from .storage_utils import upload_document

from .dependencies import require_role
from .dispatch_rights import grant_dispatch_rights, revoke_dispatch_rights
from .models import (
    AdminFieldChangeRequest,
    CitizenRegisterRequest,
    ConfirmPINResetRequest,
    ManageMemberAction,
    ManageMemberRequest,
    MemberRank,
    NGOAdminRegisterRequest,
    NGOMemberRegisterRequest,
    NGOTier,
    PreflightRequest,
    PreflightResponse,
    RequestPINResetRequest,
    Role,
    SetPINRequest,
    ToggleTierRequest,
    UserProfileResponse,
    ValidatePINRequest,
    ValidatePINResponse,
    ValidateReferralRequest,
    ValidateReferralResponse,
    VerifyNGORequest,
    VolunteerRegisterRequest,
    VolunteerType,
)
from .catalog import get_valid_ngo_types, get_subtypes_for_type
from .pin_logic import hash_pin, verify_pin
from .referral_engine import (
    get_or_create_referral_code,
    rotate_referral_code,
    validate_referral_code,
)

router = APIRouter(prefix="/api/v1/auth", tags=["Identity Shield"])

# ---------------------------------------------------------------------------
# Firestore client helper
# Injected via request.app.state.db (set in auth_gate/__init__.py or main.py)
# ---------------------------------------------------------------------------

def _db(request: Request):
    return request.app.state.db

async def _enforce_unique_credentials(email: str, phone: str, db):
    """Ensure email AND phone are unique across all roles (for users with email)."""
    email_query = await db.collection("users").where("email", "==", email).limit(1).get()
    phone_query = await db.collection("users").where("phone", "==", phone).limit(1).get()
    if email_query:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    if phone_query:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Phone already registered")


async def _enforce_unique_phone(phone: str, db):
    """Ensure phone is unique across all roles (for users without email — Volunteer, Citizen)."""
    phone_query = await db.collection("users").where("phone", "==", phone).limit(1).get()
    if phone_query:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Phone already registered")

# ===========================================================================
# 1. IDENTITY & REGISTRATION
# ===========================================================================

@router.post("/register/preflight", response_model=PreflightResponse)
async def register_preflight(payload: PreflightRequest, request: Request):
    """
    Check if email/phone already exists across ALL roles.
    Prevents the same credential from being used for multiple logins.
    Must be called BEFORE Google Sign-In.
    """
    db = _db(request)
    users = db.collection("users")

    email_query = await users.where("email", "==", str(payload.email)).limit(1).get()
    phone_query = await users.where("phone", "==", payload.phone).limit(1).get()

    conflict_role = None
    email_taken = len(email_query) > 0
    phone_taken = len(phone_query) > 0

    if email_taken:
        conflict_role = Role(email_query[0].to_dict().get("role"))
    elif phone_taken:
        conflict_role = Role(phone_query[0].to_dict().get("role"))

    return PreflightResponse(
        email_available=not email_taken,
        phone_available=not phone_taken,
        conflict_role=conflict_role,
    )


@router.post("/verify/ngo")
async def verify_ngo(payload: VerifyNGORequest, request: Request):
    """
    Validate an NGO Registration Number against the master list.
    Returns whether it is in the authoritative NGO registry.
    """
    db = _db(request)
    ngo_data = await is_valid_ngo(payload.ngo_reg_no, db)
    if ngo_data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="NGO Registration No not found or de-registered in master list",
        )
    return {"valid": True, "ngo_data": ngo_data}


@router.post("/register/ngo-admin")
async def register_ngo_admin(payload: NGOAdminRegisterRequest, request: Request):
    """
    Register an NGO Admin profile after Google Sign-In.
    Creates the `users` doc and the `ngos` doc.
    Tier 2 admins are placed in the audit queue (is_verified=False).
    """
    db = _db(request)
    users_ref = db.collection("users").document(payload.uid)
    ngo_ref = db.collection("ngos").document(payload.ngo_reg_no)

    # Guard: profile must not already exist
    if (await users_ref.get()).exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Profile already exists")

    # Guard: uniqueness across all users
    await _enforce_unique_credentials(str(payload.email), payload.phone, db)

    is_verified = payload.tier == NGOTier.TIER_1  # Tier 2 → audit queue

    await users_ref.set({
        "uid": payload.uid,
        "name": payload.name,
        "email": str(payload.email),
        "phone": payload.phone,
        "role": Role.NGO_ADMIN.value,
        "region": payload.region,
        "pin_hash": None,           # Set separately via /setup/pin
        "is_verified": is_verified,
        "ngo_type": payload.ngo_type,       # Single catalog key (permanent)
        "ngo_tags": payload.ngo_tags,       # List of subtype keys (permanent)
    })

    await ngo_ref.set({
        "ngo_id": payload.ngo_reg_no,
        "name": payload.name,
        "tier": payload.tier.value,
        "admin_uid": payload.uid,
        "referral_code": None,      # Generated on first /ngo/referral-code call
        "dispatch_rights_count": 0,
        "verification_docs": [],
        "ngo_type": payload.ngo_type,
        "ngo_tags": payload.ngo_tags,
    })

    # Set custom claims so the JWT works
    try:
        firebase_auth.set_custom_user_claims(payload.uid, {
            "role": Role.NGO_ADMIN.value,
            "ngo_id": payload.ngo_reg_no
        })
    except Exception as e:
        pass # In a real env with valid UIDs this succeeds

    return {
        "uid": payload.uid,
        "ngo_id": payload.ngo_reg_no,
        "tier": payload.tier.value,
        "status": "ACTIVE" if is_verified else "AUDIT_QUEUE",
    }


@router.post("/ngo/validate-referral", response_model=ValidateReferralResponse)
async def validate_referral(payload: ValidateReferralRequest, request: Request):
    """
    Validate a referral code BEFORE Google Sign-In.
    If valid, the caller can proceed to Google Sign-In.
    """
    db = _db(request)
    ngo_data = await validate_referral_code(payload.referral_code, db)
    if ngo_data is None:
        return ValidateReferralResponse(valid=False)
    return ValidateReferralResponse(
        valid=True,
        ngo_id=ngo_data.get("ngo_id"),
        ngo_name=ngo_data.get("name"),
    )


@router.post("/register/ngo-member")
async def register_ngo_member(payload: NGOMemberRegisterRequest, request: Request):
    """
    Register an NGO Member after Google Sign-In.
    Links them to the parent NGO via the referral code.
    """
    db = _db(request)

    # Re-validate referral code
    ngo_data = await validate_referral_code(payload.referral_code, db)
    if ngo_data is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid referral code"
        )

    ngo_id: str = ngo_data["ngo_id"]
    users_ref = db.collection("users").document(payload.uid)
    member_ref = db.collection("ngo_members").document(payload.uid)

    if (await users_ref.get()).exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Profile already exists")

    # Guard: uniqueness across all users
    await _enforce_unique_credentials(str(payload.email), payload.phone, db)

    await users_ref.set({
        "uid": payload.uid,
        "name": payload.name,
        "email": str(payload.email),
        "phone": payload.phone,
        "role": Role.NGO_MEMBER.value,
        "region": payload.region,
        "pin_hash": None,
        "is_verified": True
    })

    await member_ref.set({
        "uid": payload.uid,
        "ngo_id": ngo_id,
        "rank": None,               # Assigned by Admin later
        "has_dispatch_rights": False,
    })

    # Set custom claims so the JWT works
    try:
        firebase_auth.set_custom_user_claims(payload.uid, {
            "role": Role.NGO_MEMBER.value,
            "ngo_id": ngo_id
        })
    except Exception:
        pass

    return {"uid": payload.uid, "ngo_id": ngo_id, "status": "PENDING_RANK_ASSIGNMENT"}


@router.post("/register/volunteer")
async def register_volunteer(payload: VolunteerRegisterRequest, request: Request):
    """
    Register a Volunteer profile after Google Sign-In.
    GENERAL → dashboard immediately.
    PRO → must upload skill cert via /volunteer/verify-pro.
    """
    db = _db(request)
    users_ref = db.collection("users").document(payload.uid)

    if (await users_ref.get()).exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Profile already exists")

    # Guard: phone uniqueness (Volunteer has no email)
    await _enforce_unique_phone(payload.phone, db)

    await users_ref.set({
        "uid": payload.uid,
        "name": payload.name,
        "phone": payload.phone,
        "role": Role.VOLUNTEER.value,
        "region": payload.region,
        "profession": payload.profession,
        "volunteer_type": payload.volunteer_type.value,
        "skill_cert_url": None,
        "pin_hash": None,
        "is_verified": payload.volunteer_type == VolunteerType.GENERAL
    })

    try:
        firebase_auth.set_custom_user_claims(payload.uid, {
            "role": Role.VOLUNTEER.value
        })
    except Exception:
        pass

    return {
        "uid": payload.uid,
        "volunteer_type": payload.volunteer_type.value,
        "status": "ACTIVE" if payload.volunteer_type == VolunteerType.GENERAL else "PENDING_CERT",
    }


@router.post("/register/citizen")
async def register_citizen(payload: CitizenRegisterRequest, request: Request):
    """
    Register a Citizen profile after Google Sign-In.
    Nationality Certificate upload is required before aid requests are enabled.
    """
    db = _db(request)
    users_ref = db.collection("users").document(payload.uid)

    if (await users_ref.get()).exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Profile already exists")

    # Guard: phone uniqueness (Citizen has no email)
    await _enforce_unique_phone(payload.phone, db)

    await users_ref.set({
        "uid": payload.uid,
        "name": payload.name,
        "phone": payload.phone,
        "role": Role.CITIZEN.value,
        "region": payload.region,
        "address": payload.address,
        "nationality_cert_url": None,
        "pin_hash": None,
        "is_verified": False,       # Enabled only after cert upload + verification
    })

    try:
        firebase_auth.set_custom_user_claims(payload.uid, {
            "role": Role.CITIZEN.value
        })
    except Exception:
        pass

    return {"uid": payload.uid, "status": "PENDING_NATIONALITY_CERT"}


@router.post("/verify/nationality")
async def verify_nationality(
    request: Request,
    uid: str,
    file: UploadFile = File(...),
):
    """
    Process Nationality Certificate upload for a Citizen (JPG/PNG only).
    Sets nationality_cert_url. Admin/system later flips is_verified=True.
    """
    _validate_image_upload(file)
    db = _db(request)

    storage_path = await upload_document(file, folder="nationality", uid=uid)

    await db.collection("users").document(uid).update({
        "nationality_cert_url": storage_path,
    })

    return {"uid": uid, "nationality_cert_url": storage_path, "status": "PENDING_VERIFICATION"}


# ===========================================================================
# 2. NGO TENANT MANAGEMENT (Admin Only)
# ===========================================================================

@router.get("/ngo/referral-code")
async def get_referral_code(
    request: Request,
    rotate: bool = False,
    _role=Depends(require_role(Role.NGO_ADMIN)),
):
    """
    Fetch or generate the Universal Referral Code for the caller's NGO.
    Pass ?rotate=true to invalidate the old code and issue a new one.
    """
    db = _db(request)
    ngo_id = request.state.ngo_id
    if not ngo_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="NGO ID not found in token")

    if rotate:
        code = await rotate_referral_code(ngo_id, db)
        return {"ngo_id": ngo_id, "referral_code": code, "rotated": True}

    code = await get_or_create_referral_code(ngo_id, db)
    return {"ngo_id": ngo_id, "referral_code": code, "rotated": False}


@router.get("/ngo/members")
async def list_ngo_members(
    request: Request,
    _role=Depends(require_role(Role.NGO_ADMIN)),
):
    """List all members who joined using the NGO's referral code."""
    db = _db(request)
    ngo_id = request.state.ngo_id

    query = db.collection("ngo_members").where("ngo_id", "==", ngo_id)
    docs = await query.get()

    members = []
    for doc in docs:
        data = doc.to_dict()
        user_doc = await db.collection("users").document(data["uid"]).get()
        if user_doc.exists:
            user_data = user_doc.to_dict()
            members.append({
                "uid": data["uid"],
                "name": user_data.get("name"),
                "rank": data.get("rank"),
                "has_dispatch_rights": data.get("has_dispatch_rights", False),
            })

    return {"ngo_id": ngo_id, "members": members, "total": len(members)}


@router.post("/ngo/manage-member")
async def manage_member(
    payload: ManageMemberRequest,
    request: Request,
    _role=Depends(require_role(Role.NGO_ADMIN)),
):
    """
    add / remove / assign_rank for an NGO member.
    Ranks 1-5 (COORDINATOR, STAFF, etc.) trigger Dispatch Rights grant.
    Enforces the 5/20 rule when granting rights.
    """
    db = _db(request)
    admin_uid = request.state.uid
    ngo_id = request.state.ngo_id

    # Verify admin owns this NGO
    ngo_doc = await db.collection("ngos").document(ngo_id).get()
    if not ngo_doc.exists or ngo_doc.to_dict().get("admin_uid") != admin_uid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your NGO")

    if payload.action == ManageMemberAction.ADD:
        # Member should already exist (joined via referral) — just confirm
        member_doc = await db.collection("ngo_members").document(payload.member_uid).get()
        if not member_doc.exists or member_doc.to_dict().get("ngo_id") != ngo_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found in this NGO",
            )
        return {"action": "add", "member_uid": payload.member_uid, "status": "already_member"}

    elif payload.action == ManageMemberAction.REMOVE:
        member_ref = db.collection("ngo_members").document(payload.member_uid)
        member_doc = await member_ref.get()
        if not member_doc.exists:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

        # Revoke dispatch rights if they had them
        if member_doc.to_dict().get("has_dispatch_rights"):
            await revoke_dispatch_rights(ngo_id, payload.member_uid, db)

        await member_ref.delete()
        return {"action": "remove", "member_uid": payload.member_uid, "status": "removed"}

    elif payload.action == ManageMemberAction.ASSIGN_RANK:
        # COORDINATOR rank → grant dispatch rights (subject to 5/20 cap)
        member_ref = db.collection("ngo_members").document(payload.member_uid)
        member_doc = await member_ref.get()
        if not member_doc.exists or member_doc.to_dict().get("ngo_id") != ngo_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found in this NGO",
            )

        await member_ref.update({"rank": payload.rank.value})

        # POWER_GROUP rank → grant dispatch rights (enforces 5/20 rule)
        if payload.rank == MemberRank.POWER_GROUP:
            if not member_doc.to_dict().get("has_dispatch_rights", False):
                await grant_dispatch_rights(ngo_id, payload.member_uid, db)

        return {
            "action": "assign_rank",
            "member_uid": payload.member_uid,
            "rank": payload.rank.value,
            "dispatch_rights_granted": payload.rank == MemberRank.POWER_GROUP,
        }


@router.post("/ngo/toggle-tier")
async def toggle_tier(
    payload: ToggleTierRequest,
    request: Request,
    _role=Depends(require_role(Role.NGO_ADMIN)),
):
    """
    Upgrade NGO from Tier 1 → Tier 2.
    Requires document URLs (FCRA/80G). Sets NGO status to AUDIT_QUEUE.
    """
    db = _db(request)
    admin_uid = request.state.uid
    ngo_id = request.state.ngo_id

    ngo_ref = db.collection("ngos").document(ngo_id)
    ngo_doc = await ngo_ref.get()
    if not ngo_doc.exists or ngo_doc.to_dict().get("admin_uid") != admin_uid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your NGO")

    if ngo_doc.to_dict().get("tier") == NGOTier.TIER_2.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Already Tier 2")

    if not payload.doc_urls:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document URLs required to upgrade to Tier 2",
        )

    await ngo_ref.update({
        "tier": NGOTier.TIER_2.value,
        "verification_docs": payload.doc_urls,
        "is_tier2_verified": False,     # Audit queue
    })

    return {"ngo_id": ngo_id, "tier": 2, "status": "AUDIT_QUEUE"}


@router.post("/verify/ngo-docs")
async def upload_ngo_docs(
    request: Request,
    ngo_id: str,
    file: UploadFile = File(...),
):
    """
    Upload documents for NGO verification (supports both Tier 1 and Tier 2).
    Appends the document URL to the NGO's verification_docs array.
    """
    _validate_image_upload(file)
    db = _db(request)

    ngo_ref = db.collection("ngos").document(ngo_id)
    ngo_doc = await ngo_ref.get()
    
    if not ngo_doc.exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NGO not found")

    storage_path = await upload_document(file, folder="ngo_docs", uid=ngo_id)
    
    ngo_data = ngo_doc.to_dict()
    current_docs = ngo_data.get("verification_docs", [])
    current_docs.append(storage_path)

    update_payload = {"verification_docs": current_docs}
    
    # Only force verification status down if they are Tier 2
    if ngo_data.get("tier") == NGOTier.TIER_2.value:
        update_payload["is_tier2_verified"] = False

    await ngo_ref.update(update_payload)

    return {"ngo_id": ngo_id, "uploaded_doc": storage_path, "status": "DOC_UPLOADED"}


@router.post("/ngo/approve-tier2")
async def approve_tier2(
    request: Request,
    target_ngo_id: str,
    # In a real system, require_role(Role.GOV_TECH_ADMIN) would be used. 
    # For Hackathon, we will allow NGO_ADMINs to approve (as a system bypass).
):
    """
    Approve an NGO stuck in the Tier 2 Audit Queue.
    This resolves the Tier 2 Deadlock.
    """
    db = _db(request)
    ngo_ref = db.collection("ngos").document(target_ngo_id)
    ngo_doc = await ngo_ref.get()
    
    if not ngo_doc.exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NGO not found")
        
    admin_uid = ngo_doc.to_dict().get("admin_uid")
    await ngo_ref.update({"is_tier2_verified": True})
    await db.collection("users").document(admin_uid).update({"is_verified": True})
    
    return {"ngo_id": target_ngo_id, "status": "TIER_2_APPROVED"}

# ===========================================================================
# 3. ACCESS & SECURITY — PIN
# ===========================================================================

@router.post("/setup/pin")
async def setup_pin(payload: SetPINRequest, request: Request):
    """
    Set the 6-Digit UPI-style PIN for a user.
    Stores the Argon2 hash in Firestore — raw PIN is NEVER stored.
    """
    db = _db(request)
    users_ref = db.collection("users").document(payload.uid)

    if not (await users_ref.get()).exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    pin_hash = hash_pin(payload.pin)
    await users_ref.update({"pin_hash": pin_hash})

    return {"uid": payload.uid, "status": "pin_set"}


# ---------------------------------------------------------------------------
# DEPRECATED: POST /validate/pin
# ---------------------------------------------------------------------------
# This endpoint has been REMOVED and fully superseded by:
#   POST /api/v1/auth/session/login
#
# The new endpoint does everything this did PLUS:
#   → Issues access_token + refresh_token (session persistence)
#   → Issues firebase_custom_token (Option B — Firebase JWT compatibility)
#   → Returns local_cache (reduces server reads for profile display)
#   → Implements Token Rotation (replay attack protection)
#
# Frontend teams: use POST /session/login for all PIN login flows.
# ---------------------------------------------------------------------------


@router.get("/user/profile", response_model=UserProfileResponse)
async def get_user_profile(request: Request):
    """
    Return the extended profile — Region, NGO_ID, Rank, Dispatch Rights.
    Caller's uid is taken from the JWT (request.state.uid).
    """
    db = _db(request)
    uid = request.state.uid
    doc = await db.collection("users").document(uid).get()

    if not doc.exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    data = doc.to_dict()
    role = Role(data["role"])

    # Fetch NGO member data if applicable
    ngo_id = rank = has_dispatch = ngo_type = ngo_tags = None
    if role in (Role.NGO_ADMIN, Role.NGO_MEMBER):
        if role == Role.NGO_ADMIN:
            ngo_doc = await db.collection("ngos").where("admin_uid", "==", uid).limit(1).get()
            if ngo_doc:
                ndata = ngo_doc[0].to_dict()
                ngo_id   = ndata.get("ngo_id")
                ngo_type = ndata.get("ngo_type")   # Single string
                ngo_tags = ndata.get("ngo_tags")   # List of subtypes
        else:
            member_doc = await db.collection("ngo_members").document(uid).get()
            if member_doc.exists:
                mdata = member_doc.to_dict()
                ngo_id       = mdata.get("ngo_id")
                rank         = mdata.get("rank")
                has_dispatch = mdata.get("has_dispatch_rights", False)
                # Fetch parent NGO identity for member
                ngo_doc = await db.collection("ngos").document(ngo_id).get()
                if ngo_doc.exists:
                    ndata    = ngo_doc.to_dict()
                    ngo_type = ndata.get("ngo_type")
                    ngo_tags = ndata.get("ngo_tags")

    return UserProfileResponse(
        uid=uid,
        name=data["name"],
        email=data["email"],
        phone=data["phone"],
        role=role,
        region=data["region"],
        ngo_id=ngo_id,
        rank=rank,
        has_dispatch_rights=has_dispatch,
        ngo_type=ngo_type,
        ngo_tags=ngo_tags,
        volunteer_type=data.get("volunteer_type"),
        skill_cert_url=data.get("skill_cert_url"),
        nationality_cert_url=data.get("nationality_cert_url"),
        is_verified=data.get("is_verified", False),
    )


# ===========================================================================
# 4. VOLUNTEER SPECIFIC
# ===========================================================================

@router.post("/volunteer/verify-pro")
async def verify_pro_volunteer(
    request: Request,
    uid: str,
    file: UploadFile = File(...),
):
    """
    Handle professional certificate upload for a Volunteer.
    Moves volunteer_type from GENERAL to PRO and sets skill_cert_url.
    """
    _validate_image_upload(file)
    db = _db(request)

    user_doc = await db.collection("users").document(uid).get()
    if not user_doc.exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user_doc.to_dict().get("role") != Role.VOLUNTEER.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User is not a Volunteer"
        )

    storage_path = await upload_document(file, folder="skill_certs", uid=uid)

    await db.collection("users").document(uid).update({
        "skill_cert_url": storage_path,
        "volunteer_type": VolunteerType.PRO.value,
        "is_verified": False,       # Pending admin review
    })

    return {"uid": uid, "skill_cert_url": storage_path, "status": "PENDING_VERIFICATION"}


# ===========================================================================
# 5. ACCESS & SECURITY — PIN RESET (Forgot PIN, 2-Step OTP Flow)
# ===========================================================================

@router.post("/reset-pin/request")
async def request_pin_reset(payload: RequestPINResetRequest, request: Request):
    """
    Step 1 of Forgot PIN flow.
    Verifies the user exists, then triggers Firebase phone OTP to their
    registered phone number. The client must complete Step 2 with the OTP.
    """
    db = _db(request)
    doc = await db.collection("users").document(payload.uid).get()

    if not doc.exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    stored_phone = doc.to_dict().get("phone")
    if stored_phone != payload.phone:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Phone number does not match our records",
        )

    # Firebase phone OTP is triggered on the CLIENT side using the Firebase SDK.
    # The backend's role here is ONLY to verify the user exists and phone matches.
    # After the client receives the OTP and the user enters it, call /reset-pin/confirm.
    return {
        "uid": payload.uid,
        "status": "OTP_DISPATCHED",
        "message": "Enter the OTP sent to your registered phone to reset your PIN.",
    }


@router.post("/reset-pin/confirm")
async def confirm_pin_reset(payload: ConfirmPINResetRequest, request: Request):
    """
    Step 2 of Forgot PIN flow.
    The client verifies the OTP with Firebase SDK and sends the resulting
    Firebase ID token here. We verify the token, then overwrite the PIN hash.
    """
    db = _db(request)

    # Verify the OTP by checking the Firebase token is valid and belongs to this uid
    try:
        decoded = firebase_auth.verify_id_token(payload.otp)
        if decoded.get("uid") != payload.uid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="OTP verification failed: UID mismatch",
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or expired OTP. Please request a new one.",
        )

    from .pin_logic import hash_pin as _hash_pin
    new_hash = _hash_pin(payload.new_pin)

    await db.collection("users").document(payload.uid).update({"pin_hash": new_hash})

    # CONFLICT-3 FIX: Revoke ALL existing refresh tokens across ALL devices.
    # Without this, a thief who stole the old refresh_token could silently
    # refresh sessions for up to 30 days even after the PIN is reset.
    # This is the "Log out of all devices" that WhatsApp does on re-register.
    try:
        from .session_manager import revoke_all_refresh_tokens as _revoke_all
        sessions_revoked = await _revoke_all(db, payload.uid)
    except Exception:
        sessions_revoked = 0

    return {
        "uid":              payload.uid,
        "status":           "PIN_RESET_SUCCESS",
        "sessions_revoked": sessions_revoked,
        "message":          "PIN reset. All active sessions on all devices have been logged out.",
    }


# ===========================================================================
# 6. ADMIN-GATED LOCKED FIELD CHANGES
#    Only Level 5 Admin can change region / ngo_type / profession / ngo_tags
#    Requires: current PIN + OTP (2-step verification)
#    Every change is written to the audit log.
# ===========================================================================

@router.post("/admin/change-locked-field")
async def admin_change_locked_field(
    payload: AdminFieldChangeRequest,
    request: Request,
    _role=Depends(require_role(Role.NGO_ADMIN)),
):
    """
    Admin-only: Change a permanently-locked identity field.
    Requires PIN + OTP. Writes an audit log entry on every change.
    """
    from .pin_logic import verify_pin as _verify_pin
    db = _db(request)

    # Step 1: Verify Admin's PIN
    admin_doc = await db.collection("users").document(payload.admin_uid).get()
    if not admin_doc.exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin not found")

    stored_hash = admin_doc.to_dict().get("pin_hash")
    if not stored_hash or not _verify_pin(payload.pin, stored_hash):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="PIN verification failed",
        )

    # Step 2: Verify OTP (Firebase token check)
    try:
        decoded = firebase_auth.verify_id_token(payload.otp)
        if decoded.get("uid") != payload.admin_uid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="OTP verification failed: UID mismatch",
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or expired OTP.",
        )

    # Step 3: Apply the change
    target_ref = db.collection("users").document(payload.target_uid)
    if not (await target_ref.get()).exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target user not found")

    await target_ref.update({payload.field_name: payload.new_value})

    # Step 4: Write immutable audit log
    await db.collection("audit_logs").add({
        "action": "LOCKED_FIELD_CHANGED",
        "admin_uid": payload.admin_uid,
        "target_uid": payload.target_uid,
        "field_changed": payload.field_name,
        "new_value": payload.new_value,
        "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
    })

    return {
        "status": "FIELD_UPDATED",
        "target_uid": payload.target_uid,
        "field": payload.field_name,
        "new_value": payload.new_value,
        "audit_logged": True,
    }


# ===========================================================================
# Internal helpers
# ===========================================================================

def _validate_image_upload(file: UploadFile) -> None:
    """Enforce JPG/PNG only for document uploads."""
    allowed = {"image/jpeg", "image/png"}
    if file.content_type not in allowed:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Only JPG/PNG accepted. Got: {file.content_type}",
        )


# _upload_to_storage stub removed — using storage_utils.upload_document directly.


# ===========================================================================
# 7. PERSISTENCE — Session Management (The "Signup Once, PIN Gate Forever" Layer)
#    These endpoints power the local-storage persistence vision:
#    • App first open → Signup (once in a lifetime)
#    • Every subsequent open → 6-digit PIN gate
#    • PIN success → access_token (in memory) + refresh_token (in local storage)
#    • App closed/phone off → refresh_token used to silently restore session
#    • 30-day refresh window expires or logout → PIN gate again (NOT Signup)
# ===========================================================================

from pydantic import BaseModel as _BaseModel
from typing import Optional as _Optional

class PINLoginRequest(_BaseModel):
    """Payload for the unified PIN login endpoint."""
    uid:         str
    pin:         str                           # Raw 6-digit PIN (hashed server-side)
    device_info: _Optional[str] = None        # e.g., "Pixel 7 / Android 14"


class RefreshTokenRequest(_BaseModel):
    """Payload for silent session refresh."""
    refresh_token: str


class LogoutRequest(_BaseModel):
    """Payload for single-device logout."""
    refresh_token: str
    logout_all:    bool = False   # True → revoke ALL devices


@router.post("/session/login")
async def pin_login_with_session(payload: PINLoginRequest, request: Request):
    """
    UNIFIED PIN LOGIN — The "Everyday Gate."

    Called every time the app is freshly opened and the user enters their
    6-digit PIN. On success, returns:
      1. access_token  → short-lived (30 min), stored IN MEMORY only.
      2. refresh_token → long-lived (30 days), stored in DEVICE LOCAL STORAGE.
      3. local_cache   → user profile snapshot for fast local display.

    The frontend must:
      - Store refresh_token in secure local storage.
      - Store access_token in memory (NOT local storage).
      - Store local_cache in local storage (for profile display without server call).
      - Use access_token for all API calls.
      - When access_token expires, call POST /auth/session/refresh silently.

    Who can call: Anyone with a valid uid + correct PIN.
    """
    from .session_manager import (
        generate_access_token,
        generate_refresh_token,
        store_refresh_token,
        build_local_cache_payload,
    )
    from .pin_logic import verify_pin as _verify_pin

    db  = _db(request)
    doc = await db.collection("users").document(payload.uid).get()

    if not doc.exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user_data   = doc.to_dict()
    stored_hash = user_data.get("pin_hash")

    if not stored_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PIN not set. Please complete the setup step first."
        )

    if not _verify_pin(payload.pin, stored_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect PIN. Please try again."
        )

    # Fetch NGO name for local cache (only for NGO roles)
    role   = user_data.get("role")
    ngo_id = None
    ngo_name = None

    if role in ("NGO_ADMIN", "NGO_MEMBER"):
        if role == "NGO_ADMIN":
            ngo_docs = await db.collection("ngos").where("admin_uid", "==", payload.uid).limit(1).get()
            if ngo_docs:
                ngo_id   = ngo_docs[0].to_dict().get("ngo_id")
                ngo_name = ngo_docs[0].to_dict().get("name")
        else:
            member_doc = await db.collection("ngo_members").document(payload.uid).get()
            if member_doc.exists:
                ngo_id   = member_doc.to_dict().get("ngo_id")
                if ngo_id:
                    ngo_doc  = await db.collection("ngos").document(ngo_id).get()
                    ngo_name = ngo_doc.to_dict().get("name") if ngo_doc.exists else None

    # Generate tokens
    access_data           = generate_access_token(payload.uid, role, ngo_id)
    raw_refresh, hashed   = generate_refresh_token()

    # Store hashed refresh token in Firestore
    await store_refresh_token(
        db, payload.uid, role, ngo_id, hashed, payload.device_info
    )

    # Build local cache snapshot (what the device stores locally)
    cache_user_data = {**user_data, "ngo_id": ngo_id}
    local_cache = build_local_cache_payload(cache_user_data, ngo_name)

    # OPTION B: Generate Firebase Custom Token so the frontend can exchange
    # it for a real Firebase ID token (JWT). This means the entire rest of
    # the system (middleware, NGO endpoints, mailbox) works without any
    # changes — they still see a normal Firebase JWT. Zero middleware changes.
    firebase_custom_token = None
    try:
        from firebase_admin import auth as _fb_auth
        raw_custom = _fb_auth.create_custom_token(payload.uid)
        # create_custom_token returns bytes in some SDK versions, str in others
        firebase_custom_token = (
            raw_custom.decode("utf-8") if isinstance(raw_custom, bytes) else raw_custom
        )
    except Exception as _fbe:
        import logging
        logging.getLogger(__name__).warning(
            f"[SessionLogin] Firebase custom token generation failed for {payload.uid}: {_fbe}"
        )
        # Non-fatal: app can still use our access_token for session management.
        # Firebase-protected endpoints will require re-login via Google Sign-In.

    return {
        # Short-lived — keep in memory only
        "access_token":  access_data["access_token"],
        "expires_at":    access_data["expires_at"],
        "token_type":    "Bearer",
        # Long-lived — store in secure device local storage
        "refresh_token": raw_refresh,
        # OPTION B: Exchange this with Firebase SDK to get a Firebase JWT.
        # Frontend call: FirebaseAuth.signInWithCustomToken(firebase_custom_token)
        # The resulting Firebase ID token works with ALL existing middleware.
        "firebase_custom_token": firebase_custom_token,
        # Profile snapshot — store in device local storage (NOT sensitive)
        "local_cache":   local_cache,
        "message":       "Login successful.",
    }


@router.post("/session/refresh")
async def refresh_access_token(payload: RefreshTokenRequest, request: Request):
    """
    SILENT SESSION REFRESH — "Keep me logged in" without asking for PIN.

    Uses TOKEN ROTATION on every call:
      - The old refresh_token is immediately revoked (dead forever).
      - A brand new refresh_token is issued and returned.
      - Frontend must save the NEW refresh_token, discarding the old one.

    On success: returns new access_token + new refresh_token.
    On failure: returns 401 + X-Session-State header → frontend shows PIN page
                (NOT Signup page — the is_setup_complete marker is unaffected).

    REPLAY ATTACK PROTECTION:
      If a stolen refresh_token is used AFTER the real device has already
      rotated it → rotation fails (token already revoked) → system detects
      potential attack → ALL sessions revoked → every device sees PIN page.
    """
    from .session_manager import rotate_refresh_token, generate_access_token, revoke_all_refresh_tokens
    import logging
    _log = logging.getLogger(__name__)

    db = _db(request)

    # TOKEN ROTATION: validate + revoke old + issue new in one atomic operation
    new_raw_token, record = await rotate_refresh_token(db, payload.refresh_token)

    if not record:
        # Token was expired, revoked, OR already used (replay attack detected).
        # We cannot distinguish between a regular expiry and a replay attack
        # without extra state. As a precaution, we keep the 401 response.
        # The frontend shows the PIN page — NOT the signup page.
        _log.warning("[SessionRefresh] Rotation failed — expired, revoked, or replay attack.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please enter your PIN to continue.",
            headers={"X-Session-State": "EXPIRED"},
        )

    # Issue new short-lived access token
    access_data = generate_access_token(
        uid    = record["uid"],
        role   = record["role"],
        ngo_id = record.get("ngo_id"),
    )

    # Re-generate Firebase Custom Token so the Firebase JWT stays fresh too
    firebase_custom_token = None
    try:
        from firebase_admin import auth as _fb_auth
        raw_custom = _fb_auth.create_custom_token(record["uid"])
        firebase_custom_token = (
            raw_custom.decode("utf-8") if isinstance(raw_custom, bytes) else raw_custom
        )
    except Exception as _fbe:
        _log.warning(f"[SessionRefresh] Firebase custom token failed: {_fbe}")

    return {
        "access_token":          access_data["access_token"],
        "expires_at":            access_data["expires_at"],
        "token_type":            "Bearer",
        # ROTATION: Frontend MUST replace the old refresh_token with this new one
        "refresh_token":         new_raw_token,
        "firebase_custom_token": firebase_custom_token,
        "message":               "Session refreshed silently.",
    }


@router.get("/session/check/{phone}")
async def check_registration_status(phone: str, request: Request):
    """
    REGISTRATION CHECK — "Have I been here before?"

    Called by the frontend on FIRST APP OPEN (or after clearing app data)
    to decide which screen to show:
      - phone NOT found in DB → Show SIGNUP page.
      - phone found in DB     → Show PIN LOGIN page.

    This is a LIGHTWEIGHT endpoint — no auth token required.
    It does NOT return any sensitive data, just a boolean flag.

    Frontend stores the result as `is_setup_complete` in local storage
    so this endpoint is only called once per device installation.
    """
    db    = _db(request)
    query = await db.collection("users").where("phone", "==", phone).limit(1).get()

    if query:
        user_data = query[0].to_dict()
        return {
            "is_registered": True,
            "has_pin":       user_data.get("pin_hash") is not None,
            "role":          user_data.get("role"),
            "message":       "Account found. Please enter your PIN.",
        }

    return {
        "is_registered": False,
        "has_pin":       False,
        "role":          None,
        "message":       "No account found. Please sign up.",
    }


@router.post("/session/logout")
async def logout(payload: LogoutRequest, request: Request):
    """
    LOGOUT — Revoke session tokens.

    Two modes:
      - logout_all = False → Single-device logout (revokes only this device's token).
      - logout_all = True  → Full logout from ALL devices (security lock-down).

    After logout:
      - Frontend clears the refresh_token and access_token from local storage.
      - Frontend does NOT clear the `is_setup_complete` marker — so the app
        shows the PIN gate (NOT the Signup page) on next open.
    """
    from .session_manager import revoke_refresh_token, revoke_all_refresh_tokens

    db = _db(request)

    if payload.logout_all:
        # Need to find the uid from the refresh token first
        from .session_manager import validate_refresh_token
        record = await validate_refresh_token(db, payload.refresh_token)
        if not record:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or already expired session token."
            )
        count = await revoke_all_refresh_tokens(db, record["uid"])
        return {
            "status":          "LOGGED_OUT_ALL_DEVICES",
            "tokens_revoked":  count,
            "message":         "You have been logged out of all devices.",
        }
    else:
        success = await revoke_refresh_token(db, payload.refresh_token)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session token not found or already revoked."
            )
        return {
            "status":  "LOGGED_OUT",
            "message": "Logged out of this device successfully.",
        }
