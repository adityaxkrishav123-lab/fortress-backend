"""
auth_gate/pin_logic.py
6-Digit UPI-Style PIN hashing using Argon2.

Security contract (per spec):
  - NEVER store the raw PIN.
  - Store argon2 hash in Firestore `users.pin_hash`.
  - The raw PIN is used by the *frontend* as a PBKDF2 salt for local PII decryption.
    The backend never participates in the PBKDF2 derivation — it only validates
    the PIN via argon2 hash comparison.
"""

from passlib.hash import argon2


def hash_pin(raw_pin: str) -> str:
    """
    Hash a 6-digit PIN using Argon2.
    Returns an opaque hash string suitable for storing in Firestore.

    Args:
        raw_pin: The 6-digit numeric string entered by the user.

    Returns:
        Argon2 hash string.
    """
    return argon2.hash(raw_pin)


def verify_pin(raw_pin: str, stored_hash: str) -> bool:
    """
    Verify a 6-digit PIN against its stored Argon2 hash.

    Args:
        raw_pin:      PIN entered by the user at app entry.
        stored_hash:  The Argon2 hash retrieved from Firestore `users.pin_hash`.

    Returns:
        True if the PIN matches the hash, False otherwise.
    """
    return argon2.verify(raw_pin, stored_hash)
