"""
auth_gate/ngo_master_list.py
──────────────────────────────────────────────────────────────────────────────
NGO Master List — Firestore collection: `ngo_master_list`

Purpose:
    The `/verify/ngo` endpoint checks a submitted NGO Registration Number
    against this collection before allowing registration.

Seeding:
    Run this script directly to populate the master list:
        python -m backend_api.auth_gate.ngo_master_list

    Or call `seed_master_list(db, NGO_MASTER_LIST)` from your own setup script.

Collection schema per document:
    Document ID  = ngo_reg_no (e.g. "FCRA-2024-001")
    Fields:
        ngo_reg_no  : str   — same as doc ID (for query convenience)
        name        : str   — official organization name
        category    : str   — "FCRA" | "80G" | "STATE_REG" | etc.
        state       : str   — state of registration
        active      : bool  — False = blacklisted / de-registered
"""

import asyncio
import os
import logging

logger = logging.getLogger("auth_gate.ngo_master_list")

# ── Simulated master list ─────────────────────────────────────────────────────
# Replace with a real government API feed or your own curated list.
NGO_MASTER_LIST: list[dict] = [
    {"ngo_reg_no": "FCRA-2024-001", "name": "Relief India Trust",        "category": "FCRA",      "state": "Maharashtra", "active": True},
    {"ngo_reg_no": "FCRA-2024-002", "name": "Seva Foundation",           "category": "FCRA",      "state": "Karnataka",   "active": True},
    {"ngo_reg_no": "80G-2023-100",  "name": "HelpFirst NGO",             "category": "80G",       "state": "Tamil Nadu",  "active": True},
    {"ngo_reg_no": "80G-2023-101",  "name": "Asha Relief Center",        "category": "80G",       "state": "Gujarat",     "active": True},
    {"ngo_reg_no": "STATE-MH-001",  "name": "Maharashtra Disaster Corps", "category": "STATE_REG", "state": "Maharashtra", "active": True},
    {"ngo_reg_no": "STATE-KA-001",  "name": "Karnataka Aid Network",     "category": "STATE_REG", "state": "Karnataka",   "active": True},
    # Add more entries or replace this list with a DB / API call
]


async def seed_master_list(db, entries: list[dict] | None = None) -> int:
    """
    Upsert NGO entries into the `ngo_master_list` Firestore collection.

    Args:
        db:      Firestore AsyncClient (from firebase_init.init_firebase()).
        entries: List of NGO dicts. Defaults to NGO_MASTER_LIST above.

    Returns:
        Number of records written.
    """
    entries = entries or NGO_MASTER_LIST
    collection = db.collection("ngo_master_list")
    written = 0

    for entry in entries:
        doc_id = entry["ngo_reg_no"]
        await collection.document(doc_id).set(entry, merge=True)
        logger.info("Seeded: %s — %s", doc_id, entry["name"])
        written += 1

    logger.info("NGO master list seeding complete. %d records written.", written)
    return written


async def is_valid_ngo(ngo_reg_no: str, db) -> dict | None:
    """
    Check if an NGO Registration Number exists and is active.

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


# ── CLI seeder ───────────────────────────────────────────────────────────────

async def _seed_cli():
    from .firebase_init import init_firebase
    db = init_firebase()
    count = await seed_master_list(db)
    print(f"Done. {count} NGOs seeded into Firestore `ngo_master_list`.")


if __name__ == "__main__":
    # python -m backend_api.auth_gate.ngo_master_list
    asyncio.run(_seed_cli())
