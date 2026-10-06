from fastapi import APIRouter

from app.controller.auth_controller import auth_router
from app.controller.behaviour_controller import behaviour_router
from app.controller.club_controller import club_router
from app.controller.health_controller import health_router
from app.controller.league_controller import league_router
from app.controller.match_stream_controller import match_stream_router
from app.controller.matches_controller import matches_router
from app.controller.player_controller import player_router
from app.controller.team_controller import team_router, catalogs_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(health_router)
api_router.include_router(player_router)
api_router.include_router(matches_router)
api_router.include_router(league_router)
api_router.include_router(behaviour_router)
api_router.include_router(match_stream_router)
api_router.include_router(club_router)
api_router.include_router(team_router)
api_router.include_router(catalogs_router)
