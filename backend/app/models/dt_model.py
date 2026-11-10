from sqlalchemy import ForeignKey, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class DtBehaviour(Base):
    __tablename__ = "dt_behaviours"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(30))
    code: Mapped[str] = mapped_column(String)

class Dt(Base):
    __tablename__ = "dt"

    id: Mapped[int] = mapped_column(primary_key=True)
    club_id: Mapped[int] = mapped_column(
        ForeignKey("clubs.id", ondelete="CASCADE"), unique=True
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )

    behaviour_id: Mapped[int | None] = mapped_column(
        ForeignKey("dt_behaviours.id", ondelete="SET NULL"), nullable=True
    )

    club = relationship("Club", back_populates="dt")
    behaviour = relationship("DtBehaviour")
