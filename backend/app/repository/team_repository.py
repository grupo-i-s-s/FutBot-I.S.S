from sqlalchemy.orm import Session
from app.models.team_model import DefaultTeam


def get_by_club(db: Session, club_id: int) -> DefaultTeam | None:
    return db.get(DefaultTeam, club_id)


def save(db: Session, club_id: int, line_up: dict) -> DefaultTeam:
    team = get_by_club(db, club_id)

    if team is None:
        team = DefaultTeam(
            club_id=club_id,
            line_up=line_up,
        )
        db.add(team)
    else:
        team.line_up = line_up

    db.flush()
    return team