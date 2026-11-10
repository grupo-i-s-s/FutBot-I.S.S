from fastapi import APIRouter, status, Query

from app.dependencies import CurrentClub, Database
from app.schemas.pagination import MAX_PAGE_SIZE, Page, validate_page_offset
from app.schemas.player import (
    PlayerBehaviourUpdate,
    PlayerCreate,
    PlayerListResponse,
    PlayerRead,
)
from app.services import player_service

player_router = APIRouter(prefix="/players", tags=["players"])


@player_router.get("", response_model=Page[PlayerRead] | PlayerListResponse)
def list_players(
    club: CurrentClub,
    db: Database,
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int | None = Query(None, alias="pageSize", ge=1, le=MAX_PAGE_SIZE),
    limit: int = Query(9, ge=1, le=MAX_PAGE_SIZE, deprecated=True),
    search: str | None = Query(None, min_length=1),
):
    size = page_size if page_size is not None else limit
    validate_page_offset(page, size)
    players, total = player_service.get_players(db=db, club_id=club.id, page=page, limit=size, search=search)
    result = Page[PlayerRead](items=players, page=page, page_size=size, total=total)
    if page_size is not None:
        return result
    return PlayerListResponse(
        items=result.items, page=page, limit=limit, total=total, total_pages=result.total_pages,
    )

@player_router.get("/by-ids", response_model=list[PlayerRead])
def get_players_by_ids(
    club: CurrentClub,
    db: Database,
    ids: list[int] = Query(..., min_length=1),
):
    return player_service.get_players_by_ids(
        db=db,
        club_id=club.id,
        player_ids=ids,
    )


@player_router.post("", response_model=PlayerRead, status_code=status.HTTP_201_CREATED)
def create_player(payload: PlayerCreate, club: CurrentClub, db: Database):
    return player_service.create_player(db=db, club_id=club.id, data=payload)


@player_router.patch("/{player_id}/behaviour", response_model=PlayerRead)
def assign_player_behaviour(
    player_id: int, payload: PlayerBehaviourUpdate, club: CurrentClub, db: Database
):
    return player_service.assign_behaviour(
        db=db, club_id=club.id, player_id=player_id, behaviour_id=payload.behaviour_id
    )
