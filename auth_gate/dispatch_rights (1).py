"""
auth_gate/dispatch_rights.py
Dispatch Rights enforcement — The 5/20 Rule.

Rules (per spec):
  - Unlimited members can join an NGO. NO CAP on total membership.
  - Only a capped number can hold "Dispatch Rights":
      Tier 1 → max 5 members with dispatch rights.
      Tier 2 → max 20 members with dispatch rights.
  - When granting rights: increment `dispatch_rights_count` on the NGO doc.
  - When revoking rights: decrement `dispatch_rights_count`.
  - If cap is reached → 403 FORBIDDEN.
"""

from fastapi import HTTPException, status
from firebase_admin import firestore_async

DISPATCH_LIMIT = {1: 5, 2: 20}

async def grant_dispatch_rights(ngo_id: str, member_uid: str, db) -> None:
    """
    Grant dispatch rights to a member securely using a transaction.
    """
    ngo_ref = db.collection("ngos").document(ngo_id)
    member_ref = db.collection("ngo_members").document(member_uid)

    @firestore_async.transactional
    async def update_in_transaction(transaction, ngo_ref, member_ref):
        ngo_doc = await ngo_ref.get(transaction=transaction)
        if not ngo_doc.exists:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NGO not found")
        
        ngo_data = ngo_doc.to_dict()
        tier: int = ngo_data.get("tier", 1)
        current_count: int = ngo_data.get("dispatch_rights_count", 0)
        limit: int = DISPATCH_LIMIT.get(tier, 5)

        if current_count >= limit:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Dispatch rights cap reached. "
                    f"Tier {tier} NGOs can have at most {limit} members with dispatch rights."
                ),
            )

        transaction.update(ngo_ref, {"dispatch_rights_count": current_count + 1})
        transaction.set(member_ref, {"has_dispatch_rights": True}, merge=True)

    await update_in_transaction(db.transaction(), ngo_ref, member_ref)


async def revoke_dispatch_rights(ngo_id: str, member_uid: str, db) -> None:
    """
    Revoke dispatch rights from a member securely.
    """
    ngo_ref = db.collection("ngos").document(ngo_id)
    member_ref = db.collection("ngo_members").document(member_uid)

    @firestore_async.transactional
    async def remove_in_transaction(transaction, ngo_ref, member_ref):
        member_doc = await member_ref.get(transaction=transaction)
        if not member_doc.exists:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
            
        member_data = member_doc.to_dict()
        had_rights: bool = member_data.get("has_dispatch_rights", False)
        
        transaction.set(member_ref, {"has_dispatch_rights": False}, merge=True)
        
        if had_rights:
            ngo_doc = await ngo_ref.get(transaction=transaction)
            if ngo_doc.exists:
                current_count: int = ngo_doc.to_dict().get("dispatch_rights_count", 0)
                new_count = max(0, current_count - 1)
                transaction.update(ngo_ref, {"dispatch_rights_count": new_count})
                
    await remove_in_transaction(db.transaction(), ngo_ref, member_ref)
