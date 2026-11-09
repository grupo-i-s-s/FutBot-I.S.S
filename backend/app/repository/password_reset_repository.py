import hashlib
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.auth_model import PasswordResetRequest

#Serializa operaciones por email
def lock_key(db: Session, scope: str, value: str) -> None:
    digest = hashlib.sha256(
        f"password-reset:{scope}:{value}".encode()
).digest()
    key = int.from_bytes(digest[:8], "big", signed=True)
    db.execute(select(func.pg_advisory_xact_lock(key)))

#Obtiene pedidos de la ultima hora
def get_recent(
    db: Session,
    email: str,
    ip_hash: str,
    since: datetime,
) -> list[PasswordResetRequest]:
    return list(db.scalars(
        select(PasswordResetRequest)
        .where(
            PasswordResetRequest.requested_at > since,
            (PasswordResetRequest.email == email)
            | (PasswordResetRequest.ip_hash == ip_hash),
        )
        .order_by(
            PasswordResetRequest.requested_at,
            PasswordResetRequest.id,
        )
    ))

#Buscsa y bloquea
def get_active(db: Session, email: str) -> PasswordResetRequest | None:
    return db.scalar(
        select(PasswordResetRequest)
        .where(
            PasswordResetRequest.email == email,
            PasswordResetRequest.code_hash.is_not(None),
        )
        .order_by(PasswordResetRequest.id.desc())
        .limit(1)
        .with_for_update()
    )


def invalidate_for_email(db: Session, email: str) -> None:
    db.execute(
        update(PasswordResetRequest)
        .where(
            PasswordResetRequest.email == email,
            PasswordResetRequest.code_hash.is_not(None),
        )
        .values(code_hash=None)
    )


def create(
    db: Session,
    *,
    email: str,
    ip_hash: str,
    requested_at: datetime,
    expires_at: datetime,
    code_hash: str | None,
) -> None:
    db.add(PasswordResetRequest(
        email=email,
        ip_hash=ip_hash,
        requested_at=requested_at,
        expires_at=expires_at,
        code_hash=code_hash,
    ))
    db.flush()