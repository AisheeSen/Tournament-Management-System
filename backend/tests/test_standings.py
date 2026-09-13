from app.extensions import db
from app.models import Player, Match, MatchParticipant


def register_and_login(client, email, role="ORGANIZER"):
    client.post("/api/v1/auth/register", json={
        "name": "U", "email": email, "password": "password123", "role": role,
    })
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": "password123"})
    return resp.json["access_token"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def setup_two_player_match(client, app, email):
    token = register_and_login(client, email)
    tournament = client.post(
        "/api/v1/tournaments",
        json={"name": "Standings Test", "sport": "Chess", "format": "ROUND_ROBIN", "participant_type": "INDIVIDUAL"},
        headers=auth_headers(token),
    ).json
    client.post(f"/api/v1/tournaments/{tournament['id']}/open-registration", headers=auth_headers(token))

    with app.app_context():
        p1 = Player(name="Alpha")
        p2 = Player(name="Zeta")
        db.session.add_all([p1, p2])
        db.session.commit()
        p1_id, p2_id = p1.id, p2.id

    client.post(f"/api/v1/tournaments/{tournament['id']}/participants", json={"player_id": p1_id}, headers=auth_headers(token))
    client.post(f"/api/v1/tournaments/{tournament['id']}/participants", json={"player_id": p2_id}, headers=auth_headers(token))
    client.post(f"/api/v1/tournaments/{tournament['id']}/start", headers=auth_headers(token))
    client.post(f"/api/v1/tournaments/{tournament['id']}/fixtures", headers=auth_headers(token))

    with app.app_context():
        match = Match.query.filter_by(tournament_id=tournament["id"]).first()
        match_id = match.id
        mps = MatchParticipant.query.filter_by(match_id=match_id).all()
        participant_ids = [mp.participant_id for mp in mps]

    venue_resp = client.post(
        "/api/v1/venues", json={"name": "Test Venue", "location": "Test City"}, headers=auth_headers(token)
    )
    client.put(
        f"/api/v1/matches/{match_id}/schedule",
        json={"venue_id": venue_resp.json["id"], "scheduled_at": "2030-01-01T10:00:00+00:00"},
        headers=auth_headers(token),
    )

    return token, tournament["id"], match_id, participant_ids


def test_guest_can_view_standings_without_login(client, app):
    token, tid, match_id, pids = setup_two_player_match(client, app, "st1@example.com")
    resp = client.get(f"/api/v1/tournaments/{tid}/standings")
    assert resp.status_code == 200


def test_win_updates_points_and_wl_record(client, app):
    token, tid, match_id, pids = setup_two_player_match(client, app, "st2@example.com")
    client.post(
        f"/api/v1/matches/{match_id}/result",
        json={
            "result_type": "WIN",
            "winner_participant_id": pids[0],
            "scores": [
                {"participant_id": pids[0], "score": 3},
                {"participant_id": pids[1], "score": 1},
            ],
        },
        headers=auth_headers(token),
    )

    resp = client.get(f"/api/v1/tournaments/{tid}/standings")
    standings_by_pid = {row["participant_id"]: row for row in resp.json}

    winner = standings_by_pid[pids[0]]
    loser = standings_by_pid[pids[1]]

    assert winner["points"] == 3
    assert winner["won"] == 1
    assert winner["played"] == 1
    assert winner["score_difference"] == 2.0  # 3 - 1

    assert loser["points"] == 0
    assert loser["lost"] == 1
    assert loser["score_difference"] == -2.0


def test_draw_updates_both_sides(client, app):
    token, tid, match_id, pids = setup_two_player_match(client, app, "st3@example.com")
    client.post(
        f"/api/v1/matches/{match_id}/result",
        json={
            "result_type": "DRAW",
            "scores": [
                {"participant_id": pids[0], "score": 2},
                {"participant_id": pids[1], "score": 2},
            ],
        },
        headers=auth_headers(token),
    )

    resp = client.get(f"/api/v1/tournaments/{tid}/standings")
    for row in resp.json:
        assert row["points"] == 1
        assert row["drawn"] == 1
        assert row["score_difference"] == 0.0


def test_standings_ranking_order(client, app):
    token, tid, match_id, pids = setup_two_player_match(client, app, "st4@example.com")
    client.post(
        f"/api/v1/matches/{match_id}/result",
        json={
            "result_type": "WIN",
            "winner_participant_id": pids[0],
            "scores": [
                {"participant_id": pids[0], "score": 5},
                {"participant_id": pids[1], "score": 0},
            ],
        },
        headers=auth_headers(token),
    )

    resp = client.get(f"/api/v1/tournaments/{tid}/standings")
    # winner (3 points) should rank above loser (0 points)
    assert resp.json[0]["participant_id"] == pids[0]
    assert resp.json[1]["participant_id"] == pids[1]


def test_both_participants_updated_atomically(client, app):
    """Result submission and standings update happen in the same transaction —
    a valid result should never leave one participant's Standing updated
    without the other's."""
    token, tid, match_id, pids = setup_two_player_match(client, app, "st5@example.com")
    client.post(
        f"/api/v1/matches/{match_id}/result",
        json={
            "result_type": "WIN",
            "winner_participant_id": pids[0],
            "scores": [
                {"participant_id": pids[0], "score": 1},
                {"participant_id": pids[1], "score": 0},
            ],
        },
        headers=auth_headers(token),
    )

    resp = client.get(f"/api/v1/tournaments/{tid}/standings")
    assert len(resp.json) == 2
    assert all(row["played"] == 1 for row in resp.json)

def test_standings_show_all_participants_before_any_results(client, app):
    token, tid, match_id, pids = setup_two_player_match(client, app, "stzero@example.com")
    resp = client.get(f"/api/v1/tournaments/{tid}/standings")
    assert resp.status_code == 200
    assert len(resp.json) == 2
    for row in resp.json:
        assert row["played"] == 0
        assert row["points"] == 0

def test_standings_include_player_id_for_linking(client, app):
    token, tid, match_id, pids = setup_two_player_match(client, app, "linkcheck@example.com")
    resp = client.get(f"/api/v1/tournaments/{tid}/standings")
    assert resp.status_code == 200
    assert all("player_id" in row for row in resp.json)