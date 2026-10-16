from app.database import Base
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

class Stats(Base):
    __tablename__ = "Club_Stats"
    id: Mapped[int] = mapped_column(primary_key = True)
    club_id = Mapped[int] = mapped_column(ForeignKey("clubs.id", ondelete="CASCADE"), nullable = False)

    points: Mapped[int] = mapped_column(default = 0, server_default= 0, nullable = False)
    played: Mapped[int] = mapped_column(default = 0, server_default = 0, nullable= False)
    wins:   Mapped[int] = mapped_column(default = 0, server_default = 0, nullable = False)
    draws:  Mapped[int] = mapped_column(default = 0, server_default = 0, nullable = False)
    losses: Mapped[int] = mapped_column(default = 0, server_default = 0, nullable = False)
    gF:     Mapped[int] = mapped_column(default = 0, server_default = 0, nullable = False)
    gA:     Mapped[int] = mapped_column(default = 0, server_default = 0, nullable = False)

    club: Mapped["Club"] = relationship(back_populates = "stats")

