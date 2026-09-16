from app.extensions import db
from app.models import Participant, TournamentParticipant, Player, Team
from app.constants.enums import ParticipationType, TournamentStatus
from app.services.tournament_service import get_tournament_or_404, TournamentError

def _compute_tournament_winner_participant_id(tournament):
    from app.models import Match, MatchResult
    from app.constants.enums import TournamentFormat

    if tournament.format == TournamentFormat.ROUND_ROBIN:
        from app.services.standings_service import list_standings
        standings = list_standings(tournament.id)
        if standings:
            return standings[0][0].participant_id
        return None

    import re
    matches = Match.query.filter_by(tournament_id=tournament.id).all()
    if not matches:
        return None

    def round_num(m):
        mo = re.match(r"Round (\d+)", m.round)
        return int(mo.group(1)) if mo else 0

    final_round = max(round_num(m) for m in matches)
    final_matches = [m for m in matches if round_num(m) == final_round]
    if final_matches:
        result = MatchResult.query.filter_by(match_id=final_matches[0].id).first()
        if result:
            return result.winner_participant_id
    return None

def get_participant_display(participant) -> dict:
    if participant is None:
        return {"id": None, "type": None, "name": None, "player_id": None, "team_id": None}
    if participant.player_id is not None:
        player = db.session.get(Player, participant.player_id)
        return {
            "id": participant.id, "type": "INDIVIDUAL",
            "name": player.name if player else None,
            "player_id": participant.player_id, "team_id": None,
        }
    if participant.team_id is not None:
        team = db.session.get(Team, participant.team_id)
        return {
            "id": participant.id, "type": "TEAM",
            "name": team.name if team else None,
            "player_id": None, "team_id": participant.team_id,
        }
    return {"id": participant.id, "type": None, "name": None, "player_id": None, "team_id": None}
class ParticipantError(Exception):
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

def register_participant(tournament_id: int, requester_user_id: int, requester_role: str,
                          player_id: int = None, team_id: int = None) -> TournamentParticipant:
    if (player_id is None) == (team_id is None):
        raise ParticipantError("Exactly one of player_id or team_id must be provided")

    tournament = get_tournament_or_404(tournament_id)

    if tournament.status != TournamentStatus.REGISTRATION_OPEN:
        raise ParticipantError(
            "Registration is not open for this tournament", status_code=409
        )

    if requester_role == "ORGANIZER":
        if tournament.organizer_id != requester_user_id:
            raise ParticipantError(
                "Only the owning organizer can register participants for this tournament",
                status_code=403,
            )
    elif requester_role == "PLAYER":
        # Players may only self-register, and only into INDIVIDUAL tournaments.
        if tournament.participant_type != ParticipationType.INDIVIDUAL:
            raise ParticipantError(
                "Players cannot self-register for team tournaments; contact the organizer",
                status_code=403,
            )
        if team_id is not None:
            raise ParticipantError("Players cannot register a team", status_code=403)

        from app.models import Player
        requesting_player = Player.query.filter_by(user_id=requester_user_id).first()
        if not requesting_player or requesting_player.id != player_id:
            raise ParticipantError("Players may only register themselves", status_code=403)
    else:
        raise ParticipantError("Unauthorized", status_code=403)

    if tournament.participant_type == ParticipationType.TEAM and team_id is None:
        raise ParticipantError(
            "This tournament requires team participants, not individual players", status_code=400
        )
    if tournament.participant_type == ParticipationType.INDIVIDUAL and player_id is None:
        raise ParticipantError(
            "This tournament requires individual player participants, not teams", status_code=400
        )

    participant_type = ParticipationType.TEAM if team_id is not None else ParticipationType.INDIVIDUAL

    query = Participant.query.filter_by(type=participant_type)
    if player_id is not None:
        query = query.filter_by(player_id=player_id)
    else:
        query = query.filter_by(team_id=team_id)
    participant = query.first()

    if participant is None:
        participant = Participant(type=participant_type, player_id=player_id, team_id=team_id)
        db.session.add(participant)
        db.session.flush()

    existing_registration = TournamentParticipant.query.filter_by(
        tournament_id=tournament_id, participant_id=participant.id
    ).first()
    if existing_registration:
        raise ParticipantError(
            "This participant is already registered in this tournament", status_code=409
        )

    registration = TournamentParticipant(tournament_id=tournament_id, participant_id=participant.id)
    db.session.add(registration)
    db.session.flush()  # get registration.id before snapshotting members

    if participant_type == ParticipationType.TEAM:
        from app.models import Player, TournamentParticipantMember
        current_roster = Player.query.filter_by(team_id=team_id).all()
        for member_player in current_roster:
            db.session.add(TournamentParticipantMember(
                tournament_participant_id=registration.id,
                player_id=member_player.id,
            ))

    db.session.commit()
    return registration



def list_participants(tournament_id: int):
    get_tournament_or_404(tournament_id)  # 404 if tournament doesn't exist
    return (
        TournamentParticipant.query
        .filter_by(tournament_id=tournament_id)
        .order_by(TournamentParticipant.registered_at)
        .all()
    )

