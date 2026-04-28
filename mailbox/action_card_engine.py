"""
mailbox/action_card_engine.py
==============================
Module 1: The Action Card Engine — The Heart of Project Powerhouse.

All Mailbox endpoints live here. Every route enforces the 5 Power Levels
at the API level before returning any data or allowing any action.

Card Lifecycle: ACTIVE → ACCEPTED | REJECTED
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from pydantic import BaseModel

from auth_gate.models import MemberRank, Role

# BUG-011 FIX: Graceful import for storage_utils — prevents full module crash if file missing
try:
    from auth_gate.storage_utils import upload_document
except ImportError:
    async def upload_document(file, folder="", uid=""):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="File storage service is not configured. Contact admin."
        )

# BUG-001 FIX: Firestore atomic array operations
try:
    from google.cloud.firestore_v1 import ArrayUnion, ArrayRemove
except ImportError:
    ArrayUnion = None
    ArrayRemove = None

router = APIRouter(prefix="/api/v1/mailbox", tags=["Mailbox — Action Card Engine"])


# ---------------------------------------------------------------------------
# Card Status Constants
# ---------------------------------------------------------------------------
STATUS_ACTIVE     = "ACTIVE"
STATUS_ACCEPTED   = "ACCEPTED"
STATUS_REJECTED   = "REJECTED"
STATUS_LIMIT_OVER = "LIMIT_OVER"   # Instant Help: all regions exhausted, partial/no fulfillment

# Card Types
TYPE_CITIZEN_SOS         = "CITIZEN_SOS"
TYPE_CITIZEN_SERVICE     = "CITIZEN_SERVICE"
TYPE_VOLUNTEER_REQUEST   = "NGO_VOLUNTEER_REQUEST"
TYPE_NGO_TO_NGO          = "NGO_TO_NGO_SERVICE"
TYPE_INSTANT_HELP        = "INSTANT_HELP"


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------

class CreateRequestPayload(BaseModel):
    card_type:   str
    ngo_type:    Optional[str] = None
    ngo_tags:    Optional[list[str]] = None
    message:     Optional[str] = None       # Free-text — anything the sender wants to say
    attachment:  Optional[str] = None       # Pre-uploaded file URL (uploaded via /card/attachment first)
    quantity:    Optional[int] = None
    items_needed: Optional[list[str]] = None  # For INSTANT_HELP
    latitude:    Optional[float] = None
    longitude:   Optional[float] = None


class NGORaiseRequestPayload(BaseModel):
    """
    Unified NGO 'Raise Request' payload.
    The frontend shows a popup with two options: Instant Help or Service.
    Both are routed through this single endpoint.
    """
    request_type: str           # "INSTANT_HELP" or "NGO_SERVICE"
    # For INSTANT_HELP
    items_needed: Optional[list[str]] = None
    # For NGO_SERVICE
    ngo_type:     Optional[str] = None
    ngo_tags:     Optional[list[str]] = None
    # Common
    message:      Optional[str] = None
    attachment:   Optional[str] = None
    quantity:     Optional[int] = None


class RespondPayload(BaseModel):
    card_id:  str
    response: str       # "ACCEPT" or "REJECT"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _db(request: Request):
    return request.app.state.db


def _get_power_level(role: str, rank: Optional[str]) -> int:
    """Converts role + rank to a numeric power level (1–5)."""
    if role == Role.NGO_ADMIN.value:
        return 5
    if role == Role.NGO_MEMBER.value:
        if rank == MemberRank.POWER_GROUP.value:
            return 4
        return 3    # MEMBER rank
    if role == Role.CITIZEN.value:
        return 2
    if role == Role.VOLUNTEER.value:
        return 1
    return 0


async def _get_caller_info(request: Request) -> dict:
    """Extracts uid, role, rank, ngo_id from the request state (set by middleware)."""
    return {
        "uid":    request.state.uid,
        "role":   request.state.role,
        "rank":   getattr(request.state, "rank", None),
        "ngo_id": getattr(request.state, "ngo_id", None),
    }


# ---------------------------------------------------------------------------
# ENDPOINT 1: Create a New Action Card
# POST /mailbox/create-request
# ---------------------------------------------------------------------------

@router.post("/create-request")
async def create_request(payload: CreateRequestPayload, request: Request):
    """
    Creates a new Action Card and triggers the correct AI Dispatch Agent.

    Who can call this:
    - CITIZEN           → CITIZEN_SOS, CITIZEN_SERVICE, INSTANT_HELP
    - NGO_ADMIN         → NGO_VOLUNTEER_REQUEST, NGO_TO_NGO_SERVICE
    - POWER_GROUP       → NGO_VOLUNTEER_REQUEST, NGO_TO_NGO_SERVICE
    """
    db    = _db(request)
    info  = await _get_caller_info(request)
    level = _get_power_level(info["role"], info["rank"])

    # --- Permission Gates ---
    citizen_types = {TYPE_CITIZEN_SOS, TYPE_CITIZEN_SERVICE, TYPE_INSTANT_HELP}
    ngo_types     = {TYPE_VOLUNTEER_REQUEST, TYPE_NGO_TO_NGO}

    if payload.card_type in citizen_types and level != 2:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only Citizens can create this type of request.")
    if payload.card_type in ngo_types and level < 4:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only NGO Admin or Power Group can create this request.")
    if level == 3:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Members are observers only and cannot create requests.")

    card_id = f"CARD-{uuid.uuid4().hex[:10].upper()}"
    now     = datetime.utcnow().isoformat()

    # BUG-004 FIX: Store sender_region on card at creation time
    # Fetch sender's region so escalation_agent can use it without a DB lookup
    sender_region = ""
    try:
        sender_doc = await db.collection("users").document(info["uid"]).get()
        if sender_doc.exists:
            sender_region = sender_doc.to_dict().get("region", "")
    except Exception:
        pass

    card_doc = {
        "card_id":     card_id,
        "card_type":   payload.card_type,
        "sender_uid":  info["uid"],
        "sender_role": info["role"],
        "sender_region": sender_region,          # ✅ BUG-004 FIX
        "ngo_id":      info["ngo_id"],
        "ngo_type":    payload.ngo_type,
        "ngo_tags":    payload.ngo_tags or [],
        # UNIVERSAL LAW
        "original_message":    payload.message,
        "original_attachment": payload.attachment,
        "quantity":      payload.quantity,
        "quantity_needed": payload.quantity or 0,
        "quantity_committed": 0,
        "items_needed":  getattr(payload, "items_needed", None) or [],
        "latitude":      getattr(payload, "latitude", None),
        "longitude":     getattr(payload, "longitude", None),
        "status":        STATUS_ACTIVE,
        "attachment_url": payload.attachment,
        "created_at":    now,
        "expires_at":    (datetime.utcnow() + timedelta(hours=24)).isoformat(),
        "accepted_by":   [],
        "rejected_by":   [],        # ✅ BUG-012 FIX: track rejections
        "fulfillment_log": [],
    }

    await db.collection("action_cards").document(card_id).set(card_doc)

    # --- Trigger the correct AI Agent (async background task) ---
    await _trigger_agent(payload.card_type, card_id, card_doc, db)

    # --- Write to NGO audit log ---
    if info["ngo_id"]:
        await _write_ngo_log(db, info["ngo_id"], info["uid"], "CARD_CREATED", card_id, payload.card_type)

    return {"card_id": card_id, "status": STATUS_ACTIVE, "created_at": now}


# ---------------------------------------------------------------------------
# ENDPOINT 1B: Unified NGO Raise Request (the 'NGO to NGO +' button)
# POST /mailbox/ngo-raise-request
# ---------------------------------------------------------------------------

@router.post("/ngo-raise-request")
async def ngo_raise_request(payload: NGORaiseRequestPayload, request: Request):
    """
    The single unified entry point for the NGO 'Raise Request' flow.
    When the NGO clicks the 'NGO to NGO (+)' button, a popup shows two
    options (Instant Help / Service). Both submit to this endpoint.

    request_type = "INSTANT_HELP"  → Routes to RegionalAgent (inventory mode)
    request_type = "NGO_SERVICE"   → Routes to RegionalAgent (service mode)

    Who can call: NGO Admin (L5) or Power Group (L4) only.
    """
    db    = _db(request)
    info  = await _get_caller_info(request)
    level = _get_power_level(info["role"], info["rank"])

    if level < 4:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only NGO Admin or Power Group can raise NGO-to-NGO requests."
        )

    if payload.request_type not in ("INSTANT_HELP", "NGO_SERVICE"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="request_type must be 'INSTANT_HELP' or 'NGO_SERVICE'."
        )

    if payload.request_type == "INSTANT_HELP" and not payload.items_needed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Instant Help requires at least one item in items_needed."
        )

    if payload.request_type == "NGO_SERVICE" and not payload.ngo_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="NGO Service request requires ngo_type."
        )

    card_type = TYPE_INSTANT_HELP if payload.request_type == "INSTANT_HELP" else TYPE_NGO_TO_NGO
    card_id   = f"CARD-{uuid.uuid4().hex[:10].upper()}"
    now       = datetime.utcnow().isoformat()

    # N-03 FIX: Fetch sender_region for NGO-raised cards too.
    # Without this, MonitorAgent's region filter and EscalationAgent's
    # get_escalation_districts() both silently fail for NGO-to-NGO cards.
    sender_region = ""
    try:
        sender_doc = await db.collection("users").document(info["uid"]).get()
        if sender_doc.exists:
            sender_region = sender_doc.to_dict().get("region", "")
    except Exception:
        pass

    card_doc = {
        "card_id":     card_id,
        "card_type":   card_type,
        "sender_uid":  info["uid"],
        "sender_role": info["role"],
        "sender_region": sender_region,          # ✅ N-03 FIX
        "ngo_id":      info["ngo_id"],
        # UNIVERSAL LAW
        "original_message":    payload.message,
        "original_attachment": payload.attachment,
        # Fields by type
        "items_needed":   payload.items_needed or [],
        "ngo_type":       payload.ngo_type,
        "ngo_tags":       payload.ngo_tags or [],
        "quantity_needed":    payload.quantity or 0,
        "quantity_committed": 0,
        "fulfillment_log":    [],
        "status":      STATUS_ACTIVE,
        "created_at":  now,
        "expires_at":  (datetime.utcnow() + timedelta(hours=24)).isoformat(),
    }

    await db.collection("action_cards").document(card_id).set(card_doc)
    await _trigger_agent(card_type, card_id, card_doc, db)

    if info["ngo_id"]:
        await _write_ngo_log(db, info["ngo_id"], info["uid"], "CARD_CREATED", card_id, card_type)

    return {
        "card_id":       card_id,
        "card_type":     card_type,
        "request_type":  payload.request_type,
        "status":        STATUS_ACTIVE,
        "created_at":    now,
        "message":       f"{'Instant Help' if payload.request_type == 'INSTANT_HELP' else 'Service'} request dispatched. NGOs in your district will receive this card.",
    }


# ---------------------------------------------------------------------------
# ENDPOINT 2: View Inbox (Role-filtered Mailbox)
# GET /mailbox/inbox
# ---------------------------------------------------------------------------

@router.get("/inbox")
async def get_inbox(request: Request):
    """
    Returns the caller's Mailbox, filtered by their Power Level.

    - L5 Admin / L4 Power Group : All cards for their NGO + can_act = True
    - L3 Member                 : All cards for their NGO + can_act = False
    - L2 Citizen                : Only their own cards
    - L1 Volunteer              : Only cards addressed to them
    """
    db    = _db(request)
    info  = await _get_caller_info(request)
    level = _get_power_level(info["role"], info["rank"])
    uid   = info["uid"]
    ngo_id = info["ngo_id"]

    cards = []

    if level >= 3 and ngo_id:
        # NGO members see all cards related to their NGO
        query = db.collection("action_cards").where("ngo_id", "==", ngo_id)
        docs  = await query.get()
        cards = [doc.to_dict() for doc in docs]

    elif level == 2:
        # BUG-008 FIX: Citizen sees BOTH their sent cards AND cards addressed to them
        sent_query    = db.collection("action_cards").where("sender_uid", "==", uid)
        recv_query    = db.collection("action_cards").where("addressed_to", "array_contains", uid)
        sent_docs     = await sent_query.get()
        recv_docs     = await recv_query.get()
        seen_ids      = set()
        for doc in list(sent_docs) + list(recv_docs):
            d = doc.to_dict()
            if d["card_id"] not in seen_ids:
                cards.append(d)
                seen_ids.add(d["card_id"])

    elif level == 1:
        # Volunteer sees only cards addressed to them
        query = db.collection("action_cards").where("addressed_to", "array_contains", uid)
        docs  = await query.get()
        cards = [doc.to_dict() for doc in docs]

    # BUG-014 FIX: Volunteer can_act = True only for their own volunteer cards
    for card in cards:
        if level == 1:
            card["can_act"] = card.get("card_type") == TYPE_VOLUNTEER_REQUEST
        else:
            card["can_act"] = level >= 4

        # --- AUDIT FIX 1: PII Leak in Inbox View ---
        # Mask contact info if the card is not yet accepted and the caller is not the sender
        is_sender = card.get("sender_uid") == uid
        if card.get("status") != STATUS_ACCEPTED and not is_sender:
            sensitive_keys = ["sender_phone", "sender_email", "ngo_contact", "ngo_admin_phone"]
            for key in sensitive_keys:
                if key in card:
                    card[key] = "[HIDDEN UNTIL ACCEPTED]"

    return {"inbox": cards, "total": len(cards), "can_act": level >= 4}


# ---------------------------------------------------------------------------
# ENDPOINT 3: Respond to an Action Card (Accept / Reject)
# POST /mailbox/respond
# ---------------------------------------------------------------------------

@router.post("/respond")
async def respond_to_card(payload: RespondPayload, request: Request):
    """
    Accept or Reject an Action Card.

    Who can call:
    - NGO_ADMIN (L5), POWER_GROUP (L4) → For all NGO-related cards
    - VOLUNTEER (L1)                    → ONLY for NGO_VOLUNTEER_REQUEST cards
    Members (L3) and Citizens (L2) cannot call this.
    """
    db    = _db(request)
    info  = await _get_caller_info(request)
    level = _get_power_level(info["role"], info["rank"])

    # --- Permission Gate ---
    if level == 3:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Members are observers only. No action allowed.")
    if level == 2:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Citizens cannot respond to cards directly.")

    if payload.response not in ("ACCEPT", "REJECT"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="response must be 'ACCEPT' or 'REJECT'.")

    card_ref = db.collection("action_cards").document(payload.card_id)
    card_doc = await card_ref.get()
    if not card_doc.exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found.")

    card = card_doc.to_dict()

    # --- Volunteer can ONLY respond to volunteer request cards ---
    if level == 1:  # VOLUNTEER
        if card["card_type"] != TYPE_VOLUNTEER_REQUEST:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="Volunteers can only respond to volunteer request cards.")
        if info["uid"] not in card.get("addressed_to", []):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="This card was not sent to you.")

    # BUG-002 FIX: Block INSTANT_HELP Accept via this endpoint — must use 2-step flow
    if card["card_type"] == TYPE_INSTANT_HELP and payload.response == "ACCEPT":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Instant Help requests require a 2-step supply commit. "
                   "Use POST /api/v1/mailbox/instant-help/{card_id}/commit instead."
        )

    if card["status"] != STATUS_ACTIVE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Card is already {card['status']}. Cannot respond.")

    new_status = STATUS_ACCEPTED if payload.response == "ACCEPT" else STATUS_REJECTED
    now = datetime.utcnow().isoformat()

    if card["card_type"] == TYPE_VOLUNTEER_REQUEST and payload.response == "ACCEPT":
        # BUG-001 FIX: Use Firestore ArrayUnion for atomic append (no race condition)
        if ArrayUnion:
            await card_ref.update({
                "accepted_by":  ArrayUnion([info["uid"]]),
                "last_updated": now,
            })
        else:
            # Fallback if google-cloud-firestore not available (dev mode)
            accepted_by = card.get("accepted_by", [])
            if info["uid"] not in accepted_by:
                accepted_by.append(info["uid"])
            await card_ref.update({"accepted_by": accepted_by, "last_updated": now})

    elif card["card_type"] == TYPE_VOLUNTEER_REQUEST and payload.response == "REJECT":
        # BUG-012 FIX: Track rejections in rejected_by, remove from addressed_to atomically
        if ArrayRemove and ArrayUnion:
            await card_ref.update({
                "addressed_to": ArrayRemove([info["uid"]]),
                "rejected_by":  ArrayUnion([info["uid"]]),
                "last_updated": now,
            })
        else:
            addressed_to = card.get("addressed_to", [])
            rejected_by  = card.get("rejected_by", [])
            if info["uid"] in addressed_to:
                addressed_to.remove(info["uid"])
            if info["uid"] not in rejected_by:
                rejected_by.append(info["uid"])
            await card_ref.update({
                "addressed_to": addressed_to,
                "rejected_by":  rejected_by,
                "last_updated": now,
            })
    else:
        # NGO Admin / Power Group accepting/rejecting a Citizen or NGO-to-NGO card
        await card_ref.update({
            "status":       new_status,
            "responded_by": info["uid"],
            "last_updated": now,
        })
        if new_status == STATUS_ACCEPTED and card["card_type"] in (TYPE_CITIZEN_SOS, TYPE_CITIZEN_SERVICE):
            await _send_acceptance_confirmation_to_citizen(db, card, info)

    # Write to NGO audit log
    if info["ngo_id"]:
        await _write_ngo_log(db, info["ngo_id"], info["uid"],
                             f"CARD_{new_status}", payload.card_id, card["card_type"])

    return {
        "card_id":    payload.card_id,
        "new_status": new_status,
        "responded_by": info["uid"],
        "timestamp":  now,
    }


# ---------------------------------------------------------------------------
# ENDPOINT 4: View a Single Action Card (Full Detail)
# GET /mailbox/card/{card_id}
# ---------------------------------------------------------------------------

@router.get("/card/{card_id}")
async def get_card_detail(card_id: str, request: Request):
    """
    Returns the full Action Card: message, attachment, status, profiles.
    Only parties in the connection can view this card.
    """
    db   = _db(request)
    info = await _get_caller_info(request)
    uid  = info["uid"]

    card_doc = await db.collection("action_cards").document(card_id).get()
    if not card_doc.exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found.")

    card = card_doc.to_dict()

    # --- Connection Check: only parties in this card can view it ---
    is_sender    = card.get("sender_uid") == uid
    is_addressed = uid in card.get("addressed_to", [])
    is_ngo_staff = (info["ngo_id"] and info["ngo_id"] == card.get("ngo_id"))
    is_accepted  = uid in card.get("accepted_by", [])

    if not any([is_sender, is_addressed, is_ngo_staff, is_accepted]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="You are not part of this connection.")

    level = _get_power_level(info["role"], info["rank"])
    card["can_act"] = level >= 4 or (level == 1 and card["card_type"] == TYPE_VOLUNTEER_REQUEST)

    # --- GAP 2 FIX: Identity Handshake (Security Gate) ---
    # Mask contact info if the card is not yet accepted and the caller is not the sender
    if card.get("status") != STATUS_ACCEPTED and not is_sender:
        sensitive_keys = ["sender_phone", "sender_email", "ngo_contact", "ngo_admin_phone"]
        for key in sensitive_keys:
            if key in card:
                card[key] = "[HIDDEN UNTIL ACCEPTED]"
                
    return card


# ---------------------------------------------------------------------------
# ENDPOINT 4B: Generate AI Report (The Final Node)
# GET /mailbox/card/{card_id}/report
# ---------------------------------------------------------------------------

@router.get("/card/{card_id}/report")
async def get_card_report(card_id: str, request: Request):
    """
    GAP 5 FIX: AI Report Compiler.
    Gathers donor/acceptor data and generates the final mission receipt.
    Only available for ACCEPTED cards.
    """
    db   = _db(request)
    info = await _get_caller_info(request)
    uid  = info["uid"]

    card_doc = await db.collection("action_cards").document(card_id).get()
    if not card_doc.exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found.")

    card = card_doc.to_dict()

    if card.get("status") != STATUS_ACCEPTED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Report is only available for ACCEPTED missions.")

    # Connection Check
    is_sender    = card.get("sender_uid") == uid
    is_addressed = uid in card.get("addressed_to", [])
    is_ngo_staff = (info["ngo_id"] and info["ngo_id"] == card.get("ngo_id"))
    is_accepted  = uid in card.get("accepted_by", [])

    if not any([is_sender, is_addressed, is_ngo_staff, is_accepted]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not authorized to view this report.")

    # Compile the report data
    report = {
        "report_id": f"RPT-{card_id}",
        "mission_type": card.get("card_type"),
        "timestamp": datetime.utcnow().isoformat(),
        "original_request": {
            "message": card.get("original_message"),
            "items_needed": card.get("items_needed", []),
            "quantity_requested": card.get("quantity_needed", 0),
        },
        "fulfillment_summary": {
            "quantity_fulfilled": card.get("quantity_committed", 0),
            "logs": card.get("fulfillment_log", []),
            "accepted_by": card.get("accepted_by", []),
        },
        "status": "SUCCESSFUL" if card.get("quantity_committed", 0) >= card.get("quantity_needed", 0) else "PARTIAL",
    }
    
    return report


# ---------------------------------------------------------------------------
# ENDPOINT 5: Upload Attachment to a Card
# POST /mailbox/card/{card_id}/attachment
# ---------------------------------------------------------------------------

@router.post("/card/{card_id}/attachment")
async def upload_card_attachment(
    card_id: str,
    request: Request,
    file: UploadFile = File(...),
):
    """
    Attach a file (image/PDF) to an existing Action Card.
    Only the sender or an NGO Admin/Power Group on the card can attach files.
    """
    _validate_upload(file)
    db   = _db(request)
    info = await _get_caller_info(request)

    card_doc = await db.collection("action_cards").document(card_id).get()
    if not card_doc.exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found.")

    card  = card_doc.to_dict()
    level = _get_power_level(info["role"], info["rank"])

    is_sender   = card.get("sender_uid") == info["uid"]
    is_ngo_auth = info["ngo_id"] == card.get("ngo_id") and level >= 4

    if not (is_sender or is_ngo_auth):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only the sender or NGO Admin/Power Group can attach files.")

    storage_path = await upload_document(file, folder="card_attachments", uid=card_id)
    await db.collection("action_cards").document(card_id).update({
        "attachment_url": storage_path,
        "attachment_uploaded_by": info["uid"],
        "attachment_uploaded_at": datetime.utcnow().isoformat(),
    })

    return {"card_id": card_id, "attachment_url": storage_path}


# ---------------------------------------------------------------------------
# ENDPOINT 6: Cancel a Card (Citizen only, ACTIVE cards only)
# DELETE /mailbox/cancel/{card_id}
# ---------------------------------------------------------------------------

@router.delete("/cancel/{card_id}")
async def cancel_card(card_id: str, request: Request):
    """
    Cancel an ACTIVE card before it is accepted.
    - Citizen: can cancel their own request.
    - NGO Admin / Power Group (L4+): can cancel cards their NGO created.
    """
    db   = _db(request)
    info = await _get_caller_info(request)
    level = _get_power_level(info["role"], info["rank"])

    # BUG-009 FIX: Allow NGOs to cancel their own requests too
    if level == 3:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Members cannot cancel cards.")
    if level == 0:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Unauthorized.")

    card_ref = db.collection("action_cards").document(card_id)
    card_doc = await card_ref.get()
    if not card_doc.exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found.")

    card = card_doc.to_dict()

    # Permission: Citizen can cancel their own, NGO L4+ can cancel their NGO's cards
    is_own_card    = card.get("sender_uid") == info["uid"]
    is_ngo_cancel  = level >= 4 and info["ngo_id"] == card.get("ngo_id")

    if not (is_own_card or is_ngo_cancel):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="You can only cancel cards you or your NGO created.")

    if card.get("status") != STATUS_ACTIVE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Only ACTIVE cards can be cancelled.")

    await card_ref.update({
        "status":       STATUS_REJECTED,
        "cancelled_by": info["uid"],
        "cancelled_at": datetime.utcnow().isoformat(),
    })

    # --- AUDIT FIX 3: Fragment Orphanage (Cascade Cancel) ---
    # If this parent card was fragmented, kill all the sub-cards too
    fragmented_into = card.get("fragmented_into", [])
    if fragmented_into:
        for frag_id in fragmented_into:
            await db.collection("action_cards").document(frag_id).update({
                "status":       STATUS_REJECTED,
                "cancelled_by": info["uid"],
                "cancelled_at": datetime.utcnow().isoformat(),
                "cancellation_reason": "PARENT_CANCELLED"
            })

    if info["ngo_id"]:
        await _write_ngo_log(db, info["ngo_id"], info["uid"], "CARD_CANCELLED", card_id, card["card_type"])

    return {"card_id": card_id, "status": STATUS_REJECTED, "message": "Card cancelled successfully."}



# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------

async def _trigger_agent(card_type: str, card_id: str, card_doc: dict, db):
    """Fires the correct AI Dispatch Agent based on the card type."""
    from dispatch.citizen_agent import CitizenAgent
    from dispatch.regional_agent import RegionalAgent
    from dispatch.manpower_agent import ManpowerAgent

    try:
        if card_type in (TYPE_CITIZEN_SOS, TYPE_CITIZEN_SERVICE):
            await CitizenAgent().dispatch(card_id, card_doc, db)
        elif card_type == TYPE_INSTANT_HELP:
            await RegionalAgent(mode="INSTANT_HELP").dispatch(card_id, card_doc, db)
        elif card_type == TYPE_NGO_TO_NGO:
            await RegionalAgent(mode="NGO_SERVICE").dispatch(card_id, card_doc, db)
        elif card_type == TYPE_VOLUNTEER_REQUEST:
            await ManpowerAgent().dispatch(card_id, card_doc, db)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Agent dispatch failed for {card_id}: {e}")


async def _send_acceptance_confirmation_to_citizen(db, original_card: dict, ngo_info: dict):
    """
    When an NGO accepts a Citizen's request, automatically send a
    confirmation Action Card back to the Citizen with:
    - The NGO's name and contact details
    - The status of their original request
    - The NGO Admin's profile (so Citizen can reach them)
    """
    import uuid
    citizen_uid = original_card.get("sender_uid")
    ngo_id      = ngo_info.get("ngo_id")
    now         = datetime.utcnow().isoformat()

    # Fetch NGO details to include in the confirmation card
    ngo_doc = await db.collection("ngos").document(ngo_id).get() if ngo_id else None
    ngo_name = ngo_doc.to_dict().get("name", "NGO") if ngo_doc and ngo_doc.exists else "An NGO"

    confirm_card_id = f"CONF-{uuid.uuid4().hex[:8].upper()}"

    await db.collection("action_cards").document(confirm_card_id).set({
        "card_id":      confirm_card_id,
        "card_type":    "ACCEPTANCE_CONFIRMATION",
        "sender_uid":   ngo_info["uid"],
        "sender_role":  ngo_info["role"],
        "ngo_id":       ngo_id,
        "addressed_to": [citizen_uid],
        "original_card_id":   original_card.get("card_id"),
        # UNIVERSAL LAW: carry the citizen's original message + attachment so they know which request
        "original_message":   original_card.get("original_message"),
        "original_attachment": original_card.get("original_attachment"),
        "ngo_name":     ngo_name,
        "ngo_contact":  ngo_doc.to_dict().get("ngo_contact") if ngo_doc and ngo_doc.exists else None,
        "ngo_admin_uid": ngo_info["uid"],
        "status":       STATUS_ACCEPTED,
        "created_at":   now,
    })


async def _generate_volunteer_roster_report(db, card_id: str, card: dict, accepted_profiles: list):
    """
    Called by MonitorAgent when a volunteer card's quota is filled.
    Generates a structured roster report and saves it to Firestore.
    The NGO Admin can download this as a JSON/CSV file from the frontend.

    Report contains:
    - Card summary (what was requested, how many needed, how many accepted)
    - Full profile list of all accepted volunteers (name, phone, profession, region)
    - Timestamp of report generation
    """
    ngo_id   = card.get("ngo_id")
    now      = datetime.utcnow().isoformat()

    report = {
        "report_id":      f"RPT-{card_id}",
        "card_id":        card_id,
        "ngo_id":         ngo_id,
        "generated_at":   now,
        "request_summary": {
            "card_type":       card.get("card_type"),
            "tags_requested":  card.get("ngo_tags", []),
            "quantity_needed": card.get("quantity", 0),
            "quantity_filled": len(accepted_profiles),
            "status":          "QUOTA_FILLED",
        },
        "volunteers": [
            {
                "name":       p.get("name"),
                "phone":      p.get("phone"),
                "profession": p.get("profession"),
                "profession_tags": p.get("profession_tags", []),
                "region":     p.get("region"),
            }
            for p in accepted_profiles
        ],
    }

    # Save report to Firestore — NGO Admin can query and download
    await db.collection("volunteer_reports").document(f"RPT-{card_id}").set(report)

    # Update the original card with the report reference
    await db.collection("action_cards").document(card_id).update({
        "volunteer_report_id": f"RPT-{card_id}",
        "report_generated_at": now,
    })

    import logging
    logging.getLogger(__name__).info(
        f"[ReportEngine] Volunteer roster report generated for card {card_id}: "
        f"{len(accepted_profiles)} volunteers."
    )


async def _write_ngo_log(db, ngo_id: str, actor_uid: str, action: str, card_id: str, card_type: str):
    """Appends an immutable entry to the NGO audit log."""
    await db.collection("ngo_logs").add({
        "ngo_id":     ngo_id,
        "actor_uid":  actor_uid,
        "action":     action,
        "card_id":    card_id,
        "card_type":  card_type,
        "timestamp":  datetime.utcnow().isoformat(),
    })


def _validate_upload(file: UploadFile, max_mb: int = 10) -> None:
    """Enforce JPG/PNG/PDF only and 10MB max size for card attachments."""
    allowed = {"image/jpeg", "image/png", "application/pdf"}
    if file.content_type not in allowed:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Only JPG, PNG, or PDF accepted. Got: {file.content_type}",
        )
    # Check file size (file.size is set by FastAPI from Content-Length)
    max_bytes = max_mb * 1024 * 1024
    if hasattr(file, "size") and file.size and file.size > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum allowed size is {max_mb}MB.",
        )

# ===========================================================================
# 6. MAILBOX CLEANUP & GLOW LOGIC
# ===========================================================================

@router.post("/upload-attachment")
async def upload_card_attachment(request: Request, file: UploadFile = File(...)):
    """Uploads an attachment for an Action Card (Max 2MB per user request)."""
    _validate_upload(file, max_mb=2)
    uid = request.state.uid
    url = await upload_document(file, folder="action_cards", uid=uid)
    return {"attachment_url": url}

@router.post("/mark-read")
async def mark_mailbox_read(request: Request):
    """Turns off the 'Glow' on the user's dashboard."""
    db = _db(request)
    uid = request.state.uid
    await db.collection("users").document(uid).update({"has_unread_updates": False})
    return {"status": "success", "glow": False}

@router.delete("/archive/{card_id}")
async def archive_card(card_id: str, request: Request):
    """
    Manually clean an Action Card from the user's server-side mailbox view.
    Usually called after the frontend moves it to Local Storage.
    """
    db = _db(request)
    uid = request.state.uid
    card_ref = db.collection("action_cards").document(card_id)
    # Using ArrayRemove to remove the user from 'addressed_to' so they no longer see it
    if ArrayRemove:
        await card_ref.update({"addressed_to": ArrayRemove([uid])})
    else:
        # Fallback
        card_doc = await card_ref.get()
        if card_doc.exists:
            data = card_doc.to_dict()
            addressed_to = data.get("addressed_to", [])
            if uid in addressed_to:
                addressed_to.remove(uid)
                await card_ref.update({"addressed_to": addressed_to})
                
    return {"status": "archived"}
