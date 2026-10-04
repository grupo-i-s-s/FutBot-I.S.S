from datetime import datetime
from sqlalchemy import (DateTime, ForeignKey, String, UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.player_model import Player


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)


class Club(Base):
    __tablename__ = "clubs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    avatar: Mapped[str] = mapped_column(String(80), nullable=False)
    friendly_available: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
        server_default="false",
    )
    players: Mapped[list[Player]] = relationship(back_populates="club")


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
