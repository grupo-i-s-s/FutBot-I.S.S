from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user_and_club
from app.models.auth_model import Club, User
from app.schemas.player import PlayerCreate, PlayerRead
from app.services import player_service

router = APIRouter(prefix="/players", tags=["Players"])


@router.post("", response_model=PlayerRead, status_code=status.HTTP_201_CREATED)
def create_player(
    payload: PlayerCreate,
    auth_data: tuple[User, Club] = Depends(get_current_user_and_club),
    db: Session = Depends(get_db),
):
    _, club = auth_data
    return player_service.create_player(db=db, club_id=club.id, data=payload)
