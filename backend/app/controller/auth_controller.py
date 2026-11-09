from fastapi import APIRouter, Request, Response

from app.config import settings
from app.dependencies import CurrentIdentity, Database
from app.schemas.auth_schemas import (
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
    UserResponse,
    VerifyEmailRequest,
    ResendVerificationRequest,
    PasswordResetRequest,
    PasswordResetConfirmRequest
)
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

@auth_router.post("/register", status_code=202)
def register(data: RegisterRequest, db: Database):
    return auth_service.register(db, data)


@auth_router.post("/login", response_model=UserResponse)
def login(data: LoginRequest, request: Request, response: Response, db: Database):
    previous_token = request.cookies.get(settings.cookie_name)

    user, token = auth_service.login(db, data, previous_token)

    set_session_cookie(response, token)

    return user


@auth_router.get("/me", response_model=UserResponse)
def me(db: Database, identity: CurrentIdentity):
    return auth_service.get_current_user(db, identity)


@auth_router.post("/logout", status_code=204)
def logout(request: Request, db: Database):
    token = request.cookies.get(settings.cookie_name)

    auth_service.logout(db, token)

    response = Response(status_code=204)
    clear_session_cookie(response)

    return response


@auth_router.post("/change-password", status_code=204)
def change_password(data: ChangePasswordRequest, db: Database, identity: CurrentIdentity):
    auth_service.change_password(db, identity, data)

    response = Response(status_code=204)
    clear_session_cookie(response)

    return response

@auth_router.post("/verify-email", response_model=UserResponse)
def verify_email(data: VerifyEmailRequest, db: Database):
    return auth_service.verify_email(db, data)

@auth_router.post("/resend-verification")
def resend_verification(data: ResendVerificationRequest, db: Database):
    return auth_service.resend_verification(db, data)

@auth_router.post("/password-reset/request", status_code=202)
def request_password_reset( data: PasswordResetRequest, request: Request, db: Database):
    client_ip = request.client.host if request.client else "unknown"
    return auth_service.request_password_reset(db, data, client_ip)


@auth_router.post("/password-reset/confirm", status_code=204)
def confirm_password_reset( data: PasswordResetConfirmRequest, db: Database):
    auth_service.confirm_password_reset(db, data)

    response = Response(status_code=204)
    clear_session_cookie(response)
    return response