from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class SensorReading(Base):
    """Telemetri sensor (staging + audit trail). Bukan tabel examination."""

    __tablename__ = "sensor_readings"

    id_reading: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    event_id: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True
    )
    device_id: Mapped[str] = mapped_column(String(64), nullable=False)
    rfid_uid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    id_session: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("kiosksessions.id_session", ondelete="SET NULL"),
        nullable=True,
    )
    NIK: Mapped[str | None] = mapped_column(
        String(16),
        ForeignKey("Users.NIK", ondelete="SET NULL"),
        nullable=True,
    )
    object_temp: Mapped[float | None] = mapped_column(Float, nullable=True)
    ambient_temp: Mapped[float | None] = mapped_column(Float, nullable=True)
    uptime_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    source_format: Mapped[str] = mapped_column(
        String(20), nullable=False, default="esp32"
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    validation_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    raw_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
