from fastapi import APIRouter

from app.controller.auth_controller import auth_router
from app.controller.health_controller import health_router
from app.controller.player_controller import player_router
from app.controller.league_controller import league_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(health_router)
api_router.include_router(player_router)
api_router.include_router(league_router)
