# Traceability Matrix

This matrix links each functional requirement to its design artifact, implementation
file, and test file, per SRS §43. Updated as each feature is completed.

**Last synced with:** `docs/SRS.md`, "Last updated: 2026-09-16 (incorporates CR-001
through CR-009)."

**Status legend:** ✅ Done · 🟡 In progress · ⬜ Not started

---

## Core Functional Requirements

| ID | Requirement | Design Artifact | Implementation | Test | Status |
|---|---|---|---|---|---|
| FR-01 | User registration & login | Auth sequence diagram (pending, §44) | `app/services/auth_service.py`, `app/routes/auth_routes.py`, `app/schemas/auth_schema.py` | `tests/test_auth.py` | ✅ |
| FR-02 | Create & configure tournament | Use-case diagram (pending, §44) | `app/services/tournament_service.py`, `app/routes/tournament_routes.py` | `tests/test_tournaments.py` | ✅ |
| FR-02a | Tournament lifecycle transitions | Activity diagram: lifecycle (pending, §44) | `advance_lifecycle()` in `tournament_service.py` | `tests/test_tournaments.py` | ✅ |
| FR-02b | Config locking after DRAFT | — | `update_tournament()` in `tournament_service.py` | `tests/test_tournaments.py` | ✅ |
| — | Venue management | — | `app/models/venue.py`, `app/routes/venue_routes.py` | `tests/test_venues.py` | ✅ |
| FR-03 | Register participant (team or individual) | ER diagram (pending, §44) | `app/services/participant_service.py`, `app/routes/participant_routes.py` | `tests/test_participants.py` | ✅ |
| FR-04 | Generate fixtures (round-robin & knockout, incl. byes) | Sequence diagram: fixture generation (pending, §44) | `app/services/fixture_service.py`, `app/routes/match_routes.py` | `tests/test_fixtures.py` | ✅ |
| FR-05 | Submit match result (organizer-only, transactional) | Sequence diagram: result → standings (pending, §44) | `app/services/result_service.py`, `app/routes/match_routes.py` | `tests/test_results.py` | ✅ |
| FR-06 | Compute & display standings | Class diagram (pending, §44) | `app/services/standings_service.py`, `app/routes/standings_routes.py` | `tests/test_standings.py` | ✅ |
| FR-07 | Knockout progression & automatic completion | Activity diagram: knockout (pending, §44) | `app/services/knockout_service.py` | `tests/test_knockout.py` | ✅ |

## Change Requests

