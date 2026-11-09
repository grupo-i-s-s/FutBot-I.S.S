from datetime import datetime, timezone
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional

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
    
    draw_seed: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
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
        index=True,
    )

    club_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("clubs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    line_up: Mapped[dict | list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        server_default="[]",
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
        CheckConstraint(
            "lineup_version >= 0",
            name="ck_league_registrations_lineup_version",
        ),
    )

    lineup_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )


class LeagueRound(Base):
    __tablename__ = "league_rounds"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    league_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("leagues.id", ondelete="CASCADE"),
        nullable=False,
    )

    number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    schedule_confirmed: Mapped[bool] = mapped_column(
        default=False, server_default="false",
    )

    bye_club_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("clubs.id"),
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "league_id",
            "number",
            name="uq_league_rounds_league_number",
        ),
    )


class LeagueStanding(Base):
    __tablename__ = "league_standings"

    league_id: Mapped[int] = mapped_column(
        ForeignKey("leagues.id", ondelete="CASCADE"), primary_key=True,
    )
    club_id: Mapped[int] = mapped_column(
        ForeignKey("clubs.id", ondelete="CASCADE"), primary_key=True,
    )
    played: Mapped[int] = mapped_column(default=0, server_default="0")
    wins: Mapped[int] = mapped_column(default=0, server_default="0")
    draws: Mapped[int] = mapped_column(default=0, server_default="0")
    losses: Mapped[int] = mapped_column(default=0, server_default="0")
    goals_for: Mapped[int] = mapped_column(default=0, server_default="0")
    goals_against: Mapped[int] = mapped_column(default=0, server_default="0")
    points: Mapped[int] = mapped_column(default=0, server_default="0")
