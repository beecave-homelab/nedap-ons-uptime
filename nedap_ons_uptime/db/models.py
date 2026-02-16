from datetime import datetime
from enum import Enum
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ErrorType(str, Enum):
    DNS = "dns"
    CONNECT = "connect"
    TLS = "tls"
    TIMEOUT = "timeout"
    HTTP = "http"
    UNKNOWN = "unknown"


class Target(Base):
    __tablename__ = "targets"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=lambda: uuid.uuid4()
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    interval_s: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    timeout_s: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    verify_tls: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.utcnow(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.utcnow(),
        onupdate=lambda: datetime.utcnow(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Target id={self.id} name={self.name} url={self.url} enabled={self.enabled} verify_tls={self.verify_tls}>"


class Check(Base):
    __tablename__ = "checks"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=lambda: uuid.uuid4()
    )
    target_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("targets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    checked_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.utcnow(), nullable=False, index=True
    )
    up: Mapped[bool] = mapped_column(Boolean, nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_type: Mapped[str] = mapped_column(String(50), nullable=False)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)

    __table_args__ = (
        Index("ix_checks_target_id_checked_at", "target_id", "checked_at"),
        Index("ix_checks_checked_at", "checked_at"),
    )

