# Tournament Management System

A web-based system for creating, configuring, managing, and viewing sports and
competition tournaments — supporting both team-based (football, cricket) and
individual (chess, badminton) formats, with round-robin or knockout progression.

## Problem Statement

Organizing a tournament — registering participants, generating fair fixtures, tracking
results, and computing standings — is typically done manually or with sport-specific
tools that don't generalize across team and individual competition formats. This system
provides a single, sport-agnostic backend and frontend for running any tournament,
regardless of whether participants are teams or individuals, and regardless of whether
the format is round-robin or single-elimination knockout.

## Technology Stack

**Backend**
- Python 3.12+ / Flask 3.x
- SQLAlchemy 2.x (via Flask-SQLAlchemy)
- PostgreSQL (via `psycopg` v3)
- Flask-Migrate / Alembic for schema migrations
- Flask-JWT-Extended for authentication
- Flask-Limiter for rate limiting
- Marshmallow for request/response schema validation and serialization
- Flask-CORS
- PyTest for testing

**Frontend**
- React

## Project Objective

Support two participation types — `TEAM` and `INDIVIDUAL` — and two tournament formats —
`ROUND_ROBIN` and `KNOCKOUT` — as independent, orthogonal dimensions, without
sport-specific branching in the fixture or scoring logic. See `docs/SRS.md` for the full
requirements specification.

## Backend Status

**Complete.** All functional requirements (FR-01–FR-07) and all nine change requests
(CR-001 guest access, CR-002 player self-registration, CR-003 auth hardening, CR-004
post-build hardening, CR-005 match scheduling, CR-006 minimum participants, CR-007
individual-only self-registration, CR-008 player achievements/profile, CR-009
roster-snapshot achievement attribution) are implemented, covered by 116 automated
tests, and additionally verified through two manual end-to-end integration scenarios
against the live API. See `docs/traceability-matrix.md` for the full
requirement-to-implementation mapping.

**Frontend:** Also complete — a React (Vite) SPA under `frontend/` covering guest
browsing, player/organizer auth, tournament management, participant registration,
fixtures, results entry, and standings.

---

## Repository Structure

```
tournament-management-system/
├── frontend/
│   ├── src/
│   │   ├── pages/        # Route-level views (23 pages)
│   │   ├── components/   # auth/, common/, layout/, tournament/
│   │   ├── api/          # One module per backend resource (axios)
│   │   ├── context/      # AuthContext
│   │   ├── hooks/
│   │   └── utils/
│   ├── public/
│   ├── package.json
│   └── vite.config.js
├── backend/
│   ├── app/
│   │   ├── routes/       # HTTP endpoints
│   │   ├── models/       # SQLAlchemy models
│   │   ├── services/     # Business logic
│   │   ├── schemas/      # Marshmallow request/response schemas
│   │   ├── constants/    # Shared enums
│   │   └── utils/        # Pagination helper, etc.
│   ├── tests/
│   ├── scripts/          # Manual integration-test scripts (PowerShell + SQL)
│   ├── migrations/
│   ├── requirements.txt
│   └── run.py
└── docs/
    ├── SRS.md
    ├── change-log.md
    ├── traceability-matrix.md
    └── diagrams/          # pending — see traceability-matrix.md
```

---

## Backend Setup

### 1. Prerequisites
- Python 3.12+
- PostgreSQL running locally

### 2. Clone and enter the backend directory
```bash
git clone <repo-url>
cd tournament-management-system/backend
```

### 3. Create and activate a virtual environment
```bash
python -m venv .venv
# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1
# macOS/Linux
source .venv/bin/activate
```

### 4. Install dependencies
```bash
pip install -r requirements.txt
```

### 5. Create the databases
```bash
psql -U postgres -c "CREATE DATABASE tms_dev;"
psql -U postgres -c "CREATE DATABASE tms_test;"
```
Two separate databases are required — tests refuse to run against a non-test database
as a safety guard (checked via `conftest.py`).

