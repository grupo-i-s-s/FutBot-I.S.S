from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.auth_model import AuthSession


def create(
    db: Session,
    *,
    token_hash: str,
    user_id: int,
    created_at: datetime,
    expires_at: datetime
) -> None:
    session = AuthSession(
        token_hash=token_hash,
        user_id=user_id,
        created_at=created_at,
        expires_at=expires_at
    )

    db.add(session)


def get_active(db: Session, token_hash: str, now: datetime) -> AuthSession | None:
    return db.scalar(
        select(AuthSession).where(AuthSession.token_hash == token_hash, AuthSession.expires_at > now)
    )


def delete_by_token(db: Session, token_hash: str) -> None:
    db.execute(
        delete(AuthSession).where(AuthSession.token_hash == token_hash)
    )


def delete_for_user(db: Session, user_id: int) -> None:
    db.execute(
        delete(AuthSession).where(AuthSession.user_id == user_id)
    )