| ID | Requirement | Implementation | Test | Status |
|---|---|---|---|---|
| CR-001 | Guest (unauthenticated) read access to all tournament data | No auth decorator on any GET route across all blueprints | Guest-access tests across all test files | ✅ |
| CR-002 | Player self-registration (individual/team, new/existing team); organizers barred from player/team fields | `auth_service.py::register_user()`, `auth_schema.py` role-specific validation, `team_routes.py`, `player_routes.py` | `test_auth.py` (7 tests) | ✅ |
| CR-003 | Logout/token revocation, password reset, email verification, pagination, rate limiting (register limit raised 5→20/min post-integration-testing) | `token_blocklist.py`, `password_reset_token.py`, `email_verification_token.py`, `utils/pagination.py`, `extensions.py` (limiter) | New tests across `test_auth.py`; pagination-shape fixes in `test_tournaments.py` | ✅ |
| CR-004 | Post-build hardening: ownership checks, FK indexes, cascade deletes, standings backfill/cleanup, single-item GET routes, player-team update, CORS allowlist | See itemized breakdown in **Post-Build Hardening** table below | See itemized breakdown below | ✅ |
| CR-005 | Match scheduling: venue + time required before result entry, past-date rejection, standalone `GET /matches/{id}` | `fixture_service.py::update_match_schedule()`, `match_routes.py::put_match_schedule()` (`PUT /matches/{id}/schedule`), `match_routes.py::get_match()` (`GET /matches/{id}`); schedule presence checked in `result_service.py::submit_result()` | `test_fixtures.py::test_organizer_can_schedule_match_venue_and_time`, `::test_other_organizer_cannot_schedule_match`, `::test_get_single_match`, `::test_get_nonexistent_match_returns_404`; `test_gaps_round2.py::test_cannot_schedule_match_in_past`, `::test_cannot_submit_result_without_schedule` | ✅ |
| CR-006 | Minimum two participants required before `REGISTRATION_OPEN → ONGOING` | `tournament_service.py::advance_lifecycle()` — participant-count check when `target_status == ONGOING` | `test_tournaments.py::test_cannot_start_with_fewer_than_two_participants` | ✅ |
| CR-007 | Player self-registration restricted to `INDIVIDUAL` tournaments only; team registration remains organizer-only in all cases | `participant_service.py::register_participant()` — `PLAYER` role branch (self-only, `INDIVIDUAL`-only, no `team_id`) | `test_participants.py::test_player_can_self_register_for_individual_tournament`, `::test_player_cannot_self_register_for_team_tournament`, `::test_player_cannot_register_someone_else`, `::test_player_cannot_register_a_team` | ✅ |
| CR-008 | Player achievements and public player profile | `participant_service.py::get_player_achievements()`, `player_routes.py::get_player_profile()` (`GET /players/{id}/profile`) | `test_gaps_round2.py::test_player_profile_shows_achievement_after_winning` | ✅ |
| CR-009 | Roster-snapshot achievement attribution: team wins matched against who was actually on the roster at registration time, not the player's current team; adds `GET /teams/{id}/achievements` | `models/tournament_participant_member.py` (new table, migration `baf2dc1bd3bd`), `participant_service.py::register_participant()` (snapshot write), `::get_player_achievements()` (rewritten — dict shape `{individual, current_team, previous_team}`), `::get_team_achievements()` (new), `team_routes.py::get_team_achievements_route()` | `test_gaps_round2.py::test_achievement_includes_participant_type_and_team_name`, `::test_team_switch_reclassifies_achievement_correctly` | ✅ |

## Post-Build Hardening (Codebase Gap Review) — detail for CR-004

| # | Issue | Fix | Test | Status |
|---|---|---|---|---|
| 1 | No organizer-ownership check on participant registration, fixture generation, result submission (any organizer could manage any tournament) | Added `organizer_id` check in `participant_service.py`, `fixture_service.py`, `result_service.py` | `test_other_organizer_cannot_register_participants`, `test_other_organizer_cannot_generate_fixtures`, `test_other_organizer_cannot_submit_result` | ✅ |
| 2 | Match/result responses showed raw participant IDs, not names | `get_participant_display()` helper; `MatchSchema`, `MatchResultSchema` updated | `test_matches_include_participant_names` | ✅ |
| 3 | Participant list showed raw IDs, not names | `ParticipantSchema.name` added | `test_participant_list_includes_names` | ✅ |
| 4 | Standings only appeared after first result (registered-but-unplayed participants invisible) | `list_standings()` now backfills a zero Standing row for every registered participant | `test_standings_show_all_participants_before_any_results` | ✅ |
| 5 | No single-item GET for Player/Team | `GET /players/{id}`, `GET /teams/{id}` added | `test_guest_can_view_single_player_without_login`, `test_guest_can_view_single_team_without_login` + 404 cases | ✅ |
| 6 | No way to update a player's team or remove a participant before tournament start | `PUT /players/{id}/team`, `DELETE /tournaments/{id}/participants/{id}` | `test_player_team_update.py`, `test_participant_removal.py` (12 tests total) | ✅ |
| 7 | CORS wide open (`origins: "*"`) | `CORS_ORIGINS` env-driven allowlist | Manual verification | ✅ |
| 8 | Inconsistent score serialization (string vs number) | Standardized on plain floats across `MatchResultSchema`, `StandingSchema` | Covered by existing result/standings tests | ✅ |
| 9 | No explicit indexes on FK columns | `index=True` added to all FK columns across 8 models; migration `c49a02e1137e` | N/A (performance, not behavior) | ✅ |
| 10 | Standings responses lacked `player_id`/`team_id`, so names couldn't be linked to profiles/rosters the way match/participant names could | `player_id`/`team_id` added to `StandingSchema`, sourced via `standing.participant` | `test_standings_include_player_id_for_linking` | ✅ |

