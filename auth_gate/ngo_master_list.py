"""
auth_gate/ngo_master_list.py
──────────────────────────────────────────────────────────────────────────────
NGO Master List — Firestore collection: `ngo_master_list`

Purpose:
    The `/verify/ngo` endpoint checks a submitted NGO Registration Number
    against this collection before allowing registration.

Collection schema per document:
    Document ID  = ngo_reg_no (e.g. "FCRA-2024-001")
    Fields:
        ngo_reg_no  : str   — same as doc ID (for query convenience)
        name        : str   — official organization name
        category    : str   — "FCRA" | "80G" | "STATE_REG" | etc.
        state       : str   — state of registration
        active      : bool  — False = blacklisted / de-registered

How to Populate:
    Add documents manually via the Firebase Console or an external admin tool.
    This file contains NO dummy data.
"""

import logging

logger = logging.getLogger("auth_gate.ngo_master_list")


async def is_valid_ngo(ngo_reg_no: str, db) -> dict | None:
    """
    Check if an NGO Registration Number exists and is active in the 
    live Firestore `ngo_master_list` collection.

    Args:
        ngo_reg_no: The submitted registration number (already uppercased).
        db:         Firestore AsyncClient.

    Returns:
        The NGO document dict if found and active, else None.
    """
    doc = await db.collection("ngo_master_list").document(ngo_reg_no).get()
    if not doc.exists:
        return None
    
    data = doc.to_dict()
    if not data.get("active", False):
        return None   # De-registered / blacklisted
        
    return data
