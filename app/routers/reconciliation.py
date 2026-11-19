from fastapi import APIRouter, Depends, HTTPException

from app.core.security import DbSession
from app.models.reconciliation import EvidenceReconciliation
from app.routers.pakar import get_pakar_user
from app.schemas.reconciliation import (
    EvidenceReconciliationEvaluateRequest,
    EvidenceValidationDetail,
    ReconciliationResponse,
)
from app.services.reconciliation_service import evaluate_clinical_evidence


router = APIRouter(tags=["Clinical Evidence Reconciliation"])


@router.post("/reconciliation/evaluate", response_model=ReconciliationResponse)
def evaluate_reconciliation(
    payload: EvidenceReconciliationEvaluateRequest,
    db: DbSession,
    user=Depends(get_pakar_user),
):
    from app.models.gejala import Gejala
    from app.core.security import is_admin

    examination = db.get(Gejala, payload.id_gejala)
    if examination is None:
        raise HTTPException(status_code=404, detail="Data pemeriksaan tidak ditemukan.")
    if not is_admin(user) and examination.NIK != user.NIK:
        raise HTTPException(status_code=403, detail="Tidak memiliki akses ke pemeriksaan ini.")

    try:
        result = evaluate_clinical_evidence(
            db=db,
            id_gejala=payload.id_gejala,
            cv_prediction=payload.cv_prediction,
            cv_confidence=payload.cv_confidence,
            cv_status=payload.cv_status,
            expert_category=payload.expert_category,
            safety_alert=payload.safety_alert,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    record = (
        db.query(EvidenceReconciliation)
        .filter(EvidenceReconciliation.id_gejala == payload.id_gejala)
        .first()
    )
    if record is None:
        record = EvidenceReconciliation(
            id_gejala=payload.id_gejala,
            reconciliation_status=result["reconciliation_status"],
            summary=result["summary"],
            cv_status=result["evidence_validation"]["computer_vision"],
            temp_status=result["evidence_validation"]["body_temperature"],
            expert_status=result["evidence_validation"]["expert_system"],
            cv_prediction=result["cv_prediction"],
            cv_confidence=result["cv_confidence"],
            measured_temp=result["measured_temp"],
            expert_category=result["expert_category"],
            safety_alert=result["safety_alert"],
            supporting_evidence=result["supporting_evidence"],
            conflicting_evidence=result["conflicting_evidence"],
            missing_evidence=result["missing_evidence"],
            invalid_evidence=result["invalid_evidence"],
            explanation=result["explanation"],
            recommended_action=result["recommended_action"],
        )
        db.add(record)
    else:
        record.reconciliation_status = result["reconciliation_status"]
        record.summary = result["summary"]
        record.cv_status = result["evidence_validation"]["computer_vision"]
        record.temp_status = result["evidence_validation"]["body_temperature"]
        record.expert_status = result["evidence_validation"]["expert_system"]
        record.cv_prediction = result["cv_prediction"]
        record.cv_confidence = result["cv_confidence"]
        record.measured_temp = result["measured_temp"]
        record.expert_category = result["expert_category"]
        record.safety_alert = result["safety_alert"]
        record.supporting_evidence = result["supporting_evidence"]
        record.conflicting_evidence = result["conflicting_evidence"]
        record.missing_evidence = result["missing_evidence"]
        record.invalid_evidence = result["invalid_evidence"]
        record.explanation = result["explanation"]
        record.recommended_action = result["recommended_action"]

    db.commit()
    db.refresh(record)

    return ReconciliationResponse(
        id_reconciliation=record.id_reconciliation,
        id_gejala=record.id_gejala,
        reconciliation_status=record.reconciliation_status,
        summary=record.summary,
        evidence_validation=EvidenceValidationDetail(
            computer_vision=record.cv_status,
            body_temperature=record.temp_status,
            expert_system=record.expert_status,
        ),
        cv_prediction=record.cv_prediction,
        cv_confidence=record.cv_confidence,
        measured_temp=record.measured_temp,
        expert_category=record.expert_category,
        safety_alert=record.safety_alert,
        supporting_evidence=record.supporting_evidence,
        conflicting_evidence=record.conflicting_evidence,
        missing_evidence=record.missing_evidence,
        invalid_evidence=record.invalid_evidence,
        explanation=record.explanation,
        recommended_action=record.recommended_action,
    )


@router.get("/reconciliation/{id_gejala}", response_model=ReconciliationResponse)
def get_reconciliation(
    id_gejala: str,
    db: DbSession,
    user=Depends(get_pakar_user),
):
    from app.models.gejala import Gejala
    from app.core.security import is_admin

    examination = db.get(Gejala, id_gejala)
    if examination is None:
        raise HTTPException(status_code=404, detail="Data pemeriksaan tidak ditemukan.")
    if not is_admin(user) and examination.NIK != user.NIK:
        raise HTTPException(status_code=403, detail="Tidak memiliki akses ke pemeriksaan ini.")

    record = (
        db.query(EvidenceReconciliation)
        .filter(EvidenceReconciliation.id_gejala == id_gejala)
        .first()
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Hasil rekonsiliasi belum tersedia.")

    return ReconciliationResponse(
        id_reconciliation=record.id_reconciliation,
        id_gejala=record.id_gejala,
        reconciliation_status=record.reconciliation_status,
        summary=record.summary,
        evidence_validation=EvidenceValidationDetail(
            computer_vision=record.cv_status,
            body_temperature=record.temp_status,
            expert_system=record.expert_status,
        ),
        cv_prediction=record.cv_prediction,
        cv_confidence=record.cv_confidence,
        measured_temp=record.measured_temp,
        expert_category=record.expert_category,
        safety_alert=record.safety_alert,
        supporting_evidence=record.supporting_evidence,
        conflicting_evidence=record.conflicting_evidence,
        missing_evidence=record.missing_evidence,
        invalid_evidence=record.invalid_evidence,
        explanation=record.explanation,
        recommended_action=record.recommended_action,
    )
