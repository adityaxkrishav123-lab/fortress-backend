"""
main.py — Humanitarian Logistics Fortress v2.0
================================================
The Application Entry Point (Firestore Edition).

Architecture:
  - Single source of truth: Firestore (via app.state.db)
  - All domain logic lives in registered routers
  - MonitorAgent runs in the background watching all active cards

Registered Routers:
  /api/v1/auth/*     — Identity, PIN, Session persistence  (auth_gate)
  /api/v1/mailbox/*  — Action Cards, Inbox, Respond        (mailbox)
  /api/v1/ngo/*      — NGO Report Logs                     (ngo)
  /api/v1/profile/*  — Profile Updates                     (profile)

Utility Endpoints (inline below):
  POST /api/v1/ingest/disaster_report — OmniParser ingestion
  GET  /api/v1/notifications/{uid}    — Notification center
  POST /api/v1/notifications/{id}/read
  POST /api/v1/export/csv             — CSV data export
  POST /api/v1/pii/decrypt            — PII vault decryption
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

import asyncio
import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# ── Firebase ──────────────────────────────────────────────────────────────────
from auth_gate.firebase_init import init_firebase

# ── Domain Routers ────────────────────────────────────────────────────────────
from auth_gate.routes import router as auth_router
from mailbox.action_card_engine import router as mailbox_router
from mailbox.instant_help import router as instant_help_router
from mailbox.instant_help_accept import router as instant_help_accept_router
from ngo.ngo_log import router as ngo_log_router
from profile.profile_update import router as profile_router

# ── Background Agents ─────────────────────────────────────────────────────────
from dispatch.monitor_agent import MonitorAgent
from region_config import get_all_monitored_regions

# ── Utility Modules ───────────────────────────────────────────────────────────
from notification_manager import NotificationManager
from dispatch.key_manager import KeyManager
from omni_parser import OmniFormatParser

# ── Logging Setup ─────────────────────────────────────────────────────────────
try:
    from pythonjsonlogger import jsonlogger
    _handler = logging.StreamHandler()
    _handler.setFormatter(jsonlogger.JsonFormatter("%(asctime)s %(name)s %(levelname)s %(message)s"))
    logging.basicConfig(level=logging.WARNING, handlers=[_handler])
except ImportError:
    logging.basicConfig(level=logging.WARNING, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

logger = logging.getLogger("Main")

# ── AI Parser Bootstrap ───────────────────────────────────────────────────────
try:
    key_manager = KeyManager()
    parser = OmniFormatParser(key_manager=key_manager)
except Exception as _e:
    logger.error(f"FATAL: Failed to initialize AI Parser — {_e}")
    parser = None


# ─────────────────────────────────────────────────────────────────────────────
# LIFESPAN — App Startup & Shutdown
# ─────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup:
      1. Initialize Firestore → store as app.state.db (single source of truth).
      2. Launch MonitorAgent background task (watches all active action cards).

    Shutdown:
      1. Cancel MonitorAgent cleanly.
    """
    # ── CRITICAL: Initialize Firestore ────────────────────────────────────────
    # All routers access the db via: request.app.state.db
    logger.warning("FORTRESS STARTING — Connecting to Firestore...")
    try:
        app.state.db = init_firebase()
        logger.warning("FORTRESS: Firestore connected. Database is LIVE. ✅")
    except Exception as e:
        logger.error(f"FORTRESS: Firestore connection FAILED — {e}")
        raise  # Cannot start without a database

    # ── Start MonitorAgent ────────────────────────────────────────────────────
    monitored_regions = get_all_monitored_regions()
    monitor_agent     = MonitorAgent(monitored_regions=monitored_regions)
    monitor_task      = asyncio.create_task(monitor_agent.run_forever(app.state.db))
    logger.warning(f"FORTRESS WATCHDOG: MonitorAgent started across {len(monitored_regions)} regions.")

    yield  # ── App is running ──────────────────────────────────────────────────

    monitor_task.cancel()
    try:
        await asyncio.gather(monitor_task, return_exceptions=True)
    except asyncio.CancelledError:
        pass
    logger.warning("FORTRESS: MonitorAgent stopped cleanly.")


# ─────────────────────────────────────────────────────────────────────────────
# FASTAPI APP SETUP
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Humanitarian Logistics Fortress",
    description="Project Powerhouse — Emergency Logistics Engine v2.0",
    version="2.0.0",
    lifespan=lifespan,
)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],    # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────────────────
# REGISTER ROUTERS
# ─────────────────────────────────────────────────────────────────────────────

app.include_router(auth_router)                # /api/v1/auth/*
app.include_router(mailbox_router)             # /api/v1/mailbox/*
app.include_router(instant_help_router)        # /api/v1/instant-help/*
app.include_router(instant_help_accept_router) # /api/v1/instant-help/accept/*
app.include_router(ngo_log_router)             # /api/v1/ngo/*
app.include_router(profile_router)             # /api/v1/profile/*