### 6. Configure environment variables
```bash
cp .env.example .env
```
Generate secrets:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```
Fill in `backend/.env`:
```
DATABASE_URL=postgresql+psycopg://postgres:your_password@localhost:5432/tms_dev
TEST_DATABASE_URL=postgresql+psycopg://postgres:your_password@localhost:5432/tms_test
JWT_SECRET_KEY=<generated secret>
SECRET_KEY=<a different generated secret>
FLASK_ENV=development
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```
`.env` is gitignored and must never be committed. `.env.example` is the committed
template with placeholder values only.

### 7. Run migrations
```bash
flask --app run.py db upgrade
```

### 8. Run the server
```bash
flask --app run.py run
```
For auto-reload on code changes during development:
```bash
flask --app run.py run --debug
```
Confirm it's up:
```bash
curl http://localhost:5000/api/v1/health
```

### 9. Run tests
Always run from inside `backend/`:
```bash
python -m pytest -v
```
Expect all 116 tests to pass.

### 10. Manual integration test scripts (optional)
`backend/scripts/scenario_a.ps1` (round-robin) and `scenario_b.ps1` (knockout) run a
full lifecycle against the live server via real HTTP calls. `cleanup_integ_data.sql`
removes the test data they create. Requires the server running in a separate terminal.

---

## Frontend Setup

### 1. Prerequisites
- Node.js (LTS recommended)

### 2. Enter the frontend directory and install dependencies
```bash
cd tournament-management-system/frontend
npm install
```

### 3. Configure environment variables
```bash
cp .env.example .env
```
Fill in `frontend/.env`:
```
VITE_API_BASE_URL=http://localhost:5000/api/v1
```

### 4. Run the dev server
```bash
npm run dev
```
Confirm it's serving on `http://localhost:5173` — this must match one of the
backend's `CORS_ORIGINS` values (§6 above already includes it by default), or
requests will be blocked by the browser.

### 5. Full local run
With both the backend (`flask --app run.py run`, port 5000) and frontend
(`npm run dev`, port 5173) running simultaneously in separate terminals, open
`http://localhost:5173` to use the application.

---

## API Reference

Base path: `/api/v1`. Governing rule (CR-001): **all `GET` endpoints are public; all
`POST`/`PUT`/`DELETE` endpoints require authentication**, almost always the ORGANIZER
role, plus tournament ownership for tournament-scoped writes.

### Auth
| Endpoint | Method | Auth | Notes |
|---|---|---|---|
| `/auth/register` | POST | Public, rate-limited 20/min | See registration rules below |
| `/auth/login` | POST | Public, rate-limited 5/min | Returns JWT |
| `/auth/logout` | POST | JWT required | Revokes the current token |
| `/auth/me` | GET | JWT required | Logged-in user's profile |
| `/auth/forgot-password` | POST | Public | Dev mode returns `dev_token` |
| `/auth/reset-password` | POST | Public | |
| `/auth/verify-email` | GET | Public (`?token=`) | |
| `/auth/me/tournaments` | GET | JWT required | `{"upcoming": [...], "past": [...]}` — logged-in player's tournaments |

**Registration rules:** `role=ORGANIZER` accepts only name/email/password/role.
`role=PLAYER` additionally requires `participation_type` (`INDIVIDUAL`/`TEAM`); if
`TEAM`, also `team_option` (`NEW` + `team_name`, or `EXISTING` + `team_id`). A `Player`
record is created automatically; organizers never create Player/Team records.

### Tournaments
| Endpoint | Method | Auth | Notes |
|---|---|---|---|
| `/tournaments` | GET | **Public** | Paginated (`?page=&per_page=`) |
| `/tournaments/{id}` | GET | **Public** | |
| `/tournaments` | POST | Organizer | Starts in DRAFT |
| `/tournaments/{id}` | PUT | Organizer (owner) | Locked fields after DRAFT |
| `/tournaments/{id}/open-registration` | POST | Organizer (owner) | DRAFT → REGISTRATION_OPEN |
| `/tournaments/{id}/start` | POST | Organizer (owner) | REGISTRATION_OPEN → ONGOING |

