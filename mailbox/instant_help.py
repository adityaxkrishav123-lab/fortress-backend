"""
mailbox/instant_help.py
========================
Module 2: The Instant Help Engine.

The fast lane for physical goods (NGO to NGO).
NGO Admin/Power Group picks named items from INSTANT_HELP_ITEMS catalog and submits.

The RegionalAgent (INSTANT_HELP mode) handles the matching by searching inventory.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, field_validator

from auth_gate.catalog import INSTANT_HELP_ITEMS, is_valid_instant_item
from auth_gate.models import Role

router = APIRouter(prefix="/api/v1/instant-help", tags=["Instant Help"])


# ---------------------------------------------------------------------------
# Request Model
# ---------------------------------------------------------------------------

class InstantHelpRequest(BaseModel):
    """NGO picks 1 or more items from the INSTANT_HELP_ITEMS flat list."""
    items:   List[str]      # e.g. ["Blood Bag - O+", "Oxygen Cylinder"]
    message: str = ""       # Optional short note
    latitude: float | None = None
    longitude: float | None = None

    @field_validator("items")
    @classmethod
    def items_valid(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("At least one item must be selected.")
        for item in v:
            if not is_valid_instant_item(item):
                raise ValueError(
                    f"'{item}' is not a valid Instant Help item. "
                    f"Please select from the approved catalog."
                )
        return v


# ---------------------------------------------------------------------------
# ENDPOINT: Citizen submits an Instant Help request
# POST /instant-help/request
# ---------------------------------------------------------------------------

@router.post("/request")
async def create_instant_help_request(payload: InstantHelpRequest, request: Request):
    """
    NGO-to-NGO Instant Help endpoint.
    Creates an INSTANT_HELP Action Card and triggers the RegionalAgent
    in INSTANT_HELP mode to find NGOs with matching inventory.
    """
    db   = request.app.state.db
    uid  = request.state.uid
    role = request.state.role

    rank = getattr(request.state, "rank", None)

    if role not in (Role.NGO_ADMIN.value, Role.NGO_MEMBER.value):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only NGO Admins and Power Group members can submit Instant Help requests."
        )

    if role == Role.NGO_MEMBER.value and rank != "POWER_GROUP":
         raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only NGO Admins and Power Group members can submit Instant Help requests."
        )

    ngo_doc = await db.collection("users").document(uid).get()
    if not ngo_doc.exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    ngo_data = ngo_doc.to_dict()

    card_id = f"IH-{uuid.uuid4().hex[:10].upper()}"
    now     = datetime.utcnow().isoformat()

    card_doc = {
        "card_id":      card_id,
        "card_type":    "INSTANT_HELP",
        "sender_uid":   uid,
        "sender_role":  role,
        "sender_region": ngo_data.get("region"),
        "items_needed": payload.items,
        "message":      payload.message,
        "latitude":     payload.latitude,
        "longitude":    payload.longitude,
        "status":       "ACTIVE",
        "attachment_url": None,
        "addressed_to": [],
        "created_at":   now,
        "expires_at":   (datetime.utcnow() + timedelta(hours=24)).isoformat(),
        "accepted_by":  [],
        "ngo_id":       None,     # Will be filled once an NGO accepts
    }

    await db.collection("action_cards").document(card_id).set(card_doc)

    # Trigger RegionalAgent in INSTANT_HELP mode (background)
    try:
        from dispatch.regional_agent import RegionalAgent
        await RegionalAgent(mode="INSTANT_HELP").dispatch(card_id, card_doc, db)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"[InstantHelp] Agent dispatch failed for {card_id}: {e}")

    return {
        "card_id":      card_id,
        "items":        payload.items,
        "status":       "ACTIVE",
        "created_at":   now,
        "message":      "Your request has been sent. NGOs in your area will respond shortly.",
    }


# ---------------------------------------------------------------------------
# ENDPOINT: Get available Instant Help item catalog
# GET /instant-help/catalog
# ---------------------------------------------------------------------------

@router.get("/catalog")
async def get_instant_help_catalog():
    """Returns the full list of available Instant Help items."""
    return {"items": INSTANT_HELP_ITEMS, "total": len(INSTANT_HELP_ITEMS)}
