from datetime import datetime, timezone

from app.extensions import db


class TournamentParticipantMember(db.Model):
    """Snapshot of which players were on a team's roster at the moment that team
    registered for a tournament. This is what makes achievement attribution
    correct even after a player later joins or leaves the team — without this,
    a player's team-win history would silently rewrite itself every time they
    changed teams."""
    __tablename__ = "tournament_participant_members"

    id = db.Column(db.Integer, primary_key=True)
    tournament_participant_id = db.Column(
        db.Integer, db.ForeignKey("tournament_participants.id"), nullable=False, index=True
    )
    player_id = db.Column(db.Integer, db.ForeignKey("players.id"), nullable=False, index=True)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    tournament_participant = db.relationship("TournamentParticipant", foreign_keys=[tournament_participant_id])
    player = db.relationship("Player", foreign_keys=[player_id])

    __table_args__ = (
        db.UniqueConstraint("tournament_participant_id", "player_id", name="uq_tp_member"),
    )