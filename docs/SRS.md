# Software Requirements Specification
## Tournament Management System (TMS)

**Status:** Baselined. Changes tracked in `docs/change-log.md`.
**Last updated:** 2026-09-16 (incorporates CR-001 through CR-009)

---

## 1. Introduction

### 1.1 Purpose
This document specifies the functional and non-functional requirements for the
Tournament Management System (TMS), a web-based application for creating, configuring,
managing, and viewing tournaments across both team-based and individual sports.

### 1.2 Scope
TMS supports two participation types (`TEAM`, `INDIVIDUAL`) and two tournament formats
(`ROUND_ROBIN`, `KNOCKOUT`) as independent dimensions, without sport-specific branching
in fixture generation or scoring logic. `sport` is a free-text descriptive field on
Tournament with no fixed list — the backend places no restriction on its value.

### 1.3 Out of Scope
- Swiss-system tournaments, double round-robin, double elimination, third-place matches
- Advanced sport-specific scoring (e.g. football penalty shootouts)
- Live scoring, notifications, chat, payments, AI features, mobile application
- Account lockout after failed logins (rate limiting provides baseline brute-force
  protection instead — see §13)
- Real SMTP email delivery (development-mode token exposure used instead — see §9.3, §9.4)
- Pagination on tournament-scoped lists (participants, matches, standings) — naturally
  bounded by tournament size
- File/image upload (no tournament cover images, no attachments)

These may be documented as future enhancements but are not implemented in this version.

---

## 2. Actors

### 2.1 Guest *(CR-001)*
An unauthenticated visitor. Can, without logging in or registering:
- view the list of tournaments and tournament details, with optional status filtering
- view registered participants, teams, and players, and public player profiles
- view fixtures/matches, including assigned venue and scheduled time
- view match results
- view standings

Cannot perform any write action.

### 2.2 Player *(CR-002, CR-007, CR-008, CR-009)*
Everything a Guest can do, plus, once registered and logged in:
- register their own `Player` profile as part of account registration (§7.1)
- self-register as a participant in `INDIVIDUAL` tournaments only (§7.5) — cannot
  self-register into `TEAM` tournaments, and cannot register a team on anyone's behalf
- update their own team affiliation, including leaving a team entirely (§7.4)
- view their own profile (`GET /auth/me`) and their own tournament history
  (`GET /auth/me/tournaments`)
- view their own or any player's public profile, including tournament-win
  achievements correctly attributed to the team they were actually on at the time
  (§12.3, CR-009), and any team's own win history (§12.3a)
- log out (revokes their current session token — see §9.2)
- request a password reset if forgotten

### 2.3 Organizer
Everything a Guest can do, plus, once registered and logged in:
- create tournaments; edit name/description/sport while `DRAFT` (§6.1)
- open/close registration; start a tournament only once at least two participants are
  registered (§6.3, CR-006)
- register participants (any type, on behalf of anyone) while registration is open;
  remove a participant before the tournament starts (§7.3)
- generate fixtures once `ONGOING`
- assign a venue and schedule (date/time) to each match, required before that match's
  result can be submitted (§11.7, CR-005)
- submit match results — transactional, and the sole path to recording a result; no
  player-submission path exists under any configuration
- manage knockout progression (automatic once results are submitted)
- update any player's team affiliation on their behalf

**Organizers cannot create `Player` or `Team` records** — that only happens through
Player self-registration (§7.1). This is enforced at the schema-validation level;
including player/team fields on an Organizer registration returns `400`.

Every tournament-scoped write action (participant registration, participant removal,
fixture generation, match scheduling, result submission, and all lifecycle/CRUD
operations on the Tournament itself) verifies that the authenticated organizer is the
**same organizer who created that tournament** (`tournament.organizer_id ==
authenticated_user_id`) — enforced consistently across every relevant service function
following the CR-004 hardening pass. An organizer with a valid token cannot manage a
tournament they do not own; such attempts return `403 Forbidden`.

---

## 3. Participation Model

```
ParticipationType
    TEAM
    INDIVIDUAL
```

**TEAM** — a team participates as a unit. Players may optionally belong to a team.
**INDIVIDUAL** — an individual player participates directly. No team is involved.

