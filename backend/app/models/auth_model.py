from datetime import datetime

from sqlalchemy import (DateTime, ForeignKey, String, UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email"), UniqueConstraint("username"))
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    email: Mapped[str] = mapped_column(String(254))
    username: Mapped[str] = mapped_column(String(50))
    password_hash: Mapped[str] = mapped_column(String(255)))

    class Club(Base):
        __tablename__ = "clubs"
        id: Mapped[int] = mapped_column(primary_key=True)
        user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
        name: Mapped[str] = mapped_column(String(50))
        avatar: Mapped[str] = mapped_column(String(80))
        friendly_available: Mapped[bool] = mapped_column(default=False)

    class AuthSession(Base):
        __tablename__ = "auth_sessions"
        token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
        user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
        created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
        expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
