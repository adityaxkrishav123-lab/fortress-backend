"""
ngo/ngo_log.py
===============
Module 5: The NGO Log — The Transparency Engine.

Chronological, append-only history of every Action Card
created or changed within an NGO.

Who can see:
  - L5 NGO_ADMIN  → Full log, all details
  - L4 POWER_GROUP → Full log, all details
  - L3 MEMBER     → Full log, read-only (no action, no delete)

No one can ever delete or edit a log entry.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from auth_gate.dependencies import require_role
from auth_gate.models import MemberRank, Role

router = APIRouter(prefix="/api/v1/ngo", tags=["NGO Log"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _db(request: Request):
    return request.app.state.db


def _get_power_level(role: str, rank: str | None) -> int:
    if role == Role.NGO_ADMIN.value:
        return 5
    if role == Role.NGO_MEMBER.value:
        if rank == MemberRank.POWER_GROUP.value:
            return 4
        return 3
    return 0


async def _require_ngo_staff(request: Request) -> dict:
    """Ensures caller is at least an NGO Member (L3+). Returns caller info."""
    role  = request.state.role
    rank  = getattr(request.state, "rank", None)
    ngo_id = getattr(request.state, "ngo_id", None)
    level = _get_power_level(role, rank)

    if level < 3:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only NGO staff (Admin, Power Group, Member) can view the NGO Log."
        )
    if not ngo_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="NGO ID not found in your token."
        )
    return {"uid": request.state.uid, "role": role, "rank": rank, "ngo_id": ngo_id, "level": level}


# ---------------------------------------------------------------------------
# ENDPOINT 1: Get Full NGO Log
# GET /ngo/log
# ---------------------------------------------------------------------------

@router.get("/log")
async def get_ngo_log(
    request: Request,
    limit:  int = 50,
    offset: int = 0,
):
    """
    Returns the chronological audit log for the caller's NGO.
    Filtered by the caller's NGO — they cannot see other NGOs' logs.

    L5 Admin + L4 Power Group + L3 Member can all view this.
    No one can delete or edit entries.
    """
    db   = _db(request)
    info = await _require_ngo_staff(request)

    query = (
        db.collection("ngo_logs")
          .where("ngo_id", "==", info["ngo_id"])
          .order_by("timestamp", direction="DESCENDING")
          .limit(limit)
          .offset(offset)
    )
    docs = await query.get()

    log_entries = [doc.to_dict() for doc in docs]

    return {
        "ngo_id":  info["ngo_id"],
        "log":     log_entries,
        "total":   len(log_entries),
        "can_act": info["level"] >= 4,   # Frontend uses this to show/hide buttons
    }


# ---------------------------------------------------------------------------
# ENDPOINT 2: Get a Single Log Entry Detail
# GET /ngo/log/{card_id}
# ---------------------------------------------------------------------------

@router.get("/log/{card_id}")
async def get_log_entry(card_id: str, request: Request):
    """
    Returns all log entries related to a specific Action Card.
    Useful for seeing the full history of a single request.
    """
    db   = _db(request)
    info = await _require_ngo_staff(request)

    query = (
        db.collection("ngo_logs")
          .where("ngo_id",   "==", info["ngo_id"])
          .where("card_id",  "==", card_id)
          .order_by("timestamp", direction="ASCENDING")
    )
    docs = await query.get()

    if not docs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No log entries found for card '{card_id}' in your NGO."
        )

    return {
        "ngo_id":   info["ngo_id"],
        "card_id":  card_id,
        "history":  [doc.to_dict() for doc in docs],
        "can_act":  info["level"] >= 4,
    }


# ---------------------------------------------------------------------------
# ENDPOINT 3: Download Volunteer Roster Report
# GET /ngo/volunteer-report/{card_id}
# ---------------------------------------------------------------------------

@router.get("/volunteer-report/{card_id}")
async def get_volunteer_report(card_id: str, request: Request):
    """
    Returns the auto-generated volunteer roster report for a completed
    volunteer request card. Available once the quota is filled.

    Report contains:
    - Request summary (tags, quantity needed vs filled)
    - Full list of accepted volunteer profiles (name, phone, profession, region)
    - Downloadable as JSON from this endpoint (frontend converts to CSV/PDF)

    Who can access: NGO_ADMIN (L5) and POWER_GROUP (L4) only.
    """
    db   = _db(request)
    info = await _require_ngo_staff(request)

    if info["level"] < 4:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin and Power Group can download volunteer reports."
        )

    report_doc = await db.collection("volunteer_reports").document(f"RPT-{card_id}").get()
    if not report_doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No volunteer report found for card '{card_id}'. "
                   "The report is generated automatically when quota is filled."
        )

    report = report_doc.to_dict()

    # Ensure this NGO is only seeing their own report
    if report.get("ngo_id") != info["ngo_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This report belongs to a different NGO."
        )

    return report
