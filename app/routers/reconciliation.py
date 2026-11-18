"""
Router API untuk Clinical Evidence Reconciliation Engine (CERE)
MeaslesWatchAI - Huawei ICT Competition 2026–2027 | Innovation Track
Team: Inovexa

Endpoints:
  POST /reconciliation/evaluate : Evaluasi dan rekonsiliasi bukti klinis multimodal
  GET  /reconciliation/{id_gejala} : Ambil hasil evaluasi rekonsiliasi bukti klinis
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import DbSession, get_current_user, is_admin
from app.models.gejala import Gejala, User
from app.models.reconciliation import EvidenceReconciliation
from app.routers.kiosk_session import _session_from_token
from app.schemas.reconciliation import (
    EvidenceReconciliationEvaluateRequest,
    EvidenceValidationDetail,
    EvidenceValidationStatus,
    ReconciliationResponse,
    ReconciliationStatus,
)
from app.services.reconciliation_service import (
    DISCLAIMER_TEXT,
    evaluate_clinical_evidence,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reconciliation", tags=["Clinical Evidence Reconciliation (CERE)"])


def _resolve_reconciliation_user(
    db: Session,
    authorization: str | None,
    kiosk_session_token: str | None,
) -> User:
    """Mendukung otentikasi via JWT Bearer (Admin / Petugas) dan Kiosk Session Token."""
    if kiosk_session_token:
        _session, nik = _session_from_token(db, kiosk_session_token)
        user = db.get(User, nik)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Pasien sesi kiosk tidak ditemukan.",
            )
        return user

    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        return get_current_user(token, db)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Autentikasi diperlukan (Bearer token atau X-Kiosk-Session).",
    )


def get_reconciliation_user(
    db: DbSession,
    authorization: str | None = Header(default=None, alias="Authorization"),
    kiosk_session_token: str | None = Header(default=None, alias="X-Kiosk-Session"),
) -> User:
    return _resolve_reconciliation_user(db, authorization, kiosk_session_token)


@router.post(
    "/evaluate",
    response_model=ReconciliationResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluasi rekonsiliasi bukti klinis multimodal (CERE)",
    description=(
        "Merekonsiliasi bukti dari citra ruam (Computer Vision), sensor suhu tubuh (MLX90614), "
        "dan Sistem Pakar (Forward Chaining). Mengidentifikasi konsistensi, konflik, atau ketidaklengkapan data."
    ),
)
def evaluate_reconciliation(
    payload: EvidenceReconciliationEvaluateRequest,
    db: DbSession,
    user: User = Depends(get_reconciliation_user),
) -> ReconciliationResponse:
    # Validasi eksistensi dan hak akses pemeriksaan
    pemeriksaan = db.get(Gejala, payload.id_gejala)
    if pemeriksaan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data pemeriksaan dengan ID {payload.id_gejala} tidak ditemukan.",
        )

    if not is_admin(user) and pemeriksaan.NIK != user.NIK:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Anda tidak memiliki izin untuk mengakses pemeriksaan ini.",
        )

    try:
        return evaluate_clinical_evidence(db, payload)
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve),
        )
    except Exception as e:
        logger.exception(f"Gagal melakukan evaluasi rekonsiliasi CERE: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Terjadi kesalahan internal saat mengevaluasi rekonsiliasi bukti klinis.",
        )


@router.get(
    "/{id_gejala}",
    response_model=ReconciliationResponse,
    status_code=status.HTTP_200_OK,
    summary="Ambil hasil rekonsiliasi bukti klinis",
    description="Mengambil riwayat evaluasi CERE yang tersimpan untuk satu pemeriksaan gejala.",
)
def get_reconciliation(
    id_gejala: str,
    db: DbSession,
    user: User = Depends(get_reconciliation_user),
) -> ReconciliationResponse:
    pemeriksaan = db.get(Gejala, id_gejala)
    if pemeriksaan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data pemeriksaan dengan ID {id_gejala} tidak ditemukan.",
        )

    if not is_admin(user) and pemeriksaan.NIK != user.NIK:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Anda tidak memiliki izin untuk mengakses pemeriksaan ini.",
        )

    row = (
        db.query(EvidenceReconciliation)
        .filter(EvidenceReconciliation.id_gejala == id_gejala)
        .first()
    )

    if row is None:
        # Jika belum pernah dievaluasi secara eksplisit, jalankan rekonsiliasi otomatis
        try:
            return evaluate_clinical_evidence(
                db,
                EvidenceReconciliationEvaluateRequest(id_gejala=id_gejala),
            )
        except Exception as e:
            logger.warning(f"Evaluasi CERE otomatis gagal untuk {id_gejala}: {e}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Hasil rekonsiliasi bukti klinis belum tersedia untuk pemeriksaan ini.",
            )

    return ReconciliationResponse(
        id_reconciliation=row.id_reconciliation,
        id_gejala=row.id_gejala,
        reconciliation_status=ReconciliationStatus(row.reconciliation_status),
        summary=row.summary,
        evidence_validation=EvidenceValidationDetail(
            computer_vision=EvidenceValidationStatus(row.cv_status),
            body_temperature=EvidenceValidationStatus(row.temp_status),
            expert_system=EvidenceValidationStatus(row.expert_status),
        ),
        cv_prediction=row.cv_prediction,
        cv_confidence=row.cv_confidence,
        measured_temp=row.measured_temp,
        expert_category=row.expert_category,
        safety_alert=row.safety_alert,
        supporting_evidence=row.supporting_evidence or [],
        conflicting_evidence=row.conflicting_evidence or [],
        missing_evidence=row.missing_evidence or [],
        invalid_evidence=row.invalid_evidence or [],
        explanation=row.explanation,
        recommended_action=row.recommended_action,
        rule_version=row.rule_version,
        is_diagnosis=False,
        disclaimer=DISCLAIMER_TEXT,
        created_at=row.created_at.isoformat() if row.created_at else None,
    )

