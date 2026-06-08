# FastAPI Modular Monolith Template

A pragmatic, production-leaning **FastAPI starter** for multi-tenant SaaS apps. Feature-sliced
**modular monolith** (not hexagonal/DDD ceremony): each feature is `router → service → schema →
models`, with SQLAlchemy used directly. 100% async on `asyncpg`.

Ships with auth (JWT + refresh + lockout + TOTP MFA), multi-tenancy via Postgres RLS, Celery
(worker + beat), a swappable email provider, and a set of shared utilities. Channels, an AI-agent
subsystem, and business modules are added **per app** — the patterns are provided here.

---

## Features

- **Auth** — register / login / refresh / logout / me, account lockout, refresh-token rotation
- **MFA** — full TOTP flow (setup / enable / disable + login challenge)
- **Multi-tenancy** — shared-schema + Postgres Row-Level Security, `TenantMixin`
- **Background jobs** — Celery worker + beat, with a sync-task → async-session bridge
- **Email** — swappable `console | smtp` provider, Jinja2 templates, sent via Celery
- **Shared utils** — response envelope, pagination, logging, redis cache, rate limiter
- **Migrations** — async Alembic that **auto-discovers** every module's models
- **Docker** — api / worker / beat / postgres / redis via Compose

## Tech stack

Python 3.12 · FastAPI · SQLAlchemy 2 (async) · asyncpg · Alembic · Celery + Redis ·
python-jose · bcrypt · pyotp · Jinja2 · `uv` · `ruff`

---

## Project structure

```
app/
├── main.py                 # app factory: CORS, exception handlers, routers, logging
├── core/
│   ├── config.py           # pydantic-settings (env)
│   ├── database.py         # async engine, sessionmaker, Base, get_db
│   ├── dependencies.py     # DbSession, RedisSession, CurrentUser  (only place Depends() lives)
│   ├── tenancy.py          # RLS context, TenantMixin, rls_statements()
│   ├── security.py         # JWT + bcrypt (off the event loop) + token hashing
│   ├── celery_app.py       # Celery app, autodiscover, beat schedule
│   ├── worker.py           # run_async() + worker-scoped async session
│   ├── lifespan.py         # startup/shutdown
│   ├── exceptions.py       # AppError + handlers ({errors, message})
│   └── registry.py         # auto-discovers modules/*/models for Alembic
├── modules/
│   └── auth/               # router, service, schema, models, mfa, tasks
├── providers/
│   └── email/              # base, console, smtp, factory, render, templates/, tasks
├── shared/                 # response, pagination, logging, cache, rate_limiter
└── alembic/                # async env.py + versions/
```

A **module** owns one feature: `router.py` (thin) → `service.py` (logic) → `schema.py` (Pydantic) →
`models.py` (SQLAlchemy) and `tasks.py` (Celery) where needed.

---

## Getting started

