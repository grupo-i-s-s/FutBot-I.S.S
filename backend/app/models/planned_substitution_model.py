from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PlannedSubstitution(Base):
    __tablename__ = "planned_substitutions"
    __table_args__ = (
        CheckConstraint("pause_index BETWEEN 1 AND 3", name="ck_substitution_pause"),
        UniqueConstraint("match_id", "club_id", "command_id", name="uq_substitution_command"),
        Index(
            "uq_pending_substitution", "match_id", "club_id", "pause_index", unique=True,
            postgresql_where=text("status = 'PENDING'"), sqlite_where=text("status = 'PENDING'"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.match_id", ondelete="CASCADE"))
    club_id: Mapped[int] = mapped_column(ForeignKey("clubs.id"))
    pause_index: Mapped[int] = mapped_column(Integer)
    command_id: Mapped[str] = mapped_column(Text)
    out_player_id: Mapped[int] = mapped_column(ForeignKey("players.id"))
    in_player_id: Mapped[int] = mapped_column(ForeignKey("players.id"))
    status: Mapped[str] = mapped_column(String(16), default="PENDING", server_default="PENDING")
