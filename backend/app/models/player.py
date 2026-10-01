from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(primary_key=True)
    club_id: Mapped[int] = mapped_column(
        ForeignKey("clubs.id", ondelete="CASCADE"),
        index=True,
    )

    name: Mapped[str] = mapped_column(String(50))
    power: Mapped[int] = mapped_column(Integer)
    agility: Mapped[int] = mapped_column(Integer)
    control: Mapped[int] = mapped_column(Integer)
    speed: Mapped[int] = mapped_column(Integer)
    strength: Mapped[int] = mapped_column(Integer)

    behaviour_id: Mapped[int | None] = mapped_column(
        ForeignKey("behaviours.id", ondelete="SET NULL"),
        nullable=True,
    )
