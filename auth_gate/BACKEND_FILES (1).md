# 🛡️ Identity Shield — Complete Backend File List

Full folder structure and file order for the `backend_api/` directory.

---

## 📂 Folder Structure

```
backend_api/
│
├── auth_gate/                   ← CORE MODULE (put all your logic here)
│   ├── __init__.py
│   ├── models.py
│   ├── pin_logic.py
│   ├── referral_engine.py
│   ├── dispatch_rights.py
│   ├── middleware.py
│   ├── dependencies.py
│   ├── routes.py
│   ├── firebase_init.py
│   ├── storage_utils.py
│   ├── ngo_master_list.py
│   └── integration.py
│
├── tests/                       ← UNIT TESTS (no Firebase needed)
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_pin_logic.py
│   ├── test_referral_engine.py
│   ├── test_dispatch_rights.py
│   ├── test_models.py
│   └── test_ngo_master_list.py
│
├── requirements_auth.txt        ← CONFIG
├── pyproject.toml               ← CONFIG
├── .env.example                 ← CONFIG
└── README.md                    ← DOCS
```

---

## 🔢 Files In Order — What They Belong To

### GROUP 1 — `auth_gate/` Core Module

| Order | File | Belongs To | What It Does |
|:---:|---|---|---|
| 1 | `auth_gate/__init__.py` | Package Init | Exports `auth_router`, `AuthGateMiddleware`, `init_firebase` to `main.py` |
| 2 | `auth_gate/models.py` | Data Layer | All Pydantic schemas. Phone regex, 6-digit PIN, NGO reg no, cross-field rank rule |
| 3 | `auth_gate/pin_logic.py` | Security | Argon2 PIN hashing. `hash_pin()` and `verify_pin()`. Raw PIN never stored |
| 4 | `auth_gate/referral_engine.py` | Tenant Logic | Generates `NGO-XXXXXXXX` codes. get / rotate / validate against Firestore |
| 5 | `auth_gate/dispatch_rights.py` | Tenant Logic | Enforces 5/20 rule. 403 at cap. `revoke` is idempotent, floor=0 |
| 6 | `auth_gate/middleware.py` | Security Gate | Firebase JWT bouncer. Verifies RS256. Injects `uid`, `role`, `ngo_id` into `request.state` |
| 7 | `auth_gate/dependencies.py` | Security Gate | `require_role()` factory — used as `Depends(require_role(Role.NGO_ADMIN))` |
| 8 | `auth_gate/routes.py` | API Layer | All 16 endpoints under `/api/v1/auth/`. Calls every other module |
| 9 | `auth_gate/firebase_init.py` | Infrastructure | Initialises Firebase Admin SDK. Returns async Firestore client stored on `app.state.db` |
| 10 | `auth_gate/storage_utils.py` | Infrastructure | Firebase Storage upload. Thread-pool safe. UID-scoped path. JPG/PNG only |
| 11 | `auth_gate/ngo_master_list.py` | Data Layer | NGO registry. `is_valid_ngo()` checks active status. CLI seeder for Firestore |
| 12 | `auth_gate/integration.py` | Docs/Guide | Exact 3 lines to add to your existing `main.py` |

---

### GROUP 2 — `tests/` Unit Tests

| Order | File | Tests | Firebase? |
|:---:|---|---|:---:|
| 1 | `tests/__init__.py` | Package marker | ❌ |
| 2 | `tests/conftest.py` | Import path setup | ❌ |
| 3 | `tests/test_pin_logic.py` | Hash uniqueness, correct/wrong/partial PIN | ❌ |
| 4 | `tests/test_referral_engine.py` | Code format, uniqueness, Firestore mocked | ❌ |
| 5 | `tests/test_dispatch_rights.py` | Tier 1 cap (5), Tier 2 cap (20), 403, 404, floor=0 | ❌ |
| 6 | `tests/test_models.py` | Phone/PIN/NGO regex, cross-field rank rule | ❌ |
| 7 | `tests/test_ngo_master_list.py` | Active/inactive/missing NGO, seeder write count | ❌ |

---

### GROUP 3 — `backend_api/` Config & Docs

| Order | File | Purpose |
|:---:|---|---|
| 1 | `requirements_auth.txt` | `pip install -r requirements_auth.txt` |
| 2 | `pyproject.toml` | Pytest config — `asyncio_mode = auto` |
| 3 | `.env.example` | Copy → `.env`, fill Firebase project ID + credentials |
| 4 | `README.md` | Setup guide, endpoint table, security architecture |

---

## ⚡ Load Order (dependency chain)

```
firebase_init.py          ← no internal deps
models.py                 ← no internal deps
pin_logic.py              ← no internal deps
referral_engine.py        ← no internal deps
ngo_master_list.py        ← no internal deps
storage_utils.py          ← no internal deps
dispatch_rights.py        ← models.py
dependencies.py           ← models.py
middleware.py             ← (uses Firebase public keys via HTTP)
    ↓
routes.py                 ← ALL of the above
    ↓
__init__.py               ← routes.py + middleware.py + firebase_init.py
    ↓
main.py (YOURS)           ← __init__.py only — 3 lines added, nothing else changed
```

---

## 🚀 Quickstart (5 steps)

```bash
# 1. Install
pip install -r backend_api/requirements_auth.txt

# 2. Configure
cp backend_api/.env.example backend_api/.env
# Fill in FIREBASE_PROJECT_ID and GOOGLE_APPLICATION_CREDENTIALS

# 3. Seed NGO master list into Firestore
python -m backend_api.auth_gate.ngo_master_list

# 4. Run tests (no Firebase required — all mocked)
cd backend_api && pytest

# 5. Start server
uvicorn main:app --reload
```
