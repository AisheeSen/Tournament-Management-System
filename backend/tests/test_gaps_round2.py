def register_and_login(client, email, role="ORGANIZER"):
    payload = {"name": "U", "email": email, "password": "password123", "role": role}
    if role == "PLAYER":
        payload["participation_type"] = "INDIVIDUAL"
    client.post("/api/v1/auth/register", json=payload)
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": "password123"})
    return resp.json["access_token"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_cannot_schedule_match_in_past(client, app):
    from app.models import Player
    from app.extensions import db

    token = register_and_login(client, "pastdate@example.com")
    tournament = client.post(
        "/api/v1/tournaments",
        json={"name": "Past Date Test", "sport": "Chess", "format": "ROUND_ROBIN", "participant_type": "INDIVIDUAL"},
        headers=auth_headers(token),
    ).json
    client.post(f"/api/v1/tournaments/{tournament['id']}/open-registration", headers=auth_headers(token))

    with app.app_context():
        p1 = Player(name="P1")
        p2 = Player(name="P2")
        db.session.add_all([p1, p2])
        db.session.commit()
        p1_id, p2_id = p1.id, p2.id

    client.post(f"/api/v1/tournaments/{tournament['id']}/participants", json={"player_id": p1_id}, headers=auth_headers(token))
    client.post(f"/api/v1/tournaments/{tournament['id']}/participants", json={"player_id": p2_id}, headers=auth_headers(token))
    client.post(f"/api/v1/tournaments/{tournament['id']}/start", headers=auth_headers(token))
    matches = client.post(f"/api/v1/tournaments/{tournament['id']}/fixtures", headers=auth_headers(token)).json
    match_id = matches[0]["id"]

    resp = client.put(
        f"/api/v1/matches/{match_id}/schedule",
        json={"scheduled_at": "2020-01-01T10:00:00+00:00"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 400


def test_cannot_submit_result_without_schedule(client, app):
    from app.models import Player
    from app.extensions import db

    token = register_and_login(client, "noschedule@example.com")
    tournament = client.post(
        "/api/v1/tournaments",
        json={"name": "No Schedule Test", "sport": "Chess", "format": "ROUND_ROBIN", "participant_type": "INDIVIDUAL"},
        headers=auth_headers(token),
    ).json
    client.post(f"/api/v1/tournaments/{tournament['id']}/open-registration", headers=auth_headers(token))

    with app.app_context():
        p1 = Player(name="P1")
        p2 = Player(name="P2")
        db.session.add_all([p1, p2])
        db.session.commit()
        p1_id, p2_id = p1.id, p2.id

    client.post(f"/api/v1/tournaments/{tournament['id']}/participants", json={"player_id": p1_id}, headers=auth_headers(token))
    client.post(f"/api/v1/tournaments/{tournament['id']}/participants", json={"player_id": p2_id}, headers=auth_headers(token))
    client.post(f"/api/v1/tournaments/{tournament['id']}/start", headers=auth_headers(token))
    matches = client.post(f"/api/v1/tournaments/{tournament['id']}/fixtures", headers=auth_headers(token)).json
    match_id = matches[0]["id"]
    participant_ids = [p["id"] for p in matches[0]["participants"]]

    resp = client.post(
        f"/api/v1/matches/{match_id}/result",
        json={
            "result_type": "WIN",
            "winner_participant_id": participant_ids[0],
            "scores": [
                {"participant_id": participant_ids[0], "score": 1},
                {"participant_id": participant_ids[1], "score": 0},
            ],
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 409


def test_player_profile_shows_achievement_after_winning(client, app):
    from app.models import Player
    from app.extensions import db

    token = register_and_login(client, "achieveorg@example.com")
    tournament = client.post(
        "/api/v1/tournaments",
        json={"name": "Achievement Test", "sport": "Chess", "format": "ROUND_ROBIN", "participant_type": "INDIVIDUAL"},
        headers=auth_headers(token),
    ).json
    client.post(f"/api/v1/tournaments/{tournament['id']}/open-registration", headers=auth_headers(token))

    with app.app_context():
        p1 = Player(name="Winner Player")
        p2 = Player(name="Loser Player")
        db.session.add_all([p1, p2])
        db.session.commit()
        p1_id, p2_id = p1.id, p2.id

    client.post(f"/api/v1/tournaments/{tournament['id']}/participants", json={"player_id": p1_id}, headers=auth_headers(token))
    client.post(f"/api/v1/tournaments/{tournament['id']}/participants", json={"player_id": p2_id}, headers=auth_headers(token))
    client.post(f"/api/v1/tournaments/{tournament['id']}/start", headers=auth_headers(token))
    matches = client.post(f"/api/v1/tournaments/{tournament['id']}/fixtures", headers=auth_headers(token)).json
    match = matches[0]
    participant_ids = [p["id"] for p in match["participants"]]

    venue_resp = client.post("/api/v1/venues", json={"name": "V", "location": "L"}, headers=auth_headers(token))
    client.put(
        f"/api/v1/matches/{match['id']}/schedule",
        json={"venue_id": venue_resp.json["id"], "scheduled_at": "2030-01-01T10:00:00+00:00"},
        headers=auth_headers(token),
    )

    p1_participant_id = next(p["id"] for p in match["participants"] if p["player_id"] == p1_id)
    p2_participant_id = next(p["id"] for p in match["participants"] if p["player_id"] == p2_id)

    client.post(
        f"/api/v1/matches/{match['id']}/result",
        json={
            "result_type": "WIN",
            "winner_participant_id": p1_participant_id,
            "scores": [
                {"participant_id": p1_participant_id, "score": 1},
                {"participant_id": p2_participant_id, "score": 0},
            ],
        },
        headers=auth_headers(token),
    )

    resp = client.get(f"/api/v1/players/{p1_id}/profile")
    assert resp.status_code == 200
    assert len(resp.json["achievements"]) == 1
    assert resp.json["achievements"][0]["tournament_name"] == "Achievement Test"

def test_achievement_includes_participant_type_and_team_name(client, app):
    from app.models import Player, Team
    from app.extensions import db

    org_token = register_and_login(client, "teamachieve@example.com")
    tournament = client.post(
        "/api/v1/tournaments",
        json={"name": "Team Achievement Test", "sport": "Football", "format": "ROUND_ROBIN", "participant_type": "TEAM"},
        headers=auth_headers(org_token),
    ).json
    client.post(f"/api/v1/tournaments/{tournament['id']}/open-registration", headers=auth_headers(org_token))

    with app.app_context():
        team_a = Team(name="Falcons")
        team_b = Team(name="Ravens")
        db.session.add_all([team_a, team_b])
        db.session.commit()
        team_a_id, team_b_id = team_a.id, team_b.id
        p1 = Player(name="P1", team_id=team_a_id)
        db.session.add(p1)
        db.session.commit()
        p1_id = p1.id

    client.post(f"/api/v1/tournaments/{tournament['id']}/participants", json={"team_id": team_a_id}, headers=auth_headers(org_token))
    client.post(f"/api/v1/tournaments/{tournament['id']}/participants", json={"team_id": team_b_id}, headers=auth_headers(org_token))
    client.post(f"/api/v1/tournaments/{tournament['id']}/start", headers=auth_headers(org_token))
    matches = client.post(f"/api/v1/tournaments/{tournament['id']}/fixtures", headers=auth_headers(org_token)).json
    match = matches[0]
    participant_ids = [p["id"] for p in match["participants"]]

    venue_resp = client.post("/api/v1/venues", json={"name": "TA Venue", "location": "L"}, headers=auth_headers(org_token))
    client.put(
        f"/api/v1/matches/{match['id']}/schedule",
        json={"venue_id": venue_resp.json["id"], "scheduled_at": "2030-01-01T10:00:00+00:00"},
        headers=auth_headers(org_token),
    )
    winner_pid = next(p["id"] for p in match["participants"] if p["team_id"] == team_a_id)
    loser_pid = next(p["id"] for p in match["participants"] if p["team_id"] == team_b_id)
    client.post(
        f"/api/v1/matches/{match['id']}/result",
        json={
            "result_type": "WIN",
            "winner_participant_id": winner_pid,
            "scores": [
                {"participant_id": winner_pid, "score": 2},
                {"participant_id": loser_pid, "score": 0},
            ],
        },
        headers=auth_headers(org_token),
    )

    resp = client.get(f"/api/v1/players/{p1_id}/profile")
    assert resp.status_code == 200
    achievement = resp.json["achievements"][0]
    assert achievement["participant_type"] == "TEAM"
    assert achievement["team_name"] == "Falcons"