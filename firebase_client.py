import os
import json
import logging
from typing import Optional

try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False

logger = logging.getLogger(__name__)

class FirebaseClient:
    """
    Singleton client for interacting with Firebase/Firestore.
    Currently runs in MOCK MODE unless FIREBASE_CONFIG_PATH is set.
    """
    _instance = None
    _db = None
    _is_mock = True

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FirebaseClient, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        if not FIREBASE_AVAILABLE:
            logger.warning("Firebase Admin SDK not installed. Running in MOCK MODE.")
            return

        # Look for local files first (Hackathon Mode), then fall back to env vars
        config_path = None
        for candidate in ["serviceAccountKey.json", "service-account.json"]:
            if os.path.exists(candidate):
                config_path = candidate
                break
        
        if not config_path:
            config_path = os.environ.get("FIREBASE_CONFIG_PATH") or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        
        if config_path and os.path.exists(config_path):
            try:
                cred = credentials.Certificate(config_path)
                # Check if already initialized to prevent errors during hot-reloads
                if not firebase_admin._apps:
                    firebase_admin.initialize_app(cred)
                self._db = firestore.client()
                self._is_mock = False
                logger.info("🔥 Firebase Admin SDK Initialized Successfully. Connected to Global Ledger.")
            except Exception as e:
                logger.error(f"Failed to initialize Firebase: {e}")
                self._is_mock = True
        else:
            logger.warning("No FIREBASE_CONFIG_PATH found. Running Firebase Client in MOCK MODE.")

    @property
    def db(self):
        """Returns the Firestore client instance, or None if in mock mode."""
        return self._db

    @property
    def is_mock(self) -> bool:
        return self._is_mock

    # --- MOCK / BRIDGE METHODS (To be implemented in Phase 2) ---

    async def verify_token(self, id_token: str) -> Optional[dict]:
        """Verifies a Firebase Auth token."""
        if self._is_mock:
            # Mock verification
            return {"uid": "mock-citizen-123", "role": "citizen"}
        
        try:
            from firebase_admin import auth
            decoded_token = auth.verify_id_token(id_token)
            return decoded_token
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            return None

# Global instance for easy import
firebase_client = FirebaseClient()
