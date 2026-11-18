"""
Model EvidenceReconciliation untuk Clinical Evidence Reconciliation Engine (CERE)
MeaslesWatchAI - Innovation Track | Team Inovexa
"""

from datetime import datetime
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class EvidenceReconciliation(Base):
    """
    Menyimpan hasil sintesis dan rekonsiliasi bukti klinis multimodal (CERE).
    Menggabungkan bukti dari Computer Vision (ruam), sensor suhu MLX90614,
    dan Sistem Pakar Forward Chaining/Decision Tree.
    """
    __tablename__ = "evidence_reconciliations"

    id_reconciliation: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )

    id_gejala: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("Gejala.id_gejala"),
        nullable=False,
        unique=True,
        index=True,
    )

    reconciliation_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,  # CONSISTENT, CONFLICTING, INCOMPLETE
    )

    summary: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    cv_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,  # VALID, MISSING, INVALID, FAILED
    )

    temp_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,  # VALID, MISSING, INVALID, FAILED
    )

    expert_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,  # VALID, MISSING, INVALID, FAILED
    )

    cv_prediction: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    cv_confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    measured_temp: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    expert_category: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    safety_alert: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    supporting_evidence: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
    )

    conflicting_evidence: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
    )

    missing_evidence: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
    )

    invalid_evidence: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
    )

    explanation: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    recommended_action: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    rule_version: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="CERE-v1.0",
    )

    is_diagnosis: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