`participation_type` and `format` (§4) are independent, orthogonal fields on a
Tournament — never inferred from `sport`.

---

## 4. Tournament Format

```
TournamentFormat
    ROUND_ROBIN
    KNOCKOUT
```

---

## 5. Core Domain Model

```
User
  ├── Player (0..1)
  │     └── Team (0..1, via team_id)
  └── Organizer role

Team
  └── Player (0..N)

Tournament
  ├── organizer_id → User
  ├── TournamentParticipant (0..N)
  │     └── Participant (exactly one Player OR one Team)
  ├── Match (0..N)
  │     ├── venue_id → Venue (nullable until scheduled)
  │     ├── scheduled_at (nullable until scheduled)
  │     ├── MatchParticipant (0..2 — see §11.4 for TBA slot handling)
  │     │     └── Participant
  │     │           └── MatchScore
  │     └── MatchResult
  │           └── winner_participant_id → Participant (nullable for DRAW)
  └── Standing (0..N)
        └── Participant

User
  ├── PasswordResetToken (0..N, cascade-deleted with User)
  └── EmailVerificationToken (0..N, cascade-deleted with User)
```

The **Participant** entity is the central generic abstraction: it represents whoever
actually competes, and is exactly one Player or exactly one Team, never both, never
neither. This allows Match, MatchResult, MatchScore, and Standing to all reference
`Participant` generically.

---

## 6. Tournament Lifecycle

```
DRAFT → REGISTRATION_OPEN → ONGOING → COMPLETED
```

| Current State | Allowed Next State |
|---|---|
| DRAFT | REGISTRATION_OPEN |
| REGISTRATION_OPEN | ONGOING |
| ONGOING | COMPLETED |
| COMPLETED | *(none — terminal)* |

No skipping and no reverse transitions. The service layer rejects any transition not in
this table.

**DRAFT** → **REGISTRATION_OPEN**: entered via explicit organizer action.
**REGISTRATION_OPEN** → **ONGOING**: entered via explicit organizer action, **and only
if at least two participants are registered** (§6.3, CR-006) — otherwise rejected with
`409`.
**COMPLETED**: entered automatically once the final knockout match or the last
scheduled round-robin match's result is submitted (§11.6).

### 6.1 Configuration Locking
Before `REGISTRATION_OPEN`: organizer may freely edit `name`, `description`, `sport`,
`participant_type`, `format`, `start_date`, `end_date`.

Once `REGISTRATION_OPEN` or later: `participant_type` and `format` are locked
(`409 Conflict` if changed).

Once `ONGOING`: participants cannot be added through normal operations (only removable
before `ONGOING` — see §7.3); fixtures cannot be arbitrarily changed; completed matches
cannot be modified through normal operations.

Once `COMPLETED`: the tournament is fully read-only.

### 6.2 Ownership Enforcement
See §2.3. Every tournament-scoped write verifies `tournament.organizer_id` against the
authenticated user; mismatches return `403`.

### 6.3 Minimum Participant Requirement *(CR-006)*
`REGISTRATION_OPEN → ONGOING` additionally requires at least **two** registered
participants (`TournamentParticipant` rows). Attempting to start a tournament with
fewer than two returns `409 Conflict` with a descriptive message. This prevents a
tournament from becoming permanently stuck `ONGOING` with no valid fixtures possible
(fixture generation independently requires ≥2 participants; without this lifecycle
guard, a tournament could reach `ONGOING` and then have no path to `COMPLETED`).

---

## 7. Registration & Account Model *(CR-002, CR-007)*

### 7.1 Player Self-Registration

`POST /auth/register` with `role=PLAYER` requires additional fields:

```
participation_type: INDIVIDUAL | TEAM   (required)

If participation_type = TEAM:
  team_option: NEW | EXISTING            (required)
  If team_option = NEW:
    team_name: string                    (required)
  If team_option = EXISTING:
    team_id: integer                     (required)
```

On success, a `Player` row is created automatically, linked to the new `User` via
`user_id`. If `participation_type = TEAM`, the `Player` is also linked to the
specified team — either a newly created `Team` (rejecting duplicate names with `409`)
or an existing one (rejecting an invalid ID with `404`).

