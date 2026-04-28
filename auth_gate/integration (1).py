"""
auth_gate/integration.py
──────────────────────────────────────────────────────────────────────────────
HOW TO WIRE THE AUTH GATE INTO YOUR EXISTING main.py
──────────────────────────────────────────────────────────────────────────────

Add the following THREE blocks to your existing main.py.
DO NOT modify any logistics routes, dispatch/, or citizen_pipeline/ code.

──────────────────────────────────────────────────────────────────────────────
BLOCK 1 — Imports (add near the top of main.py)
──────────────────────────────────────────────────────────────────────────────

    from contextlib import asynccontextmanager
    from backend_api.auth_gate import AuthGateMiddleware, auth_router
    from backend_api.auth_gate.firebase_init import init_firebase

──────────────────────────────────────────────────────────────────────────────
BLOCK 2 — Lifespan (replace or extend your existing lifespan if you have one)
──────────────────────────────────────────────────────────────────────────────

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Initialise Firebase + Firestore once at startup
        app.state.db = init_firebase()
        yield
        # (teardown if needed)

    app = FastAPI(lifespan=lifespan)

──────────────────────────────────────────────────────────────────────────────
BLOCK 3 — Middleware + Router (add BEFORE your existing route includes)
──────────────────────────────────────────────────────────────────────────────

    # The Bouncer — sits in front of all routes
    app.add_middleware(AuthGateMiddleware)

    # Mount the Identity Shield endpoints at /api/v1/auth/*
    app.include_router(auth_router)

──────────────────────────────────────────────────────────────────────────────
COMPLETE EXAMPLE (minimal main.py)
──────────────────────────────────────────────────────────────────────────────
"""

# ── The snippet below is a copy-paste-ready example ──────────────────────────
#
# from contextlib import asynccontextmanager
# from fastapi import FastAPI
# from backend_api.auth_gate import AuthGateMiddleware, auth_router
# from backend_api.auth_gate.firebase_init import init_firebase
#
# # ── your existing imports ─────────────────────────────────────────────────
# # from dispatch import router as dispatch_router
# # from citizen_pipeline import router as citizen_router
# # ... etc
#
# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     app.state.db = init_firebase()          # <── one line
#     yield
#
# app = FastAPI(
#     title="Humanitarian Logistics Platform",
#     lifespan=lifespan,
# )
#
# # ── Auth Gate FIRST ───────────────────────────────────────────────────────
# app.add_middleware(AuthGateMiddleware)
# app.include_router(auth_router)
#
# # ── Your existing routers (UNCHANGED) ────────────────────────────────────
# # app.include_router(dispatch_router)
# # app.include_router(citizen_router)
# # ... etc
