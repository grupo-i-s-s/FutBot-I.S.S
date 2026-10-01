from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class League(Base):
    __tablename__ = "leagues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    min_teams: Mapped[int] = mapped_column(Integer, nullable=False)
    max_teams: Mapped[int] = mapped_column(Integer, nullable=False)
    start_datetime: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    round_interval: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")

    registrations: Mapped[list["LeagueRegistration"]] = relationship(
        "LeagueRegistration", back_populates="league", cascade="all, delete-orphan"
    )


class LeagueRegistration(Base):
    __tablename__ = "league_registrations"
    __table_args__ = (
        UniqueConstraint(
            "league_id", "club_id", name="uq_league_registrations_league_club"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    league_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("leagues.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    club_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clubs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    league: Mapped["League"] = relationship("League", back_populates="registrations")
