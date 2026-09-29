from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.auth_model import Club, User


def get_by_email(db: Session, email: str, *, lock: bool = False) -> User | None:
    query = select(User).where(User.email == email)
    if lock:
        query = query.with_for_update()
    return db.scalar(query)


def get_by_username(db: Session, username: str) -> User | None:
    return db.scalar(select(User).where(User.username == username))


def get_by_id(db: Session, user_id: int, *, lock: bool = False) -> User | None:
    query = select(User).where(User.id == user_id)
    if lock:
        query = query.with_for_update()
    return db.scalar(query)


def get_club(db: Session, user_id: int) -> Club | None:
    return db.scalar(select(Club).where(Club.user_id == user_id))


def create_user(db: Session, *, name: str, username: str, email: str, password_hash: str) -> User:
    user = User(
        name=name,
        username=username,
        email=email,
        password_hash=password_hash,
    )
    db.add(user)
    db.flush()
    return user


def create_club(db: Session, *, user_id: int, name: str, avatar: str) -> Club:
    club = Club(
        user_id=user_id,
        name=name,
        avatar=avatar,
        friendly_available=False,
    )
    db.add(club)
    db.flush()
    return club


def set_password(user: User, password_hash: str) -> None:
    user.password_hash = password_hash
