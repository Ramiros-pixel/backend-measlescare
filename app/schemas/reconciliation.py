"""
Pydantic schemas for Clinical Evidence Reconciliation Engine (CERE)
MeaslesWatchAI - Huawei ICT Competition 2026–2027
"""

from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class ReconciliationStatus(str, Enum):
    """Status hasil evaluasi rekonsiliasi bukti klinis."""
    CONSISTENT = "CONSISTENT"
    CONFLICTING = "CONFLICTING"
    INCOMPLETE = "INCOMPLETE"


class EvidenceValidationStatus(str, Enum):
    """Status validitas masing-masing modalitas bukti."""
    VALID = "VALID"
    MISSING = "MISSING"
    INVALID = "INVALID"
    FAILED = "FAILED"


class EvidenceValidationDetail(BaseModel):
    """Rincian validitas tiap modalitas bukti klinis."""
    model_config = ConfigDict(extra="forbid")

    computer_vision: EvidenceValidationStatus = Field(
        ...,
        description="Status bukti citra ruam (Computer Vision MobileNetV3).",
    )
    body_temperature: EvidenceValidationStatus = Field(
        ...,
        description="Status bukti pengukuran suhu tubuh (Sensor MLX90614).",
    )
    expert_system: EvidenceValidationStatus = Field(
        ...,
        description="Status bukti sistem pakar (Forward Chaining / Decision Tree).",
    )


class EvidenceReconciliationEvaluateRequest(BaseModel):
    """Permintaan evaluasi rekonsiliasi bukti klinis."""
    id_gejala: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="ID pemeriksaan gejala pasien.",
    )
    cv_prediction: str | None = Field(
        default=None,
        description="Hasil prediksi kelas CV (mis. 'Measles', 'Healthy', 'Chickenpox').",
    )
    cv_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Skor kepercayaan model CV (0.0 - 1.0).",
    )
    cv_probabilities: dict[str, float] | None = Field(
        default=None,
        description="Distribusi probabilitas keenam kelas model CV.",
    )


class ReconciliationResponse(BaseModel):
    """Schema respons evaluasi rekonsiliasi bukti klinis."""
    model_config = ConfigDict(from_attributes=True)

    id_reconciliation: str
    id_gejala: str
    reconciliation_status: ReconciliationStatus
    summary: str
    evidence_validation: EvidenceValidationDetail
    cv_prediction: str | None = None
    cv_confidence: float | None = None
    measured_temp: float | None = None
    expert_category: str | None = None
    safety_alert: bool = False
    supporting_evidence: list[str] = Field(default_factory=list)
    conflicting_evidence: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    invalid_evidence: list[str] = Field(default_factory=list)
    explanation: str
    recommended_action: str
    rule_version: str = "CERE-v1.0"
    is_diagnosis: bool = False
    disclaimer: str
    created_at: str | None = None

