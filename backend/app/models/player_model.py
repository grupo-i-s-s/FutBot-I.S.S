from sqlalchemy import (
    Boolean,
    ForeignKey,
    String,
    text, ForeignKeyConstraint, CheckConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.behaviour_model import Behavior


class Player(Base):
    __tablename__ = "players"
    __table_args__ = (
        # Garantiza que el comportamiento asignado pertenezca al mismo club.
        ForeignKeyConstraint(
            ["club_id", "behavior_id"],
            ["behaviors.club_id", "behaviors.id"],
            name="fk_players_behavior_club",
            ondelete="RESTRICT"
        ),
        CheckConstraint("power BETWEEN 20 AND 100", name="ck_players_power"),
        CheckConstraint("agility BETWEEN 20 AND 100", name="ck_players_agility"),
        CheckConstraint("control BETWEEN 20 AND 100", name="ck_players_control"),
        CheckConstraint("speed BETWEEN 20 AND 100", name="ck_players_speed"),
        CheckConstraint("strength BETWEEN 20 AND 100", name="ck_players_strength"),
        CheckConstraint("power + agility + control + speed + strength = 300", name="ck_players_pacss_total")
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    club_id: Mapped[int] = mapped_column(ForeignKey("clubs.id", ondelete="CASCADE"), nullable=False, index=True)
    behavior_id: Mapped[int] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    power: Mapped[int] = mapped_column(nullable=False)
    agility: Mapped[int] = mapped_column(nullable=False)
    control: Mapped[int] = mapped_column(nullable=False)
    speed: Mapped[int] = mapped_column(nullable=False)
    strength: Mapped[int] = mapped_column(nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))

    club: Mapped["Club"] = relationship(back_populates="players")
