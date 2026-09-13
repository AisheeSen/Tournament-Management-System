from flask import Blueprint, jsonify

from app.schemas.standing_schema import StandingSchema
from app.services.standings_service import list_standings
from app.services.tournament_service import TournamentError

standings_bp = Blueprint("standings", __name__)

standing_schema = StandingSchema()


@standings_bp.route("/tournaments/<int:tournament_id>/standings", methods=["GET"])
def get_standings(tournament_id):
    try:
        rows = list_standings(tournament_id)
    except TournamentError as err:
        return jsonify({"error": err.message}), err.status_code

    payload = []
    for standing, total_score, name in rows:
        payload.append(standing_schema.dump({
            "participant_id": standing.participant_id,
            "player_id": standing.participant.player_id,
            "team_id": standing.participant.team_id,
            "name": name,
            "played": standing.played,
            "won": standing.won,
            "drawn": standing.drawn,
            "lost": standing.lost,
            "points": standing.points,
            "score_difference": float(standing.score_difference or 0),
            "total_score": total_score,
        }))
    return jsonify(payload), 200