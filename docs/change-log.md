# Change Log

This log records requirement changes made after the initial baseline (per SRS §5's
change-management process). Every entry here has a corresponding update in `docs/SRS.md`.

**Note on CR-004–CR-008 dates:** these five entries were not individually dated in the
original per-CR log the way CR-001–CR-003 were; they're consolidated here as part of
syncing this log with `docs/SRS.md`'s 2026-09-04 revision ("incorporates CR-001 through
CR-008"). Relative ordering below (008 newest → 001 oldest) reflects the order the
SRS's own §18 Change History table lists them in, not confirmed calendar dates.

---

## CR-009 — Roster-snapshot-based achievement attribution

**Date:** 2026-09-16 (per migration `baf2dc1bd3bd`'s creation timestamp — the one CR in
this log with a directly evidenced date, unlike CR-004–008 above).

**Reason:** CR-008 shipped player achievements with a documented known limitation:
team-based wins were matched against whichever team a player *currently* belongs to,
not the roster at the time the tournament was actually won. In practice this meant a
player's win history silently rewrote itself on every team change — losing credit for
a real win the moment they left that team, and gaining undeserved credit for a team's
past win the moment they joined it. This was flagged in the original SRS as a
deliberate simplification, but was raised again during a later review as worth fixing
properly rather than leaving as a permanent limitation.

**Added:**
- `TournamentParticipantMember` table (migration `baf2dc1bd3bd`) — one row per team
  member, written at the moment a `team_id` is registered into a tournament. A
  point-in-time roster snapshot that is never updated afterward, regardless of later
  roster changes.
- `register_participant()` (`app/services/participant_service.py`) now writes these
  snapshot rows immediately after creating a `TEAM` registration.
- `get_player_achievements()` rewritten: return shape changed from a flat list to
  `{"individual": [...], "current_team": [...], "previous_team": [...]}`. Team
  achievements are now resolved via the snapshot rather than the player's live
  `team_id`, then bucketed into `current_team`/`previous_team` by comparing the
  winning team against the player's team *today*.
- `get_team_achievements()` (new) + `GET /teams/{id}/achievements` (public) — a
  team's own win history, independent of any individual player's roster status.
- `_compute_tournament_winner_participant_id()` — the round-robin/knockout
  winner-resolution logic, factored out of `get_player_achievements()` so both it and
  the new `get_team_achievements()` share one implementation instead of duplicating it.

**Breaking change, noted rather than versioned:** `GET /players/{id}/profile`'s
`achievements` field changed shape (list → object with three keys). No API version
bump accompanied this, since the only consumer is this project's own frontend, which
was updated in the same change; a project consuming this endpoint externally would
need to adjust.