### 1. Requirements
- Python 3.12+, [`uv`](https://docs.astral.sh/uv/), Postgres, Redis (or just Docker).

### 2. Environment
```bash
cp .example.env .env      # then edit values
```

### 3. Run with Docker (everything)
```bash
docker compose up --build
# api → http://localhost:8000   (runs migrations on start)
```

### 4. Run locally
```bash
uv sync
make alembic-upgrade        # apply migrations
make start                  # uvicorn --reload
make worker                 # celery worker   (separate shell)
make beat                   # celery beat     (separate shell)
```

Health check: `GET /api/health` · Interactive docs: `http://localhost:8000/docs`

---

## Configuration

All settings are env vars (`app/core/config.py`). Key ones:

| Var | Default | Notes |
|---|---|---|
| `SECRET_KEY` | — | JWT signing key (required) |
| `FRONTEND_URL` | `http://localhost:3000` | CORS origin |
| `DATABASE_*` | — | name / user / password / host / port |
| `REDIS_URL` | `redis://localhost:6379/0` | app cache + rate limiter |
| `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` | redis db 1 / 2 | |
| `ACCESS_TOKEN_EXPIRE_MINUTES` / `REFRESH_TOKEN_EXPIRE_DAYS` | 30 / 15 | |
| `EMAIL_PROVIDER` | `console` | `console` or `smtp` |
| `SMTP_*` | — | host / port / user / password / from / tls |

---

## API response format

Success and error responses are consistent envelopes.

```jsonc
// success
{ "data": { ... }, "status": "ok" }
// error
{ "errors": { "field": ["message"] }, "message": "..." }
```

Build them with `app/shared/response.py`:
```python
from app.shared.response import success
return success(payload, "created")
```
Raise domain errors with `AppError`; validation errors are auto-formatted into the envelope.
```python
from app.core.exceptions import AppError
raise AppError("Email already registered.", 409)
```

---

## Auth

| Method | Path | Body |
|---|---|---|
| POST | `/api/auth/register` | email, password, first_name, last_name |
| POST | `/api/auth/login` | email, password |
| POST | `/api/auth/refresh` | refresh_token |
| POST | `/api/auth/logout` | refresh_token |
| GET | `/api/auth/me` | — (Bearer) |
| POST | `/api/auth/verify-email` | token |
| POST | `/api/auth/resend-verification` | email |
| POST | `/api/auth/forgot-password` | email |
| POST | `/api/auth/reset-password` | token, password |

- Passwords hashed with bcrypt **off the event loop** (`anyio.to_thread`).
- Refresh tokens are stored hashed and **rotated** on every refresh; logout revokes them.
- Account locks after 5 failed logins; a constant-time guard avoids user enumeration.
- Registration emails a **verification** link (24 h); `is_verified` flips on `/verify-email`. Resend and forgot-password are rate-limited (3 / 5 min) and never leak whether an email exists.
- **Password reset** via emailed token (30 min); resetting revokes all of the user's refresh tokens.
- Protect a route with the current user:
  ```python
  from app.core.dependencies import CurrentUser
  @router.get("/me")
  async def me(user: CurrentUser): ...
  ```

## MFA (TOTP)

| Method | Path | Body |
|---|---|---|
| POST | `/api/auth/mfa/setup` | — (Bearer) → `{secret, otpauth_uri}` |
| POST | `/api/auth/mfa/enable` | `mfa_code` (Bearer) |
| POST | `/api/auth/mfa/disable` | `mfa_code` (Bearer) |
| POST | `/api/auth/verify-mfa-login` | `login_token`, `mfa_code` |

Login flow when MFA is enabled:
1. `POST /auth/login` → `{ "mfa_required": true, "login_token": "..." }` (short-lived, 5 min)
2. `POST /auth/verify-mfa-login` with `login_token` + `mfa_code` → access & refresh tokens

> The TOTP secret (`users.mfa_secret`) is stored plaintext; encrypt it at rest for production.

---

## Authorization (roles)

Role-based guard as a dependency; `SUPER_ADMIN` bypasses every check.

```python
from fastapi import Depends
from app.core.dependencies import AdminUser, require_role

# inject the user (ADMIN or SUPER_ADMIN only)
@router.get("/admin/stats")
async def stats(user: AdminUser): ...

# or gate a route without needing the user object
@router.delete("/things/{id}", dependencies=[Depends(require_role("ADMIN", "MANAGER"))])
async def delete_thing(id: str): ...
```

Roles live on `users.role` (`SUPER_ADMIN` / `ADMIN` / `USER`); a failure raises `403`. Roles gate
**actions**; RLS (`org_id`) gates **rows** — they're separate layers.

**Growing to custom roles + permissions:** when the dashboard needs finer per-role control, add a
`require_permission("orders:delete")` dependency backed first by a static `ROLE_PERMISSIONS` map (no
tables), then DB-backed role/permission rows once tenants define their own roles. Routes swap
`require_role` → `require_permission`; the dependency shape is unchanged.

---

## Multi-tenancy (Postgres RLS)

Shared schema, isolated at the database. Add `TenantMixin` to any tenant-scoped model and enable the
policy in its migration.

```python
from app.core.database import Base
from app.core.tenancy import TenantMixin

class Order(TenantMixin, Base):       # adds indexed org_id
    __tablename__ = "orders"
    ...
```

```python
# in the migration
from app.core.tenancy import rls_statements
for sql in rls_statements("orders"):
    op.execute(sql)
```

Set the tenant per request/transaction (transaction-local, pool-safe):
```python
from app.core.tenancy import set_tenant
await set_tenant(db, org_id)          # SET LOCAL app.current_org
```
With no tenant set, RLS denies by default (no rows). The `users` table is intentionally **global**
(auth lives above tenancy). Cross-org admin access → a DB role with `BYPASSRLS`.

---

## Background jobs (Celery)

```bash
make worker     # celery -A app.core.celery_app worker
make beat       # celery -A app.core.celery_app beat
```

Tasks live in `modules/<x>/tasks.py` (or `providers/<x>/tasks.py`); both are autodiscovered. Because
Celery tasks are sync, call async code through the bridge in `core/worker.py`:

```python
from app.core.celery_app import celery_app
from app.core.worker import run_async, worker_session_factory
from sqlalchemy import delete

@celery_app.task(name="orders.purge_drafts")
def purge_drafts() -> int:
    return run_async(_purge())

async def _purge() -> int:
    async with worker_session_factory()() as db:
        await db.execute(delete(...))
        await db.commit()
```
Schedule periodic tasks in `core/celery_app.py` → `beat_schedule`. (Ships with a daily
refresh-token purge.)

---

## Email

Swappable provider selected by `EMAIL_PROVIDER` (`console` for dev, `smtp` for prod) — same interface,
no code change. Email is **sent via Celery**, never in-request.

```python
from app.providers.email.render import render_email
from app.providers.email.tasks import send_email

html = render_email("welcome.html", first_name=user.first_name, app_name=settings.APP_NAME)
send_email.delay(user.email, "Welcome", html)
```

Templates live in `app/providers/email/templates/` (Jinja2, autoescaped, `extends base.html`). Add a
new email = drop a `.html` and call `render_email("x.html", **ctx)`. Add a new backend = implement
`EmailProvider.send` and register it in `providers/email/__init__.py`.

---

## File storage

Swappable storage selected by `STORAGE_PROVIDER` (`local` for dev, `s3` for prod). **S3 uses
presigned URLs** — clients upload and download directly to/from S3; files never stream through the
backend. The `file` module:

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/file/upload/` | get a presigned **upload** URL |
| GET | `/api/file/access/?key=…` | get a presigned **access** URL |
| PUT | `/api/file/local/{key}` | local-dev upload receiver (used when `STORAGE_PROVIDER=local`) |

Flow:
1. `POST /api/file/upload/` `{filename, content_type}` → `{ key, upload_url, method: "PUT" }`
2. Client `PUT`s the bytes to `upload_url` (straight to S3 in prod) with the matching `Content-Type`
3. Persist the returned `key`; later `GET /api/file/access/?key=<key>` → `{ url }` to view/download

In `local` mode the same flow works: `upload_url` points at `/api/file/local/{key}` (the backend
receiver) and `access_url` is served from `STORAGE_LOCAL_BASE_URL`. To actually serve local files,
mount the dir in `main.py`:
```python
from fastapi.staticfiles import StaticFiles
app.mount("/uploads", StaticFiles(directory=settings.STORAGE_LOCAL_DIR))
```

Inject the active provider anywhere via the `Storage` dependency:
```python
from app.core.dependencies import Storage
async def route(storage: Storage):
    await storage.delete(key)
```
Add a backend = implement `StorageProvider` (`upload_url` / `access_url` / `save` / `delete`) and
register it in `providers/storage/__init__.py`. S3 presigned URLs are **SigV4**, 1-hour expiry.

---

## Pagination

Page-based (`page` / `per_page`), exposed as a dependency.

```python
from app.shared.pagination import Paginate, paginated
from sqlalchemy import func, select

@router.get("/items")
async def list_items(db: DbSession, page: Paginate):
    total = await db.scalar(select(func.count()).select_from(Item))
    rows = (await db.execute(select(Item).limit(page.limit).offset(page.offset))).scalars().all()
    return success(paginated([ItemOut.model_validate(r).model_dump() for r in rows], total, page))
```

Query params: `?page=1&per_page=20` (`per_page` capped at 100). `paginated()` returns:
```json
{ "items": [...], "total": 137, "page": 1, "per_page": 20, "pages": 7 }
```
`page.limit` / `page.offset` are derived for queries; the API stays page-based.

---

## Rate limiting

Redis fixed-window limiter, applied as a route dependency. Named presets are reusable:

```python
from app.shared.rate_limiter import LoginRateLimit, DefaultRateLimit, rate_limit
from fastapi import Depends

@router.post("/login", dependencies=[LoginRateLimit])           # 5 / 60s
@router.post("/things", dependencies=[DefaultRateLimit])        # 60 / 60s
@router.post("/otp", dependencies=[Depends(rate_limit(3, 60))]) # custom
```
Exceeding the limit raises `AppError("Too many requests.", 429)`.

## Caching

```python
from app.shared.cache import cache_get, cache_set
from app.core.dependencies import RedisSession

async def route(redis: RedisSession):
    if (hit := await cache_get(redis, "key")) is not None:
        return hit
    value = ...
    await cache_set(redis, "key", value, ttl=300)
```

---

## Database & migrations

Async Alembic. Models are **auto-discovered** — `alembic/env.py` walks `modules/*/models.py`, so a new
module's tables are picked up with no `env.py` edits.

```bash
make alembic-revision MSG="add orders"   # autogenerate
make alembic-upgrade                     # apply
```

---

## Adding a new module

```bash
mkdir -p app/modules/orders
# create __init__.py, router.py, service.py, schema.py, models.py (+ tasks.py)
```
1. `models.py` — SQLAlchemy models (add `TenantMixin` if tenant-scoped).
2. `service.py` — business logic (`class OrderService: __init__(self, db)`).
3. `router.py` — thin endpoints returning `success(...)`.
4. Include it in `app/main.py`: `app.include_router(orders_router, prefix="/api")`.
5. `make alembic-revision MSG="orders"` → `make alembic-upgrade`.
6. Add tasks to `tasks.py` and register the package in `celery_app.autodiscover_tasks([...])`.

**Channels (WhatsApp/FB/IG)** and the **AI agent** subsystem are added per app the same way — channels
follow the `providers/email` pattern (a `base.py` interface + env-selected adapters); the agent is a
module that calls feature services in-process.

---

## Make targets

| Target | Action |
|---|---|
| `make start` | run the API (reload) |
| `make worker` / `make beat` | Celery worker / scheduler |
| `make alembic-revision MSG=…` / `make alembic-upgrade` | migrations |
| `make lint` / `make format` | ruff check / format |
