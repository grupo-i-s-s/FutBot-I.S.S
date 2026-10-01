from fastapi import HTTPException
from app.models.matches_model import Matches


def join_match(db, data):

    partido = db.query(Matches).filter(Matches.match_id == data.match_id).first()

    partido.visitor_id = data.club_id
    db.commit()

    return {"mensaje": "¡Te uniste al partido con éxito!"}