## P1 — Polish (SRS §38, §39)

| Item | Outcome |
|---|---|
| Error-handling audit (all 6 route files) | No inconsistencies found — every route already followed consistent `{"error": "..."}` shape and correct status codes |
| Security checklist | `.env` never committed (verified via `git log`), no `__pycache__` tracked, no hardcoded credentials, `SECRET_KEY` fallback removed |

**Status:** ✅ Complete

## P2 — Integration Testing

Two full end-to-end scenarios run against the live dev server via the actual HTTP API (not the pytest test client), documented in `backend/scripts/`:

- **Scenario A** (`scripts/scenario_a.ps1`) — 5-player round-robin tournament, full lifecycle: registration → open-registration → participant registration → start → fixture generation (10 matches) → result submission → automatic standings computation → automatic completion → guest read access at every stage. **Result: fully correct**, standings math verified by hand.
- **Scenario B** (`scripts/scenario_b.ps1`) — 6-player knockout tournament (8-slot bracket, 2 byes): bye auto-completion, Round 1 → Round 2 → Final winner advancement, champion determination, automatic completion, no third-place match generated. **Result: fully correct.**

**Bugs found and fixed during integration testing** (none of these were caught by the
unit/route-level pytest suite as it stood at the time, since all of them only surface
when exercised through a real multi-step API flow with real data). The first is now
tracked formally under CR-004; the second under the CR-003 addendum in
`docs/change-log.md`:

| Bug | Fix |
|---|---|
| `email_verification_tokens.user_id` and `password_reset_tokens.user_id` had no `ON DELETE CASCADE`, blocking manual user cleanup with a raw FK violation | Added `ondelete="CASCADE"` to both FKs; migration `eb030e9e4708` |
| `/auth/register` rate limit (5/minute) was too aggressive for realistic bulk player registration by an organizer | Raised to 20/minute; `/auth/login` unchanged at 5/minute |
| Auto-generated migration `downgrade()` for the cascade fix referenced an unnamed constraint (`None`), causing a `CompileError` if ever rolled back | Explicitly named both FK constraints in `upgrade()`/`downgrade()` |

**Status:** ✅ Complete

---

## Summary

All functional requirements (FR-01–FR-07) and all nine change requests (CR-001–CR-009)
are complete. **116 automated tests passing**, plus 2 manual end-to-end integration
scenarios verified against the live API. Known limitations (in-memory rate limiting,
unscheduled blocklist purging, dev-only token exposure) are documented in
`docs/SRS.md` §13 rather than treated as open defects. The previously-documented
non-historical team-roster achievement limitation was resolved by CR-009.

## Remaining before final submission

- **Diagrams (§17):** `docs/SRS.md` now references `docs/diagrams/context-diagram.svg`,
  `docs/diagrams/er-diagram.svg`, and related sequence/activity diagrams as the
  canonical source, but no `docs/diagrams/` directory exists in the repository yet —
  this is the one item in the SRS that is currently aspirational rather than reflecting
  the actual repo state. Schema and service interactions are fully finalized, so
  nothing blocks drawing these.
- **Frontend integration (P3):** ✅ Done since this matrix was last updated — a full
  React (Vite) frontend now exists under `frontend/src/`, covering guest browsing,
  player/organizer auth, tournament management, participant registration, fixture and
  standings display, and match result entry (23 pages, 6 API modules, shared
  `AuthContext`). Not yet broken out into its own FR-tracked rows in this matrix.
- **Frontend consistency regression (unrelated to CR-009):** a prior pass added a
  shared `ParticipantLink` component so player/team names were clickable everywhere
  in the frontend. That shared component has since been removed; most pages still
  link names but via duplicated per-file logic instead of the shared component, and
  two spots lost the link entirely — `ChampionBanner.jsx`'s champion name (now plain
  text, and the round-robin branch no longer even carries `player_id`/`team_id` to
  link with) and `TournamentManagementPage.jsx`'s "Registered participants" list. Not
  a backend/requirements issue, but worth a cleanup pass before final submission.