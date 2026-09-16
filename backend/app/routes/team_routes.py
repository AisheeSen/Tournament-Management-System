from flask import Blueprint, jsonify

from app.utils.pagination import paginate_query
from app.models import Team
from app.extensions import db
from app.services.participant_service import get_team_achievements

team_bp = Blueprint("team", __name__)


@team_bp.route("/teams", methods=["GET"])
def get_teams():
    result = paginate_query(Team.query.order_by(Team.name))
    result["items"] = [{"id": t.id, "name": t.name} for t in result["items"]]
    return jsonify(result), 200


@team_bp.route("/teams/<int:team_id>", methods=["GET"])
def get_team(team_id):
    team = db.session.get(Team, team_id)
    if not team:
        return jsonify({"error": "Team not found"}), 404
    return jsonify({"id": team.id, "name": team.name}), 200

@team_bp.route("/teams/<int:team_id>/achievements", methods=["GET"])
def get_team_achievements_route(team_id):
    team = Team.query.get(team_id)
    if not team:
        return jsonify({"error": "Team not found"}), 404
    achievements = get_team_achievements(team_id)
    return jsonify({"team_id": team.id, "team_name": team.name, "achievements": achievements}), 200