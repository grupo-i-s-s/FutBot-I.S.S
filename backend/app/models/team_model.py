from sqlalchemy import ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DefaultTeam(Base):
    __tablename__ = "default_teams"

    club_id: Mapped[int] = mapped_column(
        ForeignKey("clubs.id", ondelete="CASCADE"),
        primary_key=True,
    )

    line_up: Mapped[dict] = mapped_column(
        JSON(none_as_null=True),
        nullable=False,
    )