from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.errors import AppError
from app.models.auth_model import Club, User
from app.repository import (
    session_repository,
    user_repository,
    behaviour_repository,
    player_repository,
    team_repository,
    dt_repository,
    pending_email_verification_repository,
)
from app.schemas.auth_schemas import (
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
    UserResponse,
    VerifyEmailRequest,
    ResendVerificationRequest
)
from app.schemas.team_schemas import Lineup
from app.security import (
    DUMMY_PASSWORD_HASH,
    hash_password,
    hash_session_token,
    new_session_token,
    verify_password,
    new_email_verification_code
)
from app.services import email_service
from app.schemas.avatar_schemas import DEFAULT_AVATAR


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
        messages = {"email": "El email ya está registrado.", "clubName": "Ya existe un club con ese nombre."}
        message = messages[field]
    else:
        message = "El nombre de usuario ya está registrado."

    return AppError(
        "ACCOUNT_DUPLICATE",
        message,
        {field: message},
    )


def public_user(user: User, club: Club) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        club_id=club.id
    )


def _create_account(
    db: Session,
    *,
    email: str,
    password_hash: str,
    club_name: str,
) -> UserResponse:
    existing_email = user_repository.get_by_email(db, email)
    if existing_email:
        raise duplicate_error("email")

    user = user_repository.create_user(
        db,
        email=email,
        password_hash=password_hash,
    )

    club = user_repository.create_club(
        db,
        user_id=user.id,
        name=club_name,
        avatar=DEFAULT_AVATAR,
    )

    dt_behaviours = dt_repository.create_default_dt_behaviours(db, user.id)
    default_dt_behaviour_id = dt_behaviours[0].id if dt_behaviours else None
    dt_repository.create_dt(db, club.id, default_dt_behaviour_id)

    behaviours = behaviour_repository.create_default_behaviours(db, club.id)
    players = player_repository.create_default_players(db, club.id, behaviours)

    line_up = Lineup.model_validate({
        "formationId": 1,
        "starters": [
            {
                "playerId": player.id,
                "behaviourId": player.behavior_id,
            }
            for player in players[:3]
        ],
        "substitutes": [
            {
                "playerId": player.id,
                "behaviourId": player.behavior_id,
            }
            for player in players[3:]
        ],
    })

    team_repository.save(db, club.id, line_up.model_dump(by_alias=True))
    return public_user(user, club)


def register(db: Session, data: RegisterRequest) -> dict[str, str]:
    email = str(data.email)
    now = utc_now()

    try:
        if user_repository.get_by_email(db, email):
            raise duplicate_error("email")

        pending = pending_email_verification_repository.get_by_email(db, email, lock=True)

        if pending and pending.expires_at > now:
            raise AppError(
                "EMAIL_VERIFICATION_PENDING",
                "Ya hay una verificación pendiente para ese email. "
                "Usá el código que recibiste o solicitá uno nuevo.",
            )

        if pending:
            pending_email_verification_repository.delete_by_email(db, email)

        code = new_email_verification_code()

        pending_email_verification_repository.create(
            db,
            email=email,
            password_hash=hash_password(data.password),
            club_name=data.club_name,
            code_hash=hash_password(code),
            created_at=now,
            expires_at=now + timedelta(minutes=10),
            last_sent_at=now,
            resend_window_started_at=now,
        )

        db.commit()

    except Exception:
        db.rollback()
        raise

    email_service.send_verification_code(email, code)
    return {"message": "Se envio código para verificar tu correo."}

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

def verify_email(db: Session, data: VerifyEmailRequest) -> UserResponse:
    email = str(data.email)
    now = utc_now()

    try:
        pending = pending_email_verification_repository.get_by_email(db, email, lock=True)

        if pending is None:
            raise AppError(
                "EMAIL_VERIFICATION_INVALID",
                "El código no es válido o venció. Iniciá el registro nuevamente.",
            )

        if pending.expires_at <= now:
            pending_email_verification_repository.delete_by_email(db, email)
            db.commit()
            raise AppError(
                "EMAIL_VERIFICATION_INVALID",
                "El código no es válido o venció. Iniciá el registro nuevamente.",
            )

        if not verify_password(data.code, pending.code_hash):
            attempts = pending_email_verification_repository.increment_attempts(db, pending)

            if attempts >= 5:
                pending_email_verification_repository.delete_by_email(db, email)

            db.commit()

            if attempts >= 5:
                raise AppError(
                    "EMAIL_VERIFICATION_ATTEMPTS_EXCEEDED",
                    "Se agotaron los intentos. Iniciá el registro nuevamente.",
                )

            raise AppError(
                "EMAIL_VERIFICATION_INVALID",
                "El código no es válido o venció.",
            )

        result = _create_account(
            db,
            email=email,
            password_hash=pending.password_hash,
            club_name=pending.club_name,
        )
        pending_email_verification_repository.delete_by_email(db, email)
        db.commit()
        return result

    except IntegrityError as exc:
        db.rollback()

        diagnostic = getattr(exc.orig, "diag", None)
        constraint = getattr(diagnostic, "constraint_name", None)

        if constraint == "uq_users_email":
            raise duplicate_error("email") from exc

        if constraint == "clubs_name_key":
            raise duplicate_error("clubName") from exc

        raise

    except Exception:
        db.rollback()
        raise

def resend_verification(db: Session, data: ResendVerificationRequest) -> dict[str, str]:
    email = str(data.email)
    now = utc_now()

    try:
        pending = pending_email_verification_repository.get_by_email(db, email, lock=True)

        if pending is None:
            return {"message": "Mail no válido para verificar. Registrate nuevamente."}

        if pending.expires_at <= now:
            pending_email_verification_repository.delete_by_email(db, email)
            db.commit()
            return {"message": "La solicitud venció. Iniciá el registro nuevamente."}

        if now < pending.last_sent_at + timedelta(seconds=60):
            raise AppError(
                "EMAIL_VERIFICATION_RESEND_LIMIT",
                "Esperá 60 segundos antes de pedir otro código.",
            )

        window_started_at = pending.resend_window_started_at
        resend_count = pending.resend_count

        if now >= window_started_at + timedelta(hours=1):
            window_started_at = now
            resend_count = 0

        if resend_count >= 5:
            raise AppError(
                "EMAIL_VERIFICATION_RESEND_LIMIT",
                "Alcanzaste el máximo de 5 reenvíos por hora.",
            )

        code = new_email_verification_code()

        pending_email_verification_repository.update_for_resend(
            db,
            pending,
            code_hash=hash_password(code),
            expires_at=now + timedelta(minutes=10),
            last_sent_at=now,
            resend_window_started_at=window_started_at,
            resend_count=resend_count + 1,
        )

        email_service.send_verification_code(email, code)
        db.commit()

        return {"message": "Si existe una verificación pendiente, se envió un nuevo código."}

    except Exception:
        db.rollback()
        raise
