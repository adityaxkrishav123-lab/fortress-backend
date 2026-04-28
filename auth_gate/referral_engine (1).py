"""
auth_gate/referral_engine.py
Universal Referral Code logic for NGO tenants.

Rules (per spec):
  - One code per NGO.
  - Format: NGO-XXXX  (alphanumeric, uppercase).
  - Admins can rotate/reset the code.
  - Validation happens BEFORE Google Sign-In in the member flow.
"""

import random
import string


_CHARSET = string.ascii_uppercase + string.digits  # A-Z, 0-9
_SUFFIX_LENGTH = 8                                 # NGO-XXXXXXXX


def generate_referral_code() -> str:
    """
    Generate a unique NGO-prefixed alphanumeric referral code.

    Returns:
        e.g. "NGO-A3KF92BZ"
    """
    suffix = "".join(random.choices(_CHARSET, k=_SUFFIX_LENGTH))
    return f"NGO-{suffix}"


async def get_or_create_referral_code(ngo_id: str, db) -> str:
    """
    Fetch the existing referral code for an NGO or create one if absent.

    Args:
        ngo_id: The NGO Registration No (used as Firestore document ID).
        db:     Firestore AsyncClient.

    Returns:
        The referral code string.
    """
    doc_ref = db.collection("ngos").document(ngo_id)
    doc = await doc_ref.get()

    if doc.exists:
        data = doc.to_dict()
        code = data.get("referral_code")
        if code:
            return code

    # No code yet — generate and persist
    new_code = generate_referral_code()
    await doc_ref.set({"referral_code": new_code}, merge=True)
    return new_code


async def rotate_referral_code(ngo_id: str, db) -> str:
    """
    Rotate (reset) the referral code for an NGO.
    Old code is immediately invalidated.

    Args:
        ngo_id: The NGO Registration No.
        db:     Firestore AsyncClient.

    Returns:
        The new referral code string.
    """
    new_code = generate_referral_code()
    doc_ref = db.collection("ngos").document(ngo_id)
    await doc_ref.set({"referral_code": new_code}, merge=True)
    return new_code


async def validate_referral_code(code: str, db) -> dict | None:
    """
    Validate a referral code against Firestore.

    Args:
        code: The code entered by the prospective member.
        db:   Firestore AsyncClient.

    Returns:
        NGO document dict if valid, None if invalid.
    """
    query = db.collection("ngos").where("referral_code", "==", code).limit(1)
    results = await query.get()

    for doc in results:
        return doc.to_dict()

    return None
