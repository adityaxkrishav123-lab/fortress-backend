# 🛡️ IDENTITY SHIELD — Auth Gate

**Multi-Tenant RBAC Authentication for the Humanitarian Logistics Platform.**

All code lives in `backend_api/auth_gate/`. Your existing `main.py`, `dispatch/`, and `citizen_pipeline/` are **untouched**.

---

## 📁 File Structure

```
backend_api/
├── auth_gate/
│   ├── __init__.py          # Exports: auth_router, AuthGateMiddleware, init_firebase
│   ├── models.py            # Pydantic schemas (strict validation)
│   ├── pin_logic.py         # Argon2 PIN hashing — never stores raw PIN
│   ├── referral_engine.py   # NGO-XXXXXXXX code generation & validation
│   ├── dispatch_rights.py   # 5/20 rule enforcement
│   ├── middleware.py        # Firebase JWT verification (The Bouncer)
│   ├── dependencies.py      # require_role() RBAC dependency factory
│   ├── routes.py            # All /api/v1/auth/* endpoints
│   ├── firebase_init.py     # Firebase Admin SDK initialiser
│   ├── storage_utils.py     # Firebase Storage upload (JPG/PNG only)
│   ├── ngo_master_list.py   # NGO registry + seeder CLI
│   └── integration.py       # Copy-paste guide for wiring into main.py
├── tests/
│   ├── conftest.py
│   ├── test_pin_logic.py
│   ├── test_referral_engine.py
│   ├── test_dispatch_rights.py
│   ├── test_models.py
│   └── test_ngo_master_list.py
├── requirements_auth.txt
├── pyproject.toml
└── .env.example
```

---

## ⚡ Setup

### 1. Install dependencies

```bash
pip install -r requirements_auth.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Fill in FIREBASE_PROJECT_ID and GOOGLE_APPLICATION_CREDENTIALS
```

### 3. Wire into your existing `main.py` (3 additions only)

```python
from contextlib import asynccontextmanager
from backend_api.auth_gate import AuthGateMiddleware, auth_router, init_firebase

@asynccontextmanager
async def lifespan(app):
    app.state.db = init_firebase()   # ← line 1
    yield

app = FastAPI(lifespan=lifespan)
app.add_middleware(AuthGateMiddleware)   # ← line 2
app.include_router(auth_router)          # ← line 3

# your existing routers below — UNCHANGED
```

### 4. Seed the NGO Master List

```bash
python -m backend_api.auth_gate.ngo_master_list
```

---

## 🔌 Endpoints

All prefixed `/api/v1/auth/`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/register/preflight` | ❌ Public | Check email/phone uniqueness |
| `POST` | `/verify/ngo` | ❌ Public | Validate NGO Reg No against master list |
| `POST` | `/ngo/validate-referral` | ❌ Public | Validate referral code **before** Google Sign-In |
| `POST` | `/register/ngo-admin` | 🔑 JWT | Register NGO Admin + create NGO doc |
| `POST` | `/register/ngo-member` | 🔑 JWT | Register staff, link via referral code |
| `POST` | `/register/volunteer` | 🔑 JWT | Register volunteer (GENERAL or PRO) |
| `POST` | `/register/citizen` | 🔑 JWT | Register citizen |
| `POST` | `/verify/nationality` | 🔑 JWT | Upload nationality certificate (JPG/PNG) |
| `GET`  | `/ngo/referral-code` | 🔑 NGO_ADMIN | Get/rotate universal referral code |
| `GET`  | `/ngo/members` | 🔑 NGO_ADMIN | List all NGO members |
| `POST` | `/ngo/manage-member` | 🔑 NGO_ADMIN | add / remove / assign_rank |
| `POST` | `/ngo/toggle-tier` | 🔑 NGO_ADMIN | Upgrade Tier 1 → Tier 2 |
| `POST` | `/setup/pin` | 🔑 JWT | Set 6-digit PIN (Argon2 hash stored) |
| `POST` | `/validate/pin` | 🔑 JWT | Verify PIN for app entry |
| `GET`  | `/user/profile` | 🔑 JWT | Extended profile + NGO_ID + Rank |
| `POST` | `/volunteer/verify-pro` | 🔑 JWT | Upload skill certificate |

---

## 🔐 Security Architecture

### PIN (Security Anchor)
- **Stored**: Argon2 hash only — raw PIN **never** persisted
- **Client-side**: Flutter uses raw PIN as PBKDF2 salt for local PII decryption (backend does not participate)
- **App entry**: `/validate/pin` checks hash; on success returns `encrypted_vault_url`

### JWT Middleware
- Fetches Firebase RSA public keys from Google
- Verifies `RS256` signature, expiry, audience, and issuer
- Injects `uid`, `role`, `ngo_id` into `request.state`
- Public paths bypass verification (preflight, referral validate, docs/openapi)

### Dispatch Rights (5/20 Rule)
- Unlimited members can join any NGO
- Tier 1: max **5** members with dispatch rights
- Tier 2: max **20** members with dispatch rights
- Enforced atomically in `dispatch_rights.py` — returns `403` if cap is reached

### Tenant Isolation
- Every Firestore query for NGO data is scoped by `ngo_id` from the JWT
- No cross-NGO data leakage is possible via the API layer

---

## ✅ Running Tests

```bash
# From backend_api/ directory
pytest

# With coverage
pytest --cov=auth_gate --cov-report=term-missing
```

Test files cover: PIN hashing, referral engine, dispatch rights enforcement, Pydantic model validation, NGO master list.
All Firestore calls are mocked — **no Firebase project needed to run tests**.

---

## 🚧 Firestore Collections Used

| Collection | Purpose |
|---|---|
| `users` | Global user profile (all roles) |
| `ngos` | NGO organizational record |
| `ngo_members` | UID → NGO_ID mapping + rank + dispatch rights |
| `ngo_master_list` | Authoritative NGO registry (seeded via CLI) |