# ─────────────────────────────────────────────────────────────────────────────
# UTILITY ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/api/v1/ingest/disaster_report")
@limiter.limit("10/minute")
async def ingest_disaster_report(request: Request, file: UploadFile = File(...)):
    """
    OmniParser Ingestion.
    Accepts any file format (image, PDF, audio, text) and extracts
    structured disaster needs for human review before dispatch.
    """
    if parser is None:
        raise HTTPException(status_code=503, detail="AI Parser unavailable.")

    file_bytes = await file.read()
    mime_type  = file.content_type or "application/octet-stream"
    result     = await parser.route_and_parse(file.filename or "upload", file_bytes, mime_type)

    if result.get("status") != "success":
        raise HTTPException(status_code=400, detail=result.get("message"))

    return {
        "status":      "success",
        "audit_id":    f"AUDIT-{uuid.uuid4().hex[:6].upper()}",
        "message":     "Extracted needs. AWAITING HUMAN REVIEW.",
        "data":        result["data"],
        "unprocessed": result.get("unprocessed_items", []),
    }


@app.get("/api/v1/notifications/{user_id}")
@limiter.limit("30/minute")
async def get_my_notifications(request: Request, user_id: str):
    """Return all unread notifications for a user."""
    db = request.app.state.db
    unread = await NotificationManager.get_unread(db, user_id)
    return {"status": "success", "count": len(unread), "notifications": unread}


@app.post("/api/v1/notifications/{notification_id}/read")
@limiter.limit("60/minute")
async def mark_notification_seen(request: Request, notification_id: str):
    """Mark a single notification as read."""
    db = request.app.state.db
    await NotificationManager.mark_read(db, notification_id)
    return {"status": "success", "message": "Notification marked as read."}


@app.post("/api/v1/export/csv")
@limiter.limit("10/minute")
async def export_data_csv(request: Request, data: list, parse_id: str = "report"):
    """
    Export operational data for NGOs.
    PII remains masked as [ENCRYPTED] in the CSV until decrypted locally.
    """
    try:
        from output_formatter import OutputFormatter
        from fastapi.responses import Response
        formatter  = OutputFormatter()
        csv_bytes  = formatter.to_csv(data, {}, parse_id)
        return Response(
            content     = csv_bytes,
            media_type  = "text/csv",
            headers     = {"Content-Disposition": f"attachment; filename={parse_id}.csv"},
        )
    except ImportError:
        raise HTTPException(status_code=501, detail="Export modules not installed. Run: pip install pandas")


@app.post("/api/v1/pii/decrypt")
@limiter.limit("5/minute")
async def decrypt_pii_vault(request: Request, vault: dict, password: str):
    """
    Device-side decryption simulator for PII.
    Takes the Vault package and password to reveal real contact details.
    """
    try:
        from encryption_manager import EncryptionManager
        crypto    = EncryptionManager()
        decrypted = crypto.decrypt_pii_map(
            vault.get("encrypted_blob"),
            vault.get("salt"),
            vault.get("nonce"),
            password,
        )
        if not decrypted:
            raise HTTPException(status_code=401, detail="Invalid Vault Password.")
        return {"status": "success", "tokens": decrypted}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/utils/resolve-region")
@limiter.limit("30/minute")
async def resolve_gps_to_region(request: Request, lat: float, lon: float):
    """
    Resolve GPS coordinates to a named Region for the Citizen Profile page.
    This enables dynamic region detection even if signup region is fixed.
    """
    try:
        from region_config import get_region_from_gps
        region = get_region_from_gps(lat, lon)
        if region:
            return {"status": "success", "region": region}
        else:
            return {"status": "error", "message": "Location outside coverage area."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# ARCHIVED — Phase 1 Prototype Endpoints
# ─────────────────────────────────────────────────────────────────────────────
# The following endpoints were part of the original in-memory / SQLite prototype.
# They have been RETIRED and replaced by the Firestore-based mailbox system:
#
#   OLD: POST /api/v1/citizen/request    → NEW: POST /api/v1/mailbox/citizen/create-card
#   OLD: POST /api/v1/citizen/accept     → NEW: POST /api/v1/mailbox/respond
#   OLD: POST /api/v1/citizen/fire_ngo   → NEW: POST /api/v1/mailbox/cancel
#   OLD: POST /api/v1/citizen/confirm    → NEW: POST /api/v1/mailbox/confirm
#   OLD: POST /api/v1/citizen/reopen     → NEW: MonitorAgent handles this automatically
#   OLD: POST /api/v1/dispatch/request   → NEW: CitizenAgent (called from action_card_engine)
#
# These have not been deleted in case the old flow needs reference.
# They are simply not registered. Remove this comment block once
# the new mailbox system is fully smoke-tested.
# ─────────────────────────────────────────────────────────────────────────────