**Note:** `participation_type` here describes how the player *identifies themself* at
signup (do they play individually, or are they part of a team roster) — it is
independent of, and does not restrict, which specific tournaments they may later join;
see §7.5 for the actual per-tournament registration rule.

### 7.2 Organizer Registration

`POST /auth/register` with `role=ORGANIZER` accepts only `name`, `email`, `password`,
`role`. Including any of `participation_type`, `team_option`, `team_name`, `team_id`
is rejected with `400` — organizers never create Player or Team records.

### 7.3 Participant Removal

`DELETE /tournaments/{id}/participants/{participant_id}` — organizer-only (owning
organizer), permitted only while the tournament is `DRAFT` or `REGISTRATION_OPEN`.
Returns `409` if attempted once the tournament is `ONGOING` or `COMPLETED`. If a
`Standing` row already exists for the removed participant (e.g. created by an earlier
standings-view backfill — see §11.2), it is deleted along with the registration, so a
removed participant never lingers in the standings view *(CR-004)*.

### 7.4 Player-Team Update

`PUT /players/{id}/team` — either the Player themself (verified via their own
`user_id`) or any Organizer may reassign a player's `team_id`, including setting it
to `null` to remove them from a team entirely. A Player attempting to update another
player's team affiliation receives `403`.

### 7.5 Per-Tournament Participant Registration Rules *(CR-007)*

`POST /tournaments/{id}/participants` — requires `REGISTRATION_OPEN` status.

