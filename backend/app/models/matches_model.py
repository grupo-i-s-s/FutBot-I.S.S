from datetime import datetime
from sqlalchemy import ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Matches(Base):
    __tablename__ = "friendly_matches"
    match_id: Mapped[int] = mapped_column(primary_key=True)
    creator_id: Mapped[int] = mapped_column(
        ForeignKey("clubs.id", ondelete="CASCADE"), nullable=False
    )
    visitor_id: Mapped[int | None] = mapped_column(
        ForeignKey("clubs.id", ondelete="CASCADE"), nullable=True
    )
    init_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
