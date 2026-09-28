from app.schemas.auth_schema import (
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
    UserResponse,
)
from fastapi import APIRouter, Request, Response

from app.config import settings
from app.dependencies import CurrentIdentity, Database
from app.services import auth_service

auth_router = APIRouter(prefix="/auth", tags=["auth"])


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.cookie_name,
        value=token,
        max_age=settings.session_hours * 60 * 60,
        path="/",
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax"
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.cookie_name,
        path="/",
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax"
    )


@auth_router.post("/register", response_model=UserResponse, status_code=201)
def register(data: RegisterRequest, db: Database):
    return auth_service.register(db, data)


@auth_router.post("/login", response_model=UserResponse)
def login(data: LoginRequest, request: Request, response: Response, db: Database):
    previous_token = request.cookies.get(settings.cookie_name)

    user, token = auth_service.login(db, data, previous_token)

# REGISTRO
@auth_router.post("/registrar")
def resgistrar_endpoint(): 
    set_session_cookie(response, token)

    return user


@auth_router.get("/me", response_model=UserResponse)
def me(db: Database, identity: CurrentIdentity):
    return auth_service.get_current_user(db, identity)
