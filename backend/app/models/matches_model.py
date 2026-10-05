from datetime import datetime
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, JSON, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Matches(Base):
    __tablename__ = "matches"
    __table_args__ = (
        CheckConstraint("status IN ('WAITING', 'WAITING_OPPONENT', 'SCHEDULED', 'RUNNING', 'FINISHED', 'CANCELLED')", name="ck_matches_status"),
        CheckConstraint("duration_ms > 0 AND clock_ms >= 0 AND clock_ms <= duration_ms", name="ck_matches_clock"),
        CheckConstraint("local_score >= 0 AND visitor_score >= 0 AND sequence >= 0", name="ck_matches_result"),
        CheckConstraint("status != 'FINISHED' OR (finished_at IS NOT NULL AND clock_ms = duration_ms AND snapshot IS NOT NULL)", name="ck_matches_finished"),
        CheckConstraint("status != 'CANCELLED' OR cancellation_reason IS NOT NULL", name="ck_matches_cancellation_reason"),
    )
    match_id: Mapped[int] = mapped_column(primary_key=True)
    creator_id: Mapped[int] = mapped_column(ForeignKey("clubs.id", ondelete="CASCADE"), nullable=False)
    visitor_id: Mapped[int | None] = mapped_column(ForeignKey("clubs.id", ondelete="CASCADE"), nullable=True)
    init_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="WAITING", server_default="WAITING")
    duration_ms: Mapped[int] = mapped_column(default=300_000, server_default="300000")
    clock_ms: Mapped[int] = mapped_column(default=0, server_default="0")
    local_score: Mapped[int] = mapped_column(default=0, server_default="0")
    visitor_score: Mapped[int] = mapped_column(default=0, server_default="0")
    sequence: Mapped[int] = mapped_column(default=0, server_default="0")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    snapshot: Mapped[dict | None] = mapped_column(JSON(none_as_null=True).with_variant(JSONB(none_as_null=True), "postgresql"))
    runtime_state: Mapped[dict | None] = mapped_column(JSON(none_as_null=True).with_variant(JSONB(none_as_null=True), "postgresql"))
    cancellation_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)