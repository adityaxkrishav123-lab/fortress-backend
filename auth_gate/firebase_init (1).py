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
    Initialize the Firebase Admin SDK (idempotent — safe to call multiple times).

    Priority order for credentials:
      1. GOOGLE_APPLICATION_CREDENTIALS env var (path to JSON file) — local dev
      2. FIREBASE_SERVICE_ACCOUNT_JSON env var (raw JSON string) — CI / secrets manager

    Returns:
        An async Firestore client connected to your project.
    """
    if not firebase_admin._apps:
        # Option 1: path to service-account file
        sa_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if sa_path and os.path.exists(sa_path):
            cred = credentials.Certificate(sa_path)
            logger.info("Firebase: loaded credentials from file: %s", sa_path)

        # Option 2: raw JSON in env var (for containerised deployments)
        else:
            sa_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
            if not sa_json:
                raise EnvironmentError(
                    "Firebase credentials not found. "
                    "Set GOOGLE_APPLICATION_CREDENTIALS or FIREBASE_SERVICE_ACCOUNT_JSON."
                )
            sa_dict = json.loads(sa_json)
            cred = credentials.Certificate(sa_dict)
            logger.info("Firebase: loaded credentials from FIREBASE_SERVICE_ACCOUNT_JSON env var")

        firebase_admin.initialize_app(cred)

    db: firestore_async.AsyncClient = firestore_async.client()
    logger.info("Firestore async client ready")
    return db
