"""
auth_gate/storage_utils.py
──────────────────────────────────────────────────────────────────────────────
Firebase Storage upload helper.

Replaces the stub in routes.py.
Uses firebase_admin.storage (synchronous) wrapped in a thread pool executor
so it doesn't block the async event loop.
"""

import asyncio
import os
import uuid
from concurrent.futures import ThreadPoolExecutor

import firebase_admin.storage
from fastapi import UploadFile

_EXECUTOR = ThreadPoolExecutor(max_workers=4)

# Bucket name from env — e.g. "your-project.appspot.com"
_BUCKET_NAME: str = os.getenv("FIREBASE_STORAGE_BUCKET", "")

# Allowed MIME types for document uploads per spec (JPG/PNG only)
ALLOWED_MIME = {"image/jpeg", "image/png"}


def _sync_upload(file_bytes: bytes, content_type: str, storage_path: str) -> str:
    """
    Blocking upload — runs in a thread pool so it doesn't block asyncio.

    Returns the public Storage URI: gs://bucket/path
    """
    bucket = firebase_admin.storage.bucket(_BUCKET_NAME or None)
    blob = bucket.blob(storage_path)
    blob.upload_from_string(file_bytes, content_type=content_type)
    return f"gs://{bucket.name}/{storage_path}"


async def upload_document(file: UploadFile, folder: str, uid: str) -> str:
    """
    Async-safe upload of a JPG/PNG document to Firebase Storage.

    Args:
        file:   FastAPI UploadFile (already validated as JPG/PNG by caller).
        folder: Storage sub-folder, e.g. "nationality" or "skill_certs".
        uid:    Firebase UID of the user — used to scope the path.

    Returns:
        Firebase Storage URI string: "gs://bucket/folder/uid/filename"

    The path pattern prevents users from overwriting each other's files
    because each uid is isolated in its own prefix.
    """
    ext = "jpg" if file.content_type == "image/jpeg" else "png"
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    storage_path = f"{folder}/{uid}/{unique_name}"

    file_bytes = await file.read()

    # Run blocking SDK call off the event loop
    loop = asyncio.get_event_loop()
    gs_uri = await loop.run_in_executor(
        _EXECUTOR,
        _sync_upload,
        file_bytes,
        file.content_type,
        storage_path,
    )
    return gs_uri
