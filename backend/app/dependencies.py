from datetime import datetime, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.auth_model import AuthSession, Club, User
from app.security import hash_session_token

security = HTTPBearer()


def get_current_user_and_club(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> tuple[User, Club]:
    token = credentials.credentials
    token_hashed = hash_session_token(token)
    now = datetime.now(timezone.utc)

    stmt = select(AuthSession).where(
        AuthSession.token_hash == token_hashed,
        AuthSession.expires_at > now,
    )
    session = db.scalar(stmt)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión inválida o expirada",
        )

    user = db.get(User, session.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado",
        )

    club_stmt = select(Club).where(Club.user_id == user.id)
    club = db.scalar(club_stmt)
    if not club:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El usuario no posee un club asignado",
        )

    return user, club
