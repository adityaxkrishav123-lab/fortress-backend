"""
mailbox/instant_help_accept.py
================================
The 2-Step Instant Help Accept Engine.

When an NGO receives an INSTANT_HELP card and clicks Accept:

  STEP 1 — GET /mailbox/instant-help/{card_id}/accept-options
    Returns the list of items from the original request so the NGO
    can see what they are being asked to supply.

  STEP 2 — POST /mailbox/instant-help/{card_id}/commit
    NGO selects which items + quantities they can actually give.
    Tags with X can be cancelled (even with quantity filled).
    On submit, a supply report card is generated for NGO A.
    The agent then checks if the full quantity is met,
    or continues searching the next region.

STATUS LOGIC:
  Original card (NGO A's request):
    ACTIVE      → while searching for suppliers
    ACCEPTED    → when full quantity is committed
    LIMIT_OVER  → when all escalation districts are exhausted
                   but quantity is not fully met

  Individual NGO supply card (NGO B, C, etc.):
    ACCEPTED    → once NGO commits their portion
    (They never show LIMIT_OVER — their part is done)

UNIVERSAL LAW (applies to ALL cards):
  Every action card carries original_message + original_attachment
  from the originating request so both parties always know
  which request the card belongs to.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, field_validator

from auth_gate.catalog import is_valid_instant_item
from auth_gate.models import MemberRank, Role

# BUG-001 FIX: Firestore atomic array operations
try:
    from google.cloud.firestore_v1 import ArrayUnion, Increment
except ImportError:
    ArrayUnion = None
    Increment = None

router = APIRouter(prefix="/api/v1/mailbox/instant-help", tags=["Instant Help — 2-Step Accept"])

# Extra status constants
STATUS_ACTIVE     = "ACTIVE"
STATUS_ACCEPTED   = "ACCEPTED"
STATUS_LIMIT_OVER = "LIMIT_OVER"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class CommittedItem(BaseModel):
    """One item-quantity pair that the NGO agrees to supply."""
    item:     str
    quantity: int

    @field_validator("quantity")
    @classmethod
    def qty_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Quantity must be at least 1.")
        return v

    @field_validator("item")
    @classmethod
    def item_valid(cls, v: str) -> str:
        if not is_valid_instant_item(v):
            raise ValueError(f"'{v}' is not a valid Instant Help item.")
        return v


class CommitSupplyPayload(BaseModel):
    """
    Step 2: NGO submits the items + quantities they can provide.
    Items not included are treated as cancelled (X pressed by NGO).
    """
    committed_items: List[CommittedItem]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _db(r: Request):
    return r.app.state.db


def _get_power_level(role: str, rank: Optional[str]) -> int:
    if role == Role.NGO_ADMIN.value:          return 5
    if role == Role.NGO_MEMBER.value:
        if rank == MemberRank.POWER_GROUP.value: return 4
        return 3
    return 0


async def _require_ngo_actor(request: Request) -> dict:
    role  = request.state.role
    rank  = getattr(request.state, "rank", None)
    level = _get_power_level(role, rank)
    if level < 4:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only NGO Admin or Power Group can commit supply."
        )
    return {
        "uid":    request.state.uid,
        "role":   role,
        "rank":   rank,
        "ngo_id": getattr(request.state, "ngo_id", None),
        "level":  level,
    }


# ---------------------------------------------------------------------------
# STEP 1: Get Accept Options
# GET /mailbox/instant-help/{card_id}/accept-options
# ---------------------------------------------------------------------------

@router.get("/{card_id}/accept-options")
async def get_accept_options(card_id: str, request: Request):
    """
    Step 1 of the 2-step Instant Help accept flow.

    When the NGO clicks Accept on an INSTANT_HELP card, the frontend
    calls this endpoint first to get the list of items being requested.
    The frontend renders these as toggle tags with quantity boxes.

    The NGO can:
      - Fill in how much of each item they can provide
      - Cancel any item tag (X button) they cannot supply
    """
    db   = _db(request)
    info = await _require_ngo_actor(request)

    card_doc = await db.collection("action_cards").document(card_id).get()
    if not card_doc.exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found.")

    card = card_doc.to_dict()

    if card.get("card_type") != "INSTANT_HELP":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This endpoint is only for INSTANT_HELP cards."
        )

    if info["uid"] not in card.get("addressed_to", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This card was not sent to your NGO."
        )

    if card.get("status") != STATUS_ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Card is already {card.get('status')}. Cannot accept."
        )

    return {
        "card_id":           card_id,
        "items_needed":      card.get("items_needed", []),
        "original_message":  card.get("original_message"),
        "original_attachment": card.get("original_attachment"),
        "requester_uid":     card.get("sender_uid"),
        "instruction":       "Select the items you can supply and enter the quantity for each. "
                             "Use the X button to remove items you cannot provide.",
    }


# ---------------------------------------------------------------------------
# STEP 2: Commit Supply
# POST /mailbox/instant-help/{card_id}/commit
# ---------------------------------------------------------------------------

@router.post("/{card_id}/commit")
async def commit_supply(card_id: str, payload: CommitSupplyPayload, request: Request):
    """
    Step 2 of the 2-step Instant Help accept flow.

    NGO submits which items + quantities they can provide.
    Items cancelled with X are simply not included in the payload.

    On success:
      1. A supply report card is created for NGO A showing this NGO's commitment.
      2. The original card's committed quantity is updated.
      3. If fully fulfilled → original card closes as ACCEPTED.
      4. If not → the RegionalAgent continues searching the next region.
      5. If all districts exhausted and not fulfilled → LIMIT_OVER.
    """
    db   = _db(request)
    info = await _require_ngo_actor(request)

    if not payload.committed_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must commit at least one item. To reject, use the Reject button instead."
        )

    card_ref = db.collection("action_cards").document(card_id)
    card_doc = await card_ref.get()
    if not card_doc.exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found.")

    card = card_doc.to_dict()

    if card.get("card_type") != "INSTANT_HELP":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="This endpoint is only for INSTANT_HELP cards.")

    if info["uid"] not in card.get("addressed_to", []):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="This card was not addressed to your NGO.")

    if card.get("status") != STATUS_ACTIVE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Card is already {card.get('status')}.")

    now            = datetime.utcnow().isoformat()
    committed_data = [{"item": ci.item, "quantity": ci.quantity} for ci in payload.committed_items]
    total_committed_this_ngo = sum(ci.quantity for ci in payload.committed_items)

    # --- Generate the Supply Report Card for NGO A ---
    report_card_id = f"SUP-{uuid.uuid4().hex[:8].upper()}"
    original_ngo_id = card.get("ngo_id")   # NGO A who made the request

    # Fetch committing NGO's info for the report
    committer_ngo_doc = await db.collection("ngos").where(
        "admin_uid", "==", info["uid"]
    ).limit(1).get()
    committer_ngo_name = (
        committer_ngo_doc[0].to_dict().get("name", "An NGO")
        if committer_ngo_doc else "An NGO"
    )

    # BUG-007 FIX: Use sender_uid (the NGO that made the request) not original_requester_uid
    supply_report_card = {
        "card_id":              report_card_id,
        "card_type":            "INSTANT_HELP_SUPPLY_REPORT",
        "original_card_id":     card_id,

        # Who made the original request (NGO A)
        "requesting_ngo_id":    original_ngo_id,
        "addressed_to":         [card.get("sender_uid")],   # ✅ BUG-007 FIX: was original_requester_uid

        # Who is supplying (NGO B/C/etc.)
        "supplier_ngo_id":      info["ngo_id"],
        "supplier_ngo_name":    committer_ngo_name,
        "supplier_uid":         info["uid"],

        # What they committed
        "committed_items":      committed_data,
        "total_committed_qty":  total_committed_this_ngo,

        # Original request info (Universal Law)
        "original_message":     card.get("original_message"),
        "original_attachment":  card.get("original_attachment"),
        "original_items_needed": card.get("items_needed", []),

        "status":    STATUS_ACCEPTED,
        "created_at": now,
    }

    await db.collection("action_cards").document(report_card_id).set(supply_report_card)

    # --- GAP 4 FIX: Inventory Auto-Subtraction ---
    # Automatically decrement the committed quantities from the NGO's inventory
    for ci in payload.committed_items:
        try:
            inv_query = db.collection("ngo_inventory").where("admin_uid", "==", info["uid"]).where("item_name", "==", ci.item).limit(1)
            inv_docs = await inv_query.get()
            for doc in inv_docs:
                current_qty = doc.to_dict().get("quantity", 0)
                new_qty = max(0, current_qty - ci.quantity)
                await db.collection("ngo_inventory").document(doc.id).update({
                    "quantity": new_qty,
                    "available": new_qty > 0,
                    "last_updated": now
                })
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"[Inventory Sync] Failed to update inventory for {ci.item}: {e}")


    # --- AUDIT FIX 2: Acceptance Race Condition ---
    # Use Atomic Increment and ArrayUnion to prevent concurrent overwrite
    existing_fulfilled = card.get("quantity_committed", 0)
    new_fulfilled      = existing_fulfilled + total_committed_this_ngo
    quantity_needed    = card.get("quantity_needed", 0)

    log_entry = {
        "supplier_uid":        info["uid"],
        "supplier_ngo_name":   committer_ngo_name,
        "committed_items":     committed_data,
        "committed_qty":       total_committed_this_ngo,
        "report_card_id":      report_card_id,
        "timestamp":           now,
    }

    # Determine new overall status
    if new_fulfilled >= quantity_needed:
        new_main_status = STATUS_ACCEPTED
    else:
        new_main_status = STATUS_ACTIVE     # Still searching

    if ArrayUnion and Increment:
        await card_ref.update({
            "quantity_committed": Increment(total_committed_this_ngo),
            "fulfillment_log":    ArrayUnion([log_entry]),
            "status":             new_main_status,
            "last_updated":       now,
        })
    else:
        # Fallback for dev mode
        fulfillment_log = card.get("fulfillment_log", [])
        fulfillment_log.append(log_entry)
        await card_ref.update({
            "quantity_committed": new_fulfilled,
            "fulfillment_log":    fulfillment_log,
            "status":             new_main_status,
            "last_updated":       now,
        })

    # BUG-003 FIX: Pass updated fulfillment_log so _continue_search
    # knows about the NGO that just committed (prevents re-contacting them)
    if new_main_status == STATUS_ACTIVE:
        remaining = quantity_needed - new_fulfilled
        updated_card_for_search = dict(card)
        updated_card_for_search["fulfillment_log"] = fulfillment_log  # ✅ include just-committed
        updated_card_for_search["quantity_needed"]  = remaining
        await _continue_search(card_id, updated_card_for_search, remaining, db)

    # --- Write NGO audit log ---
    if original_ngo_id:
        await db.collection("ngo_logs").add({
            "ngo_id":      original_ngo_id,
            "actor_uid":   info["uid"],
            "action":      "INSTANT_HELP_SUPPLY_COMMITTED",
            "card_id":     card_id,
            "card_type":   "INSTANT_HELP",
            "report_card_id": report_card_id,
            "committed_qty":  total_committed_this_ngo,
            "timestamp":   now,
        })

    return {
        "report_card_id":      report_card_id,
        "committed_items":     committed_data,
        "total_committed_qty": total_committed_this_ngo,
        "quantity_needed":     quantity_needed,
        "quantity_now_fulfilled": new_fulfilled,
        "main_card_status":    new_main_status,
        "message": (
            "Supply committed. Full request fulfilled. Card closed."
            if new_main_status == STATUS_ACCEPTED
            else f"Supply committed. Still searching for {remaining} more units."
        ),
    }


# ---------------------------------------------------------------------------
# Internal: Continue Search After Partial Fulfillment
# ---------------------------------------------------------------------------

async def _continue_search(card_id: str, card: dict, remaining_qty: int, db) -> None:
    """
    After an NGO commits a partial supply, the RegionalAgent continues
    searching the next region for the remaining quantity.
    If all districts are exhausted without full fulfillment, sets LIMIT_OVER.
    """
    try:
        from dispatch.regional_agent import RegionalAgent

        # Pass the remaining quantity so the agent knows what's still needed
        updated_card = dict(card)
        updated_card["quantity_needed"] = remaining_qty

        result = await RegionalAgent(mode="INSTANT_HELP").continue_partial(
            card_id, updated_card, db
        )
        if result == "EXHAUSTED":
            await db.collection("action_cards").document(card_id).update({
                "status":         STATUS_LIMIT_OVER,
                "limit_over_at":  datetime.utcnow().isoformat(),
            })
            import logging
            logging.getLogger(__name__).warning(
                f"[InstantHelpAccept] Card {card_id}: all regions exhausted. "
                f"Remaining unfulfilled: {remaining_qty}. Status → LIMIT_OVER."
            )
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(
            f"[InstantHelpAccept] Continue search failed for {card_id}: {e}"
        )