**Affected SRS sections:** §2.2 (Player), §7.5 (registration-time snapshot), §8.5
(new table), §12.3 (rewritten), §12.3a (new endpoint), §13 (limitation removed), §1.3
(out-of-scope item removed, since it's now implemented)

**Status:** Approved and implemented.

---

## CR-008 — Player achievements and public player profile

**Reason:** No way for a player, or anyone else, to see a player's tournament-win
history. Achievement data (which tournaments a player has won) existed implicitly in
`Standing`/`MatchResult` rows but required a manual join to surface.

**Added:**
- `GET /players/{id}/profile` (public) — returns the player's `id`, `name`, `team_id`,
  `team_name`, and an `achievements` list of `COMPLETED` tournaments they won (as
  round-robin standings leader, or as the recorded knockout-final winner)
- `get_player_achievements()` in `app/services/participant_service.py`

**Known limitation, documented rather than silently incorrect:** team-based wins are
matched against the player's **current** team, not the roster at the time the
tournament was won — the system does not track historical team membership. A player
who has since left a winning team loses credit for that win; a player who joins a team
after it won something gains credit retroactively. A fully correct implementation
would require snapshotting team membership at tournament-registration time, which is
out of scope for this version.

**Affected SRS sections:** §12.3 (Player Achievements & Public Profile), §1.3 (Out of
Scope — historical team-roster tracking)

**Status:** Approved and implemented.

---

## CR-007 — Player self-registration restricted to INDIVIDUAL tournaments only

**Reason:** CR-002 established that players self-register via `POST
/auth/register`, but left the per-tournament registration rule under-specified: it was
possible to read the original design as allowing a player to self-register into a
`TEAM` tournament, which doesn't make sense without a "team captain" concept in the
data model (no single player can commit an entire team's roster on the team's behalf).

**Clarified rule (§7.5):**
- Organizers may register a `player_id` or `team_id` (matching the tournament's
  `participant_type`) on behalf of anyone, into any tournament they own.
- Players may self-register **only their own** `player_id` (verified server-side), and
  **only into `INDIVIDUAL` tournaments**. Attempting to self-register into a `TEAM`
  tournament, or to submit a `team_id` at all, returns `403`.

Team registration therefore remains organizer-managed in all cases.

**Added:** Role/participant-type branch in `register_participant()`
(`app/services/participant_service.py`)

**Affected SRS sections:** §7.5 (Per-Tournament Participant Registration Rules)

**Status:** Approved and implemented.

---

## CR-006 — Minimum two participants required to start a tournament

**Reason:** `REGISTRATION_OPEN → ONGOING` had no participant-count check. A tournament
could be started with zero or one registered participants, at which point fixture
generation (which independently requires ≥2 participants) would permanently fail —
leaving the tournament stuck `ONGOING` with no path to `COMPLETED`.

**Added:** Participant-count check in `advance_lifecycle()`
(`app/services/tournament_service.py`) when the target status is `ONGOING`; returns
`409 Conflict` with a descriptive message if fewer than two `TournamentParticipant`
rows exist.

**Affected SRS sections:** §6.3 (Minimum Participant Requirement)

**Status:** Approved and implemented.

---

## CR-005 — Match scheduling requirements

**Reason:** Matches could have a result submitted with no venue or scheduled time ever
assigned, and there was no way to set either through the API — venue/time only existed
as nullable columns with no corresponding endpoint. Separately, nothing prevented
scheduling a match in the past.

**Added:**
- `PUT /matches/{id}/schedule` (organizer, owner) — sets `venue_id` and/or
  `scheduled_at`; rejects a `scheduled_at` in the past (server-side UTC clock) with
  `400`; rejects an unknown `venue_id` with `404`
- `GET /matches/{id}` (public) — standalone single-match lookup, needed by clients
  driving the new scheduling workflow without fetching a whole tournament's match list
- Result-submission guard in `submit_result()` (`app/services/result_service.py`): a
  match with a null `venue_id` or `scheduled_at` returns `409 Conflict` on
  `POST /matches/{id}/result`. Does not apply to knockout byes, which are
  auto-completed during fixture generation and never pass through this path.

**Affected SRS sections:** §8.2 (Match — CR-005 fields), §11.7 (Match Scheduling), §12.4
(error-code table addition: `409` — unscheduled match)

**Status:** Approved and implemented.

---

## CR-004 — Post-build hardening

**Reason:** Gaps identified during a full codebase review conducted after the core
functional requirements (FR-01–FR-07) were complete: any organizer could manage any
tournament regardless of ownership, several list/detail responses leaked raw internal
IDs instead of names, standings were invisible until the first result was submitted,
no single-item GET existed for Player/Team, no endpoint existed to update a player's
team or remove a participant, CORS was wide open (`origins: "*"`), score
serialization was inconsistent (string vs. number), and no foreign-key column had an
explicit index.

**Added:**
- Organizer-ownership checks (`tournament.organizer_id == authenticated_user_id`) in
  `participant_service.py`, `fixture_service.py`, `result_service.py` — a mismatch
  returns `403`
- `get_participant_display()` helper, applied in `MatchSchema`, `MatchResultSchema`,
  `ParticipantSchema` so responses show a resolved name instead of a raw ID
- Standings backfill: `list_standings()` now creates a zero-value `Standing` row for
  every registered participant, so a participant appears in standings before their
  first match
- `GET /players/{id}`, `GET /teams/{id}` (single-item lookups)
- `PUT /players/{id}/team` (player self, or organizer, reassign or clear team
  affiliation) and `DELETE /tournaments/{id}/participants/{id}` (organizer, owner,
  only before `ONGOING`) — the latter also deletes any pre-existing `Standing` row for
  that participant, so a removed participant never lingers in the standings view
- `CORS_ORIGINS` env-driven allowlist, replacing the wide-open default
- Standardized score serialization on plain floats across `MatchResultSchema`,
  `StandingSchema`
- Explicit `index=True` on every foreign-key column across all models (migration
  `c49a02e1137e`), since PostgreSQL does not index foreign keys automatically
- `ON DELETE CASCADE` on `PasswordResetToken.user_id` and
  `EmailVerificationToken.user_id` (migration `eb030e9e4708`), found during the P2
  manual integration-testing pass when deleting a user raised a raw FK-violation error;
  folded into this CR as it's the same "hardening pass" category of fix
- `player_id`/`team_id` added to `StandingSchema` alongside the existing
  `participant_id`/`name`, matching the same linking pattern already applied to
  match and participant responses

**Affected SRS sections:** §2.3 (Ownership Enforcement), §7.3 (Participant Removal),
§7.4 (Player-Team Update), §8.3 (Indexes), §8.4 (Cascade Deletes)

**Status:** Approved and implemented.

---

## CR-003 — Auth hardening and pagination

**Date:** 2026-08-26
**Reason:** Gaps identified during a full codebase review: no logout/token revocation,
no password reset, no email verification, unbounded list endpoints, no rate limiting
on auth endpoints.

**Added:**
- JWT logout via server-side token blocklist (`TokenBlocklist`, keyed by `jti`, storing
  `expires_at` for future cleanup of naturally-expired entries)
- Password reset flow (`POST /auth/forgot-password`, `POST /auth/reset-password`) —
  previously issued unused tokens are invalidated when a new one is requested.
  Development mode exposes the raw token in the API response since no SMTP provider is
  configured; production would email it instead.
- Email verification (`is_verified` field on `User`, `GET /auth/verify-email`) — tracked
  but **not enforced**; login does not require a verified account. Same dev-only token
  exposure pattern as password reset.
- Rate limiting on `/auth/login` (5/minute) and `/auth/register` (initially 5/minute,
  see addendum below)
- Pagination on `GET /tournaments`, `GET /players`, `GET /teams` — the only system-wide
  unbounded lists. Tournament-scoped lists (participants, matches, standings) remain
  unpaginated by design, since they're naturally capped by tournament size.

**Explicitly out of scope:** account lockout after failed logins, real SMTP integration,
pagination on tournament-scoped endpoints.

**Response shape change:** `GET /tournaments`, `GET /players`, `GET /teams` now return
`{"items": [...], "page": N, "per_page": N, "total": N, "total_pages": N}` instead of a
bare array.

**Status:** Approved and implemented.

### Addendum (discovered during P2 integration testing, 2026-08-26)

Manual end-to-end testing of a realistic bulk-registration workflow (an organizer
registering several players in quick succession) hit the 5/minute rate limit on
`/auth/register`, which is unrealistically tight for that use case. **Register limit
raised to 20/minute.** `/auth/login` remains at 5/minute, since brute-force protection
on a single account's password is the actual threat model there, not bulk registration.

---

## CR-002 — Player self-registration with team creation/joining

**Date:** 2026-08-24
**Reason:** The original registration flow (`POST /auth/register`) only created a
`User` row. There was no way to create a `Player` or `Team` record through the API at
all — every test and manual workflow had to insert them directly via SQLAlchemy,
bypassing the API entirely. This meant a real user could never actually register as a
tournament participant through the system as built.

**Clarified registration model** (three-tier, as specified by the team):
1. **Guests** — browse everything, no account required (see CR-001).
2. **Players** — register via `POST /auth/register` with `role=PLAYER`. Must also
   specify `participation_type` (`INDIVIDUAL` or `TEAM`). If `TEAM`, must specify
   `team_option` (`NEW`, with a `team_name`, or `EXISTING`, with a `team_id`). A
   `Player` row is created automatically and linked to the new `User`, and to a `Team`
   if applicable.
3. **Organizers** — register via `POST /auth/register` with `role=ORGANIZER`. Cannot
   include any player/team fields — rejected with `400` if they do. Organizers never
   create `Player` or `Team` records themselves.

One email = one identity, enforced by the existing `User.email` unique constraint — no
additional work needed, since an email can't register as both an Organizer and a Player.

**Added:**
- Role-specific validation in `RegisterSchema` (`app/schemas/auth_schema.py`)
- Automatic `Player`/`Team` creation inside `register_user()` (`app/services/auth_service.py`)
- `GET /teams` (public, list) — lets a registering player browse existing teams to join

**Affected SRS sections:** §7 (Participation Model), §10 (Player)

**Status:** Approved and implemented.

---

## CR-001 — Public read access for guests

**Date:** 2026-08-23
**Reason:** Unauthenticated visitors should be able to browse tournaments, participants,
fixtures, results, and standings without an account. Login is required only for actions
(creating tournaments, registering as a participant, submitting results, managing
lifecycle).

**Affected SRS sections:** §6 (Actors), §37 (API)
**Affected design:** All GET endpoints are public; POST/PUT/DELETE remain
role-protected.
**Confirmed during discussion:** match result submission is organizer-only with no
player-submission path, consistent with the original SRS §6 listing of "submit match
results" solely under Organizer.

**Status:** Approved and implemented starting with Backend Phase 3 (Tournament/Venue
routes), applied retroactively as a design rule to all subsequent routes.

---