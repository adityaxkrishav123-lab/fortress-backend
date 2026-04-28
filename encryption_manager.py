"""
ENCRYPTION MANAGER — Device-Anchored PII Protection
=====================================================
Architecture:
- Key is derived from user's password using PBKDF2-HMAC-SHA256
  (never stored in plaintext anywhere — not on device, not on server)
- Encryption: AES-256-GCM (authenticated encryption — tamper-proof)
- Backup: The encrypted key blob is stored on the SERVER
  (encrypted with user's password hash, so only they can recover it)
- If phone lost: user re-enters password → key is re-derived → data recoverable

Flow:
  encrypt_pii_map(token_map, password) → {encrypted_blob, salt, nonce}
  decrypt_pii_map(encrypted_blob, salt, nonce, password) → token_map

Dependencies:
  pip install cryptography
"""

import os
import json
import base64
import logging
from typing import Optional

logger = logging.getLogger("EncryptionManager")

try:
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.backends import default_backend
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    logger.error(
        "CRITICAL: 'cryptography' package not installed. "
        "Run: pip install cryptography"
    )


class EncryptionManager:
    """
    Handles all PII encryption and decryption.

    Key Design Decisions:
    - PBKDF2 with 600,000 iterations (NIST 2024 recommended minimum)
    - AES-256-GCM: authenticated encryption (detects tampering)
    - Salt and nonce are random per operation (never reused)
    - Raw key never persisted — always re-derived from password
    """

    PBKDF2_ITERATIONS = 600_000  # NIST 2024 recommended minimum
    KEY_LENGTH = 32               # 256-bit key for AES-256

    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """
        Derives a 256-bit encryption key from user's password + salt.
        The salt makes rainbow table attacks impossible.
        """
        if not CRYPTO_AVAILABLE:
            raise RuntimeError("cryptography package required for encryption.")

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=self.KEY_LENGTH,
            salt=salt,
            iterations=self.PBKDF2_ITERATIONS,
            backend=default_backend()
        )
        return kdf.derive(password.encode('utf-8'))

    def encrypt_pii_map(self, token_map: dict, password: str) -> dict:
        """
        Encrypts the full PII token map using AES-256-GCM.

        Args:
            token_map: {token: original_value} from PIIShield
            password: user's account password (never stored)

        Returns:
            {
                "encrypted_blob": base64 string (safe to store on server),
                "salt": base64 string (public — needed for key derivation),
                "nonce": base64 string (public — needed for decryption)
            }
        """
        if not CRYPTO_AVAILABLE:
            raise RuntimeError("cryptography package required for encryption.")

        if not token_map:
            return {"encrypted_blob": None, "salt": None, "nonce": None}

        # Generate fresh random salt and nonce for every encryption operation
        salt = os.urandom(16)   # 128-bit salt
        nonce = os.urandom(12)  # 96-bit nonce (GCM standard)

        key = self._derive_key(password, salt)
        aesgcm = AESGCM(key)

        # Serialize the token map to JSON bytes
        plaintext = json.dumps(token_map, ensure_ascii=False).encode('utf-8')

        # Encrypt: AES-256-GCM (authenticated — detects tampering)
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)

        logger.info(f"EncryptionManager: Encrypted {len(token_map)} PII tokens.")

        return {
            "encrypted_blob": base64.b64encode(ciphertext).decode('ascii'),
            "salt": base64.b64encode(salt).decode('ascii'),
            "nonce": base64.b64encode(nonce).decode('ascii')
        }

    def decrypt_pii_map(
        self,
        encrypted_blob: str,
        salt: str,
        nonce: str,
        password: str
    ) -> Optional[dict]:
        """
        Decrypts the PII token map.
        Only works if the password matches the one used for encryption.

        Returns:
            token_map dict if successful, None if password is wrong or data tampered.
        """
        if not CRYPTO_AVAILABLE:
            raise RuntimeError("cryptography package required for decryption.")

        if not encrypted_blob:
            return {}

        try:
            ciphertext = base64.b64decode(encrypted_blob)
            salt_bytes = base64.b64decode(salt)
            nonce_bytes = base64.b64decode(nonce)

            key = self._derive_key(password, salt_bytes)
            aesgcm = AESGCM(key)

            plaintext = aesgcm.decrypt(nonce_bytes, ciphertext, None)
            token_map = json.loads(plaintext.decode('utf-8'))

            logger.info(f"EncryptionManager: Decrypted {len(token_map)} PII tokens.")
            return token_map

        except Exception as e:
            # Wrong password or tampered data — both look the same to the attacker
            logger.error(f"EncryptionManager: Decryption failed — {e}")
            return None

    def build_recovery_package(self, encrypted_result: dict, user_id: str) -> dict:
        """
        Builds the server-side recovery blob.
        Stored on our server — allows key recovery if phone is lost.
        The server can NEVER decrypt this — only the user with their password can.

        Returns:
            {
                "user_id": ...,
                "recovery_blob": encrypted salt + nonce package,
                "note": human-readable note about what this is
            }
        """
        return {
            "user_id": user_id,
            "salt": encrypted_result["salt"],      # public — safe to store
            "nonce": encrypted_result["nonce"],    # public — safe to store
            "note": (
                "This is the cryptographic metadata needed to re-derive your "
                "encryption key. It cannot decrypt your data without your password."
            )
        }
