from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.auth_model import PendingEmailVerification


def get_by_email(
    db: Session,
    email: str,
    *,
    lock: bool = False
    ) -> PendingEmailVerification | None:
    query = select(PendingEmailVerification).where(PendingEmailVerification.email == email)
    if lock:
        query = query.with_for_update()
    return db.scalar(query)


def create(
    db: Session,
    *,
    email: str,
    password_hash: str,
    club_name: str,
    code_hash: str,
    created_at,
    expires_at,
    last_sent_at,
    resend_window_started_at
    ) -> PendingEmailVerification:
    pending = PendingEmailVerification(
        email=email,
        password_hash=password_hash,
        club_name=club_name,
        code_hash=code_hash,
        created_at=created_at,
        expires_at=expires_at,
        last_sent_at=last_sent_at,
        resend_window_started_at=resend_window_started_at,
    )
    db.add(pending)
    db.flush()
    return pending


def delete_by_email(db: Session, email: str) -> None:
    db.execute(delete(PendingEmailVerification).where(PendingEmailVerification.email == email))