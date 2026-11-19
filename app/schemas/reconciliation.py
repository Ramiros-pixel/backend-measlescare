from pydantic import BaseModel, Field


class EvidenceReconciliationEvaluateRequest(BaseModel):
    id_gejala: str = Field(min_length=1, max_length=20)
    cv_prediction: str | None = None
    cv_confidence: float | None = Field(default=None, ge=0, le=1)
    cv_probabilities: dict[str, float] | None = None
    cv_status: str | None = None
    expert_category: str | None = None
    safety_alert: bool | None = None


class EvidenceValidationDetail(BaseModel):
    computer_vision: str
    body_temperature: str
    expert_system: str


class ReconciliationResponse(BaseModel):
    id_reconciliation: str
    id_gejala: str
    reconciliation_status: str
    summary: str
    evidence_validation: EvidenceValidationDetail
    cv_prediction: str | None = None
    cv_confidence: float | None = None
    measured_temp: float | None = None
    expert_category: str | None = None
    safety_alert: bool
    supporting_evidence: list[str]
    conflicting_evidence: list[str]
    missing_evidence: list[str] = []
    invalid_evidence: list[str] = []
    explanation: str
    recommended_action: str
