from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
import logging
from math import ceil
from secrets import compare_digest

from app.repository import password_reset_repository
from app.schemas.auth_schemas import ( PasswordResetRequest, PasswordResetConfirmRequest)
from app.security import password_reset_digest

from app.config import settings
from app.errors import AppError
from app.models.auth_model import Club, User
from app.repository import (
    session_repository,
    user_repository,
    club_repository,
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
from app.security import ( DUMMY_PASSWORD_HASH, hash_password, hash_session_token, new_session_token, verify_password, new_email_verification_code)
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
    messages = {"email": "El email ya está registrado.", "clubName": "Ya existe un club con ese nombre."}
    message = messages.get(field, "El nombre de usuario ya está registrado.")

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

        if club_repository.get_by_name(db, data.club_name):
            raise duplicate_error("clubName")

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

PASSWORD_RESET_MESSAGE = {
    "message": "Si la cuenta existe, recibirás un código para recuperar la contraseña."
}


def password_reset_invalid() -> AppError:
    return AppError(
        "PASSWORD_RESET_INVALID",
        "El código no es válido o venció.",
    )


def check_password_reset_limit(
    requests: list,
    email: str,
    ip_hash: str,
    now: datetime,
) -> None:
    retry_after = 0
    groups = (
        [item.requested_at for item in requests if item.email == email],
        [item.requested_at for item in requests if item.ip_hash == ip_hash],
    )

    for times in groups:
        if times:
            retry_after = max(
                retry_after,
                60 - (now - times[-1]).total_seconds(),
            )

        if len(times) >= 5:
            retry_after = max(
                retry_after,
                3600 - (now - times[-5]).total_seconds(),
            )

    if retry_after > 0:
        raise AppError(
            "PASSWORD_RESET_RATE_LIMIT",
            "Esperá antes de solicitar otro código.",
            {"retryAfter": str(ceil(retry_after))},
        )

def request_password_reset(
    db: Session,
    data: PasswordResetRequest,
    client_ip: str,
) -> dict[str, str]:
    email = str(data.email)
    ip_hash = password_reset_digest("PASSWORD_RESET_IP", client_ip)

    try:
        password_reset_repository.lock_key(db, "email", email)
        password_reset_repository.lock_key(db, "ip", ip_hash)

        now = utc_now()
        recent = password_reset_repository.get_recent( db, email, ip_hash, now - timedelta(hours=1) )
        check_password_reset_limit(recent, email, ip_hash, now)

        pending_account = pending_email_verification_repository.get_by_email(db, email, lock=True)
        user = user_repository.get_by_email(db, email)
        has_pending_account = ( pending_account is not None and pending_account.expires_at > now)
        code_hash = None

        if user is not None or has_pending_account:
            previous = password_reset_repository.get_active(db, email)

            while True:
                code = new_email_verification_code()
                digest = password_reset_digest(
                    "PASSWORD_RESET",
                    f"{email}\0{code}",
                )
                if previous is None or not compare_digest(
                    digest,
                    previous.code_hash,
                ):
                    break

            try:
                email_service.send_password_reset_code(email, code)
            except AppError as exc:
                if exc.code not in {
                    "EMAIL_DELIVERY_FAILED",
                    "EMAIL_NOT_CONFIGURED",
                }:
                    raise

                logging.getLogger(__name__).warning(
                    "Falló un envío de recuperación (%s).",
                    exc.code,
                )
            else:
                password_reset_repository.invalidate_for_email(db, email)
                code_hash = digest

        password_reset_repository.create(
            db,
            email=email,
            ip_hash=ip_hash,
            requested_at=now,
            expires_at=now + timedelta(minutes=10),
            code_hash=code_hash,
        )

        db.commit()
        return dict(PASSWORD_RESET_MESSAGE)

    except Exception:
        db.rollback()
        raise

def confirm_password_reset( db: Session, data: PasswordResetConfirmRequest) -> None:
    email = str(data.email)
    digest = password_reset_digest(
        "PASSWORD_RESET",
        f"{email}\0{data.code}",
    )

    try:
        password_reset_repository.lock_key(db, "email", email)
        pending_account = pending_email_verification_repository.get_by_email(
            db, email, lock=True,
        )
        user = user_repository.get_by_email(db, email, lock=True)
        pending = password_reset_repository.get_active(db, email)
        now = utc_now()

        has_pending_account = (
            pending_account is not None
            and pending_account.expires_at > now
        )

        if (
            (user is None and not has_pending_account)
            or pending is None
            or pending.expires_at <= now
            or pending.attempts >= 5
        ):
            raise password_reset_invalid()

        if not compare_digest(digest, pending.code_hash):
            pending.attempts += 1

            if pending.attempts >= 5:
                pending.code_hash = None

            db.commit()
            raise password_reset_invalid()

        if verify_password(data.new_password, user.password_hash):
            raise AppError(
                "PASSWORD_INVALID",
                "La nueva contraseña debe ser diferente.",
                {"newPassword": "Elegí una contraseña diferente."},
            )

        user_repository.set_password(
            user,
            hash_password(data.new_password),
        )
        session_repository.delete_for_user(db, user.id)
        password_reset_repository.invalidate_for_email(db, email)

        db.commit()

    except Exception:
        db.rollback()
        raise