### Venues, Players, Teams
| Endpoint | Method | Auth | Notes |
|---|---|---|---|
| `/venues` | GET | **Public** | |
| `/venues` | POST | Organizer | |
| `/players` | GET | **Public** | Paginated |
| `/players/{id}` | GET | **Public** | |
| `/players/{id}/team` | PUT | Player (self) or Organizer | Set `team_id: null` to leave a team |
| `/players/{id}/profile` | GET | **Public** | `achievements` is `{individual, current_team, previous_team}`, matched via roster snapshots taken at registration time (CR-008, CR-009) |
| `/teams` | GET | **Public** | Paginated |
| `/teams/{id}` | GET | **Public** | |
| `/teams/{id}/achievements` | GET | **Public** | Team's own win history, independent of current roster (CR-009) |

### Participants, Fixtures, Results, Standings
| Endpoint | Method | Auth | Notes |
|---|---|---|---|
| `/tournaments/{id}/participants` | GET | **Public** | |
| `/tournaments/{id}/participants` | POST | Organizer (owner) | Requires REGISTRATION_OPEN |
| `/tournaments/{id}/participants/{pid}` | DELETE | Organizer (owner) | Only before ONGOING |
| `/tournaments/{id}/fixtures` | POST | Organizer (owner) | Requires ONGOING; one-time |
| `/tournaments/{id}/matches` | GET | **Public** | Includes participant names |
| `/matches/{id}` | GET | **Public** | Standalone single-match lookup (CR-005) |
| `/matches/{id}/schedule` | PUT | Organizer (owner) | Sets `venue_id`/`scheduled_at`; rejects past dates (CR-005) |
| `/matches/{id}/result` | POST | Organizer (owner) | Transactional; organizer-only, no player path; requires venue + schedule set (CR-005) |
| `/matches/{id}/result` | GET | **Public** | |
| `/tournaments/{id}/standings` | GET | **Public** | Ordered: points → score diff → total score → name; rows include `player_id`/`team_id` for linking |

### Automatic tournament completion
The tournament transitions to `COMPLETED` automatically — no explicit organizer
action — once either: the knockout final's result is submitted, or the last scheduled
round-robin match's result is submitted.

### Pagination response shape
`GET /tournaments`, `GET /players`, `GET /teams` return:
```json
{ "items": [...], "page": 1, "per_page": 20, "total": 42, "total_pages": 3 }
```

### Standard error responses
| Code | Meaning |
|---|---|
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden (wrong role, or not the owning organizer) |
| 404 | Not Found |
| 409 | Conflict |
| 429 | Too Many Requests (rate limit) |
| 500 | Internal Server Error |

```json
{ "error": "Team is already registered in this tournament" }
```

---

## Known Limitations (documented, not defects)

- Rate limiting uses in-memory storage — resets on restart, not multi-process safe.
  Fine for this project's scope; would use Redis in a real deployment.
- Password reset and email verification tokens are exposed directly in API responses
  only when `FLASK_ENV=development`, since no SMTP provider is configured. Must never
  be enabled in production.
- Email verification is tracked (`is_verified`) but not enforced — unverified accounts
  can still log in and use the system.
- `TokenBlocklist` entries are not purged automatically on a schedule; a
  `TokenBlocklist.purge_expired()` utility exists but must be invoked manually or from
  a future maintenance job.

---

## Contributing (team workflow)

- Never commit `.env` — verify with `git status` before every commit
- Shared files requiring coordination before editing: `app/constants/enums.py`,
  `app/models/__init__.py`, `app/__init__.py`
- Update `docs/traceability-matrix.md` when a feature's implementation and tests are
  both complete, not at the end of the project
- Log any requirement change in `docs/change-log.md` before implementing it
- The dev server does not hot-reload by default — restart it (or run with `--debug`)
  after changing backend code before testing manually

---

## Documentation

- [`docs/SRS.md`](docs/SRS.md) — full requirements specification
- [`docs/change-log.md`](docs/change-log.md) — record of requirement changes since baseline
- [`docs/traceability-matrix.md`](docs/traceability-matrix.md) — requirement → design → implementation → test mapping
- [`docs/diagrams/`](docs/diagrams/) — ER diagram, class diagram, sequence diagrams, activity diagrams (pending — referenced in `docs/SRS.md` §17, but the directory doesn't exist in the repo yet — see `docs/traceability-matrix.md` "Remaining before final submission")