def remove_participant(tournament_id: int, participant_id: int, organizer_id: int):
    from app.models import Standing

    tournament = get_tournament_or_404(tournament_id)

    if tournament.organizer_id != organizer_id:
        raise ParticipantError(
            "Only the owning organizer can remove participants from this tournament",
            status_code=403,
        )

    if tournament.status not in (TournamentStatus.DRAFT, TournamentStatus.REGISTRATION_OPEN):
        raise ParticipantError(
            "Participants can only be removed before the tournament starts",
            status_code=409,
        )

    registration = TournamentParticipant.query.filter_by(
        tournament_id=tournament_id, participant_id=participant_id
    ).first()
    if not registration:
        raise ParticipantError("This participant is not registered in this tournament", status_code=404)

    db.session.delete(registration)

    stale_standing = Standing.query.filter_by(
        tournament_id=tournament_id, participant_id=participant_id
    ).first()
    if stale_standing:
        db.session.delete(stale_standing)

    db.session.commit()

def list_my_tournaments(user_id: int):
    """Returns tournaments the logged-in player is registered in, split into
    upcoming (not yet COMPLETED) and past (COMPLETED)."""
    from app.models import Player, Tournament

    player = Player.query.filter_by(user_id=user_id).first()
    if not player:
        return {"upcoming": [], "past": []}

    participant = Participant.query.filter_by(
        type=ParticipationType.INDIVIDUAL, player_id=player.id
    ).first()

    team_participant_ids = []
    if player.team_id:
        team_participant = Participant.query.filter_by(
            type=ParticipationType.TEAM, team_id=player.team_id
        ).first()
        if team_participant:
            team_participant_ids.append(team_participant.id)

    participant_ids = team_participant_ids
    if participant:
        participant_ids.append(participant.id)

    if not participant_ids:
        return {"upcoming": [], "past": []}

    registrations = TournamentParticipant.query.filter(
        TournamentParticipant.participant_id.in_(participant_ids)
    ).all()

    tournament_ids = [r.tournament_id for r in registrations]
    tournaments = Tournament.query.filter(Tournament.id.in_(tournament_ids)).all()

    upcoming = [t for t in tournaments if t.status != TournamentStatus.COMPLETED]
    past = [t for t in tournaments if t.status == TournamentStatus.COMPLETED]

    return {"upcoming": upcoming, "past": past}

def get_player_achievements(player_id: int) -> dict:
    """Returns {"individual": [...], "current_team": [...], "previous_team": [...]}.
    Team achievements are attributed only to tournaments the player actually had a
    roster-snapshot record for (see TournamentParticipantMember) — never to a team's
    wins the player wasn't actually part of at registration time."""
    from app.models import Tournament, Player, TournamentParticipant, TournamentParticipantMember, Team
    from app.constants.enums import TournamentStatus

    player = db.session.get(Player, player_id)
    if not player:
        return {"individual": [], "current_team": [], "previous_team": []}

    individual_achievements = []
    current_team_achievements = []
    previous_team_achievements = []

    individual_participant = Participant.query.filter_by(
        type=ParticipationType.INDIVIDUAL, player_id=player_id
    ).first()
    if individual_participant:
        registrations = TournamentParticipant.query.filter_by(
            participant_id=individual_participant.id
        ).all()
        for reg in registrations:
            tournament = db.session.get(Tournament, reg.tournament_id)
            if not tournament or tournament.status != TournamentStatus.COMPLETED:
                continue
            winner_id = _compute_tournament_winner_participant_id(tournament)
            if winner_id == individual_participant.id:
                individual_achievements.append({
                    "tournament_id": tournament.id,
                    "tournament_name": tournament.name,
                    "sport": tournament.sport,
                    "format": tournament.format.value,
                })

    member_rows = TournamentParticipantMember.query.filter_by(player_id=player_id).all()
    for member in member_rows:
        reg = db.session.get(TournamentParticipant, member.tournament_participant_id)
        if not reg:
            continue
        tournament = db.session.get(Tournament, reg.tournament_id)
        if not tournament or tournament.status != TournamentStatus.COMPLETED:
            continue
        winner_id = _compute_tournament_winner_participant_id(tournament)
        if winner_id != reg.participant_id:
            continue

        participant = db.session.get(Participant, reg.participant_id)
        if not participant or not participant.team_id:
            continue
        team = db.session.get(Team, participant.team_id)
        team_name = team.name if team else None

        achievement = {
            "tournament_id": tournament.id,
            "tournament_name": tournament.name,
            "sport": tournament.sport,
            "format": tournament.format.value,
            "team_id": participant.team_id,
            "team_name": team_name,
        }
        if player.team_id and participant.team_id == player.team_id:
            current_team_achievements.append(achievement)
        else:
            previous_team_achievements.append(achievement)

    return {
        "individual": individual_achievements,
        "current_team": current_team_achievements,
        "previous_team": previous_team_achievements,
    }


def get_team_achievements(team_id: int) -> list:
    """All completed tournaments this team's Participant record has won,
    regardless of current roster — used for the team's own achievement list."""
    from app.models import Tournament, TournamentParticipant
    from app.constants.enums import TournamentStatus

    participant = Participant.query.filter_by(type=ParticipationType.TEAM, team_id=team_id).first()
    if not participant:
        return []

    achievements = []
    registrations = TournamentParticipant.query.filter_by(participant_id=participant.id).all()
    for reg in registrations:
        tournament = db.session.get(Tournament, reg.tournament_id)
        if not tournament or tournament.status != TournamentStatus.COMPLETED:
            continue
        winner_id = _compute_tournament_winner_participant_id(tournament)
        if winner_id == participant.id:
            achievements.append({
                "tournament_id": tournament.id,
                "tournament_name": tournament.name,
                "sport": tournament.sport,
                "format": tournament.format.value,
            })
    return achievements