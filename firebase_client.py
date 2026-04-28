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

        # 1. Check for JSON string in Environment Variable (Best for Render/Cloud)
        json_creds = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")
        if json_creds:
            try:
                json_creds = json_creds.strip().strip("'").strip('"')
                cred_dict = json.loads(json_creds)
                
                if "private_key" in cred_dict:
                    pk = cred_dict["private_key"]
                    # Ultra-aggressive fix: replace literal \n and escaped \\n
                    pk = pk.replace("\\n", "\n")
                    # Remove any extra quotes or spaces inside the key
                    pk = pk.strip().replace('"', "").replace("'", "")
                    cred_dict["private_key"] = pk
                
                cred = credentials.Certificate(cred_dict)
                if not firebase_admin._apps:
                    firebase_admin.initialize_app(cred)
                self._db = firestore.client()
                self._is_mock = False
                logger.info("🔥 Firebase initialized from Env JSON. Database is LIVE.")
                return
            except Exception as e:
                logger.error(f"Failed to initialize Firebase from JSON Env: {e}")

        # 2. Fall back to local files (But fix them too!)
        config_path = None
        for candidate in ["serviceAccountKey.json", "service-account.json"]:
            if os.path.exists(candidate):
                config_path = candidate
                break
        
        if config_path and os.path.exists(config_path):
            try:
                # NEW: Read the file and fix it before passing to credentials
                with open(config_path, "r") as f:
                    data = json.load(f)
                    if "private_key" in data:
                        data["private_key"] = data["private_key"].replace("\\n", "\n")
                    cred = credentials.Certificate(data)
                
                if not firebase_admin._apps:
                    firebase_admin.initialize_app(cred)
                self._db = firestore.client()
                self._is_mock = False
                logger.info("🔥 Firebase initialized from fixed file. Database is LIVE.")
            except Exception as e:
                logger.error(f"Failed to initialize Firebase from fixed file: {e}")
                self._is_mock = True
        else:
            logger.warning("No Firebase credentials found. Running in MOCK MODE.")

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