| Caller role | Behavior |
|---|---|
| Organizer (owning) | May register a `player_id` or `team_id`, matching the tournament's `participant_type`, on behalf of anyone, into any tournament they own. |
| Player | May self-register **only their own** `player_id` (verified server-side; supplying someone else's `player_id` returns `403`), and **only into `INDIVIDUAL` tournaments**. Attempting to self-register into a `TEAM` tournament, or to submit a `team_id` at all, returns `403`. |

Team registration is therefore organizer-managed in all cases — there is no
self-service path for a player to commit an entire team's roster to a tournament,
since no "team captain" concept exists in the data model.

When a `team_id` is registered (by an Organizer), the system snapshots the team's
current roster into `TournamentParticipantMember` rows at that moment — one per
current member — so achievement attribution can later be resolved against *who was
actually on the team when it registered*, not whoever happens to be on the team when
someone later looks up an achievement (§12.3, CR-009).

---

## 8. Data Model

*(Unchanged from the frozen database design for the core tournament tables — see the
Frozen DB Design document for full column-level detail on Player, Team, Tournament,
Participant, TournamentParticipant, Venue, Match, MatchParticipant, MatchResult,
MatchScore, and Standing. Columns added under later CRs are shown below. An
Entity-Relationship diagram is maintained separately at `docs/diagrams/er-diagram.svg`,
using Chen notation: entities as rectangles, attributes as ovals, relationships as
diamonds.)*

### 8.1 User
| Column | Type | Constraint |
|---|---|---|
| id | Integer | PK |
| name | String | NOT NULL |
| email | String | UNIQUE, NOT NULL |
| password_hash | String | NOT NULL |
| role | Enum(ORGANIZER, PLAYER) | NOT NULL |
| is_verified | Boolean | NOT NULL, default False *(CR-003)* |
| created_at | DateTime | NOT NULL |

### 8.2 Match *(fields relevant to CR-005; unchanged fields omitted, see Frozen DB Design)*
| Column | Type | Constraint |
|---|---|---|
| venue_id | Integer | FK → Venue.id, nullable |
| scheduled_at | DateTime (tz-aware) | nullable |

Both fields are nullable by design (a match may exist before it is scheduled), but
**both must be non-null before a result can be submitted for that match** (§11.7).

### 8.3 Indexes *(CR-004)*
Explicit B-tree indexes are declared on every foreign-key column across all tables
(`Tournament.organizer_id`, `Player.team_id`, `Player.user_id`,
`Participant.player_id`, `Participant.team_id`, `TournamentParticipant.tournament_id`,
`TournamentParticipant.participant_id`, `Match.tournament_id`, `Match.venue_id`,
`MatchParticipant.match_id`, `MatchParticipant.participant_id`,
`MatchResult.match_id`, `MatchResult.winner_participant_id`, `Standing.tournament_id`,
`Standing.participant_id`), since PostgreSQL does not automatically index foreign keys.

### 8.4 Cascade Deletes *(CR-004)*
`PasswordResetToken.user_id` and `EmailVerificationToken.user_id` are declared with
`ON DELETE CASCADE` — deleting a `User` automatically removes their outstanding
reset/verification tokens rather than raising a foreign-key violation. No other
relationship in the schema cascades on delete; deleting a `Tournament`, `Match`, or
similar core entity with dependent records is intentionally blocked, to avoid silent
loss of tournament history.

### 8.5 Tournament Participant Roster Snapshot *(CR-009)*
| Column | Type | Constraint |
|---|---|---|
| id | Integer | PK |
| tournament_participant_id | Integer | FK → TournamentParticipant.id, NOT NULL, indexed |
| player_id | Integer | FK → Player.id, NOT NULL, indexed |
| created_at | DateTime (tz-aware) | NOT NULL |

Unique on `(tournament_participant_id, player_id)`. One row is written per current
team member at the moment a `team_id` is registered into a tournament (§7.5) — a
point-in-time roster snapshot, never updated afterward regardless of later roster
changes. See §12.3 for how this is used.

---

## 9. Authentication & Account Management *(CR-003)*

### 9.1 Passwords
Hashed via `werkzeug.security`, never stored or compared as plaintext.

### 9.2 Logout / Token Revocation
`POST /auth/logout` (requires valid JWT) — records the token's `jti` (JWT ID) and its
original `exp` (expiry) in a `TokenBlocklist` table. Subsequent requests presenting a
blocklisted token are rejected as unauthenticated, even though the token has not
naturally expired yet. Blocklist entries store `expires_at` so that entries for
tokens which have since expired naturally can be safely purged (not currently
scheduled automatically — see §13).

### 9.3 Password Reset
```
POST /auth/forgot-password  { email }
  -> generates a PasswordResetToken (30-minute TTL)
  -> invalidates any previously issued, still-unused tokens for that user
  -> in development mode only, returns the raw token in the response body
     (dev_token field) since no SMTP provider is configured; production
     would email it instead and never expose it via the API

POST /auth/reset-password  { token, new_password }
  -> validates token is unused and unexpired
  -> updates password_hash
  -> marks token used
```

### 9.4 Email Verification
`User.is_verified` (boolean, default `false`) is set via `GET
/auth/verify-email?token=...`. An `EmailVerificationToken` (48-hour TTL) is generated
automatically at registration time; in development mode the token is returned in the
registration response (`dev_verification_token`). **Verification is tracked but not
enforced** — an unverified user can still log in and use the system normally.

### 9.5 Rate Limiting
| Endpoint | Limit |
|---|---|
| `POST /auth/login` | 5 per minute per IP |
| `POST /auth/register` | 20 per minute per IP |

`/auth/register`'s limit was raised from an initial 5/minute after integration testing
showed 5/minute was unrealistically tight for an organizer performing legitimate bulk
player registration. `/auth/login` remains at 5/minute, since brute-force protection
on a single account's password — not bulk throughput — is the relevant threat model
there. Disabled automatically in the test configuration. Uses in-memory storage (§13).

---

## 10. Match Results — Draws and Winners

For round-robin tournaments, equal scores produce a draw (`result_type = DRAW`,
`winner_participant_id = NULL`). **For knockout tournaments, a completed match must
produce a winner — a `DRAW` result is rejected outright with `400`** *(CR-005)*,
requiring the organizer to resolve ties by whatever real-world tie-break mechanism
applies (e.g. penalties, sudden death) and submit the deciding outcome as a `WIN`. No
automated rematch/replay mechanism exists; this is a deliberate scope decision (see
§1.3).

Result submission is organizer-only, with the owning-organizer check from §2.3
applied. Players do not submit their own match results under any configuration.

---

## 11. Fixture Generation, Scheduling & Match Result Transaction

### 11.1 Round-Robin
For N participants: `N(N-1)/2` matches for even N; odd N gets a bye per round via the
circle method. No self-pairing, no duplicate pairing.

### 11.2 Round-Robin Standings
Win = 3 points, Draw = 1, Loss = 0. `score_difference = total for - total against`.
Ordering: points desc, then score difference desc, then total score desc, then name
asc. Every registered participant appears in standings with zero values from the
moment fixtures exist (a backfill on read ensures this — see §7.3 for the
corresponding cleanup rule when a participant is later removed).

### 11.3 Knockout — Bracket Sizing & Byes
Bracket size = smallest power of two >= participant count. Byes assigned to the first
N registered participants deterministically; a bye is represented as an immediately
`COMPLETED` single-participant match with a `MatchResult` already recorded.

### 11.4 Knockout — Progression & TBA Slots
A match winner advances automatically to the next round's corresponding slot. Until
both slots of a future-round match are filled, that match has fewer than two
`MatchParticipant` rows; clients display the unfilled side as "TBA." Final's winner =
champion; no third-place match.

### 11.5 Sport Independence
Fixture generation branches on `participant_type` and `format` only, never on `sport`.

### 11.6 Automatic Tournament Completion
When a knockout final concludes, or the last scheduled round-robin match completes,
the tournament automatically transitions to `COMPLETED` — a system-triggered
transition, not requiring explicit organizer action.

### 11.7 Match Scheduling — Venue and Time *(CR-005)*
`PUT /matches/{id}/schedule` — organizer-only (owning organizer). Body:
`{ "venue_id": <int, optional>, "scheduled_at": <ISO datetime, optional> }`.

Rules:
- `scheduled_at` **must not be in the past** relative to the time of the request
  (server-side clock, UTC); attempting to schedule a match in the past returns `400`.
- `venue_id`, if provided, must reference an existing `Venue`, or `404` is returned.
- **A match's result cannot be submitted until it has both a non-null `venue_id` and a
  non-null `scheduled_at`.** Attempting `POST /matches/{id}/result` on an unscheduled
  match returns `409 Conflict`. This does not apply to knockout byes, which are
  auto-completed by the fixture-generation process itself and never pass through the
  normal result-submission path.
- `GET /matches/{id}` (a standalone single-match lookup, added to support this
  workflow and any client needing to resolve a match by ID directly rather than only
  via a tournament's match list) is public, matching the read-access rule in §2.1.

### 11.8 Match Result Transaction
```
Validate Match -> Validate Schedule Is Set -> Validate Scores -> Create MatchResult ->
Create MatchScore rows -> Update Match.status = COMPLETED -> Update Standings /
Progression -> COMMIT
```
Any failure triggers full ROLLBACK (see §14 for the ACID rationale).

---

## 12. API Summary

Base path: `/api/v1`. Governing rule (CR-001): **all `GET` endpoints are public; all
`POST`/`PUT`/`DELETE` endpoints require authentication**, almost always requiring the
ORGANIZER role plus tournament ownership where applicable (§2.3). Full endpoint list
maintained in `README.md`.

### 12.1 Pagination
`GET /tournaments`, `GET /players`, `GET /teams` return
`{"items": [...], "page", "per_page", "total", "total_pages"}` rather than a bare
array. All other list endpoints are unpaginated. `GET /tournaments` additionally
accepts `?status=DRAFT|REGISTRATION_OPEN|ONGOING|COMPLETED` for filtering.

### 12.2 Enriched Profile & Tournament Data *(CR-004, CR-008)*
- `GET /auth/me` includes `player_id`, `team_id`, and `team_name` (all `null` for an
  Organizer, or a Player with no team) in addition to the base user fields.
- `GET /auth/me/tournaments` returns `{"upcoming": [...], "past": [...]}` — tournaments
  the logged-in player is registered in (individually, or via their current team),
  split by whether the tournament has reached `COMPLETED`.
- `GET /tournaments/{id}` includes `organizer_name` and `organizer_email`, so a
  prospective team registrant can identify who to contact for a `TEAM` tournament
  they cannot self-register into (§7.5).
- Participant objects returned from `GET /tournaments/{id}/participants`, `GET
  /tournaments/{id}/matches`, and match-result payloads include `player_id`/`team_id`
  alongside the display `name`, so clients can link to a player's public profile or a
  team's roster without a separate lookup.

- `GET /tournaments/{id}/standings` rows include `player_id`/`team_id` alongside
  `participant_id` and `name`, for the same client-side linking purpose.

### 12.3 Player Achievements & Public Profile *(CR-008, CR-009)*
`GET /players/{id}/profile` (public) returns:
```json
{
  "id": 7, "name": "...", "team_id": 3, "team_name": "...",
  "achievements": {
    "individual": [
      {"tournament_id": 12, "tournament_name": "...", "sport": "...", "format": "..."}
    ],
    "current_team": [
      {"tournament_id": 9, "tournament_name": "...", "sport": "...", "format": "...",
       "team_id": 3, "team_name": "..."}
    ],
    "previous_team": [
      {"tournament_id": 4, "tournament_name": "...", "sport": "...", "format": "...",
       "team_id": 1, "team_name": "..."}
    ]
  }
}
```
An "achievement" is a `COMPLETED` tournament this player won — either as the
round-robin standings leader, or as the knockout final's recorded winner.
`individual` achievements are matched against the player's own individual
`Participant` record. Team achievements are matched only against tournaments where a
`TournamentParticipantMember` snapshot row (§8.5) proves this specific player was
actually on that team's roster when it registered — never against a team's wins in
general. Each such achievement is then classified as `current_team` if the winning
team is still the player's team today, or `previous_team` if the player has since
moved to a different team (or left team play entirely). A player who joins a team
*after* it won something gains no credit for that win, since no snapshot row ties
them to that registration — this was the exact failure mode of the pre-CR-009
approach (see the change log for the full before/after).

### 12.3a Team Achievements *(CR-009)*
`GET /teams/{id}/achievements` (public) returns:
```json
{ "team_id": 3, "team_name": "...", "achievements": [
    {"tournament_id": 9, "tournament_name": "...", "sport": "...", "format": "..."}
] }
```
All `COMPLETED` tournaments this team's own `Participant` record has won, independent
of roster history or of any individual player's current affiliation — this is the
team's own win history, unaffected by who has since joined or left.

### 12.4 Standard Error Responses
| Code | Meaning |
|---|---|
| 400 | Bad Request - invalid input, invalid lifecycle transition, past-dated schedule |
| 401 | Unauthorized - missing/invalid/revoked JWT |
| 403 | Forbidden - wrong role, not the owning organizer, self-registration overreach |
| 404 | Not Found |
| 409 | Conflict - duplicate registration, duplicate result, invalid state transition, insufficient participants to start, unscheduled match |
| 429 | Too Many Requests - rate limit exceeded (§9.5) |
| 500 | Internal Server Error |

Response body: `{ "error": "<message>" }`

---

## 13. Non-Functional Requirements

- **Security:** passwords hashed; JWT secret from environment variables with no
  fallback default; `.env` never committed; CORS restricted to an explicit origin
  allowlist (`CORS_ORIGINS` env var) rather than wide open; all organizer-only routes
  protected by role-based authorization plus ownership verification (§2.3).
- **Data Integrity:** multi-step writes are transactional with rollback on failure
  (see §14, ACID). Uniqueness and referential integrity enforced at the database level
  in addition to service-level validation. Explicit indexes on all foreign keys (§8.3).
  Controlled cascade deletes only where semantically correct (§8.4).
- **Extensibility:** sport-agnostic domain model.
- **Known limitations (documented, not defects):**
  - Rate limiting uses in-memory storage — resets on server restart and would not
    function correctly across multiple server processes. Acceptable for this
    project's single-process deployment scope; a production deployment would use a
    shared store (e.g. Redis).
  - Token blocklist entries are not automatically purged on a schedule; a
    `TokenBlocklist.purge_expired()` utility exists but must be invoked manually or
    via a future maintenance job.
  - Email verification and password reset tokens are exposed directly in API
    responses in development mode only, since no SMTP provider is configured. This
    must never be enabled in a production deployment.
  - No application-level locking beyond PostgreSQL's default transaction isolation;
    acceptable given the project's realistic concurrency profile (§14).

---

## 14. ACID Properties in This System

| Property | Implementation |
|---|---|
| **Atomicity** | Multi-step writes — most notably `submit_result()` (validate → create result → create scores → update match status → update standings → advance knockout winner → possibly auto-complete tournament) — run inside a single database transaction with explicit rollback on any failure, so a partial failure never leaves a result recorded without its corresponding standings update. |
| **Consistency** | Enforced via database CHECK/UNIQUE/FK constraints (e.g. a `Participant` must reference exactly one of Player/Team; `MatchResult.result_type = WIN` requires a winner) combined with service-layer business rules (the lifecycle state machine, the knockout-cannot-draw rule, the schedule-before-result rule). Every committed transaction leaves the database in a valid state. |
| **Isolation** | Relies on PostgreSQL's default Read Committed isolation level and row-level locking; concurrent result submissions for different matches do not corrupt shared `Standing` rows. No additional application-level locking is implemented, which is an accepted scope limitation given this system's realistic single-organizer-at-a-time usage pattern. |
| **Durability** | Standard PostgreSQL write-ahead logging guarantees committed data survives an application or server restart. The only intentionally non-durable state in the system is the rate limiter's in-memory counter (§9.5, §13), which is not part of the transactional domain data. |

---

## 15. Architecture

```
React Frontend -> REST API -> Routes/Controllers -> Services -> SQLAlchemy Models -> PostgreSQL
```

Business logic resides in the service layer, not in route functions.

---

## 16. Testing Summary

- **116 automated tests** (pytest), covering models, services, and routes across every
  functional requirement, change request, and hardening fix described in this document.
- **2 manual end-to-end integration scenarios** run against the live API (documented in
  `backend/scripts/scenario_a.ps1`, `scenario_b.ps1`): a full round-robin lifecycle and
  a full knockout lifecycle including byes.
- Integration testing and subsequent manual exploratory testing surfaced and led to
  fixes for: a missing FK cascade, an overly strict rate limit, a broken migration
  downgrade, a missing organizer-ownership check on three services, orphaned standings
  rows after participant removal, the ability to start a tournament with too few
  participants, the ability to submit an unscheduled match's result, the ability
  to schedule a match in the past, and incorrect achievement attribution after a
  player changed teams — see `docs/change-log.md` for full detail per CR.

---

## 17. Diagrams

Maintained under `docs/diagrams/`:
- `context-diagram.svg` / Level 1 DFD — see the project's DFD documentation for the
  full data-flow decomposition (Guest/Player/Organizer as external entities; P1–P6 as
  the major internal processes; D1–D6 as the underlying data stores).
- `er-diagram.svg` — Chen-notation Entity-Relationship diagram (entities as
  rectangles, attributes as ovals, relationships as diamonds).

---

## 18. Change History

See `docs/change-log.md` for full narrative detail on each entry.

| CR | Summary | Status |
|---|---|---|
| CR-001 | Guest actor with public read access | Approved, implemented |
| CR-002 | Player self-registration with team creation/joining | Approved, implemented |
| CR-003 | Auth hardening (logout, password reset, email verification), pagination, rate limiting | Approved, implemented |
| CR-004 | Post-build hardening: ownership checks on participant/fixture/result services, participant/match name resolution, standings backfill & cleanup, single-item GET routes, player-team update, CORS tightening, FK indexes, cascade deletes | Approved, implemented |
| CR-005 | Match scheduling requirements: venue/time required before result entry, past-date rejection, standalone `GET /matches/{id}` | Approved, implemented |
| CR-006 | Minimum two participants required to start a tournament | Approved, implemented |
| CR-007 | Player self-registration restricted to `INDIVIDUAL` tournaments only; team registration remains organizer-only in all cases | Approved, implemented |
| CR-008 | Player achievements and public player profile | Approved, implemented |
| CR-009 | Roster-snapshot-based achievement attribution: team achievements are matched against who was actually on the team's roster at registration time, not the player's current team; adds `GET /teams/{id}/achievements` | Approved, implemented |