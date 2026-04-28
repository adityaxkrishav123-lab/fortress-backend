"""
auth_gate/firebase_init.py
Initializes the Firebase Admin SDK and returns an async Firestore client.

Call `init_firebase()` once at app startup (lifespan handler).
The resulting `db` object is stored on `app.state.db` so all route
handlers can reach it via `request.app.state.db`.

Environment variables required:
    FIREBASE_PROJECT_ID       — GCP project ID
    GOOGLE_APPLICATION_CREDENTIALS — Path to service-account JSON,
                                     OR set FIREBASE_SERVICE_ACCOUNT_JSON
                                     to the raw JSON string (for secrets managers).
"""

import json
import os
import logging

import firebase_admin
from firebase_admin import credentials, firestore_async

logger = logging.getLogger("auth_gate.firebase")


def init_firebase() -> firestore_async.AsyncClient:
    """
    Initialize the Firebase Admin SDK with aggressive private key repair.
    """
    if not firebase_admin._apps:
        # Priority 1: FIREBASE_SERVICE_ACCOUNT_JSON (Secrets Manager / Render Env)
        sa_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
        if sa_json:
            try:
                sa_json = sa_json.strip().strip("'").strip('"')
                sa_dict = json.loads(sa_json)
                if "private_key" in sa_dict:
                    sa_dict["private_key"] = sa_dict["private_key"].replace("\\n", "\n").strip().replace('"', "").replace("'", "")
                
                cred = credentials.Certificate(sa_dict)
                firebase_admin.initialize_app(cred)
                logger.info("Firebase: loaded credentials from fixed FIREBASE_SERVICE_ACCOUNT_JSON")
            except Exception as e:
                logger.error("Failed to load Firebase from Env: %s", e)
                raise

        # Priority 2: local file
        else:
            sa_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or "./service-account.json"
            if sa_path and os.path.exists(sa_path):
                try:
                    with open(sa_path, "r") as f:
                        data = json.load(f)
                        if "private_key" in data:
                            data["private_key"] = data["private_key"].replace("\\n", "\n").strip()
                        cred = credentials.Certificate(data)
                        firebase_admin.initialize_app(cred)
                        logger.info("Firebase: loaded and FIXED credentials from file: %s", sa_path)
                except Exception as e:
                    logger.error("Failed to load Firebase from file %s: %s", sa_path, e)
                    raise
            else:
                raise EnvironmentError("No Firebase credentials found in Env or File.")

    db: firestore_async.AsyncClient = firestore_async.client()
    logger.info("Firestore async client ready")
    return db
