from fastapi import APIRouter

from app.controller.auth_controller import auth_router
from app.controller.club_controller import club_router
from app.controller.health_controller import health_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(club_router)
api_router.include_router(health_router)
