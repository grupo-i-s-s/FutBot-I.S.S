from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.repository import (
    session_repository,
    user_repository, behaviour_repository, player_repository
)
from app.schemas.auth_schemas import (
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
    UserResponse
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.errors import AppError
from app.models.auth_model import Club, User
from app.security import (
    DUMMY_PASSWORD_HASH,
    hash_password,
    hash_session_token,
    new_session_token,
    verify_password
)


@dataclass(frozen=True)
class Identity:
    user_id: int
    session_hash: str


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def session_error() -> AppError:
    return AppError(
        "SESSION_INVALID",
        "La sesión no existe o venció. Iniciá sesión nuevamente.")


def duplicate_error(field: str) -> AppError:
    if field == "email":
        message = "El email ya está registrado."
    else:
        message = "El nombre de usuario ya está registrado."

    return AppError(
        "ACCOUNT_DUPLICATE",
        message,
        {field: message}
    )


def public_user(user: User, club: Club) -> UserResponse:
    return UserResponse(
        id=user.id,
        name=user.name,
        username=user.username,
        email=user.email,
        club_id=club.id
    )


def register(db: Session, data: RegisterRequest) -> UserResponse:
    try:
        existing_email = user_repository.get_by_email(db, str(data.email))

        if existing_email:
            raise duplicate_error("email")

        existing_username = user_repository.get_by_username(db, data.username)

        if existing_username:
            raise duplicate_error("username")

        user = user_repository.create_user(
            db,
            name=data.name,
            username=data.username,
            email=str(data.email),
            password_hash=hash_password(data.password)
        )

        club = user_repository.create_club(
            db,
            user_id=user.id,
            name=data.club_name,
            avatar=data.avatar
        )

        behaviours = behaviour_repository.create_default_behaviours(db, club.id)

        player_repository.create_default_players(db, club.id, behaviours)


        result = public_user(user, club)

        db.commit()
        return result

    except IntegrityError as exc:
        db.rollback()

        # Resuelve también el caso de dos registros simultáneos que intentan utilizar el mismo email o username.
        diagnostic = getattr(exc.orig, "diag", None)
        constraint = getattr(diagnostic, "constraint_name", None)

        if constraint == "uq_users_email":
            raise duplicate_error("email") from exc

        if constraint == "uq_users_username":
            raise duplicate_error("username") from exc

        raise

    except Exception:
        db.rollback()
        raise


def login(db: Session, data: LoginRequest, previous_token: str | None) -> tuple[UserResponse, str]:
    try:
        user = user_repository.get_by_email(db, str(data.email), lock=True)

        encoded_hash = (
            user.password_hash
            if user is not None
            else DUMMY_PASSWORD_HASH
        )

        password_matches = verify_password(data.password, encoded_hash)

        if user is None or not password_matches:
            raise AppError(
                "INVALID_CREDENTIALS",
                "Email o contraseña incorrectos.")

        club = user_repository.get_club(db, user.id)

        if club is None:
            raise AppError(
                "ACCOUNT_INCOMPLETE",
                "La cuenta no tiene un club asociado.")

        # Reemplaza la sesión anterior de este navegador.
        if previous_token:
            session_repository.delete_by_token(
                db,
                hash_session_token(previous_token),
            )

        token = new_session_token()
        now = utc_now()

        session_repository.create(
            db,
            token_hash=hash_session_token(token),
            user_id=user.id,
            created_at=now,
            expires_at=now + timedelta(hours=settings.session_hours)
        )

        result = public_user(user, club)

        db.commit()
        return result, token

    except Exception:
        db.rollback()
        raise


def authenticate(db: Session, token: str | None) -> Identity:
    if not token or len(token) != 43:
        raise session_error()

    token_hash = hash_session_token(token)

    session = session_repository.get_active(db, token_hash, utc_now())

    if session is None:
        raise session_error()

    return Identity(
        user_id=session.user_id,
        session_hash=token_hash
    )


def get_current_user(db: Session, identity: Identity) -> UserResponse:
    user = user_repository.get_by_id(db, identity.user_id)

    if user is None:
        raise session_error()

    club = user_repository.get_club(db, user.id)

    if club is None:
        raise AppError(
            "ACCOUNT_INCOMPLETE",
            "La cuenta no tiene un club asociado.")

    return public_user(user, club)


def logout(db: Session, token: str | None) -> None:
    try:
        if token:
            session_repository.delete_by_token(db, hash_session_token(token), )

        db.commit()

    except Exception:
        db.rollback()
        raise


def change_password(db: Session, identity: Identity, data: ChangePasswordRequest) -> None:
    try:
        user = user_repository.get_by_id(db, identity.user_id, lock=True)

        # Revalida la sesión luego de obtener el bloqueo.
        # Otro cambio de contraseña podría haberla revocado.
        session = session_repository.get_active(db, identity.session_hash, utc_now())

        if user is None or session is None:
            raise session_error()

        current_password_matches = verify_password(data.old_password, user.password_hash)

        if not current_password_matches:
            raise AppError(
                "PASSWORD_INVALID",
                "La contraseña actual es incorrecta.",
                {
                    "oldPassword": (
                        "La contraseña actual es incorrecta."
                    )
                },
            )

        new_password_matches = verify_password(data.new_password, user.password_hash)

        if new_password_matches:
            raise AppError(
                "PASSWORD_INVALID",
                "La nueva contraseña debe ser diferente.",
                {
                    "newPassword": (
                        "Elegí una contraseña diferente."
                    )
                }
            )

        user_repository.set_password(user, hash_password(data.new_password))

        # Incluye la sesión desde la que se hizo el cambio.
        session_repository.delete_for_user(db, user.id)

        db.commit()

    except Exception:
        db.rollback()
        raise
