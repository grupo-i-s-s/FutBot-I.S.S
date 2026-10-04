from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class League(Base):
    __tablename__ = "leagues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)

    is_private: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
        server_default="false",
    )
    password_hash: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    min_teams: Mapped[int] = mapped_column(Integer, nullable=False)
    max_teams: Mapped[int] = mapped_column(Integer, nullable=False)

    start_datetime: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    round_interval: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="open",
    )

    access_code: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    registrations: Mapped[list["LeagueRegistration"]] = relationship(
        "LeagueRegistration",
        back_populates="league",
        cascade="all, delete-orphan",
    )

    creator_club_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("clubs.id", ondelete="SET NULL"),
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint("name", name="leagues_name_key"),
    )


class LeagueRegistration(Base):
    __tablename__ = "league_registrations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    league_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("leagues.id", ondelete="CASCADE"),
        nullable=False,
    )

    club_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("clubs.id", ondelete="CASCADE"),
        nullable=False,
    )

    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    line_up: Mapped[dict | list] = mapped_column(
        JSON,
        nullable=False,
    )

    league: Mapped["League"] = relationship(
        "League",
        back_populates="registrations",
    )

    __table_args__ = (
        UniqueConstraint(
            "league_id",
            "club_id",
            name="uq_league_registrations_league_club",
        ),
    )
