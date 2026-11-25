"""Ingesti pembacaan sensor: validasi domain + resolusi sesi aktif + persistensi.

Backend adalah validator otoritatif. Bridge (adapter tipis) hanya mem-parse dan
menormalisasi payload; seluruh keputusan status direkam di sini bersama alasan
terstruktur dan payload mentah (audit trail). Tidak ada auto-registrasi pasien.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.constants import (
    ALLOWED_DEVICES,
    RFID_UID_PATTERN,
    SUHU_MAX,
    SUHU_MIN,
)
from app.models.gejala import KioskSession, PatientCard
from app.models.sensor import SensorReading

log = logging.getLogger("sensor-service")

_UID_RE = re.compile(RFID_UID_PATTERN)


def _active_sessions(db: Session, id_device: str) -> list[KioskSession]:
    """Sesi aktif (revoked=0, belum kedaluwarsa) untuk perangkat kiosk."""
    now = datetime.utcnow()
    return (
        db.query(KioskSession)
        .filter(
            KioskSession.id_device == id_device,
            KioskSession.revoked.is_(False),
            KioskSession.expires_at > now,
        )
        .order_by(KioskSession.created_at.desc())
        .all()
    )


def _uid_check(
    db: Session, rfid_uid: str | None, session_nik: str | None
) -> tuple[str, str] | None:
    """Validasi UID. Return (status, reason) bila ditolak, None bila lolos.

    UID tidak pernah menjadi sumber identitas pasien; hanya cross-check/audit.
    Kartu tak dikenal ditolak (tidak pernah di-register otomatis).
    """
    if rfid_uid is None:
        return None
    if not _UID_RE.match(rfid_uid):
        return ("REJECTED_UID", "bad_uid_format")
    card = db.query(PatientCard).filter(PatientCard.rfid_uid == rfid_uid).first()
    if card is None:
        return ("REJECTED_UID", "unknown_card")
    if session_nik is not None and card.NIK != session_nik:
        return ("REJECTED_UID", "card_patient_mismatch")
    return None


def ingest_sensor_reading(db: Session, payload: dict, calling_device) -> dict:
    """Validasi + persisten satu pembacaan. Return dict status terstruktur."""
    event_id = str(payload.get("event_id") or "")
    device_id = str(payload.get("device_id") or "")
    rfid_uid = (payload.get("rfid_uid") or "").strip().upper() or None
    object_temp = payload.get("object_temp")
    ambient_temp = payload.get("ambient_temp")
    uptime_ms = payload.get("uptime_ms")
    source_format = payload.get("source_format") or "esp32"
    raw_payload = payload.get("raw_payload")

    def _row(status, validation_status=None, reason=None, session=None):
        return SensorReading(
            event_id=event_id,
            device_id=device_id,
            rfid_uid=rfid_uid,
            id_session=session.id_session if session else None,
            NIK=session.NIK if session else None,
            object_temp=object_temp,
            ambient_temp=ambient_temp,
            uptime_ms=uptime_ms,
            source_format=source_format,
            status=status,
            validation_status=validation_status,
            reason=reason,
            raw_payload=raw_payload,
        )

    def _commit(row):
        try:
            db.add(row)
            db.commit()
            db.refresh(row)
        except IntegrityError:
            db.rollback()
            return {
                "status": "duplicate",
                "event_id": event_id,
                "reason": "event_id_already_processed",
            }
        return {
            "status": row.status,
            "id_reading": row.id_reading,
            "event_id": row.event_id,
            "id_session": row.id_session,
            "nik": row.NIK,
            "validation_status": row.validation_status,
            "reason": row.reason,
        }

    # Idempotensi pre-check (tanpa menunggu exception UNIQUE)
    if event_id:
        existing = (
            db.query(SensorReading)
            .filter(SensorReading.event_id == event_id)
            .first()
        )
        if existing is not None:
            return {
                "status": "duplicate",
                "event_id": event_id,
                "reason": "event_id_already_processed",
            }

    # 1. device allowlist (MQTT device_id)
    if device_id not in ALLOWED_DEVICES:
        return _commit(_row("REJECTED_DEVICE", reason="device_not_allowed"))

    # 2. suhu wajib ada
    if object_temp is None:
        return _commit(
            _row(
                "REJECTED_PAYLOAD",
                validation_status="MISSING",
                reason="missing_temperature",
            )
        )

    # 3. rentang suhu (nilai asli dipertahankan; tidak di-clamp)
    if not (SUHU_MIN <= object_temp <= SUHU_MAX):
        return _commit(
            _row(
                "REJECTED_RANGE",
                validation_status="INVALID",
                reason="temperature_out_of_range",
            )
        )
    validation_status = "VALID"

    # 4. resolusi sesi aktif (per perangkat kiosk, bukan per MQTT device_id)
    sessions = _active_sessions(db, calling_device.id_device)

    if len(sessions) > 1:
        return _commit(
            _row(
                "REJECTED_MULTI_SESSION",
                validation_status=validation_status,
                reason="multiple_active_sessions",
            )
        )

    session = sessions[0] if sessions else None
    session_nik = session.NIK if session else None

    # 5. validasi UID (cross-check terhadap pasien sesi)
    uid_reject = _uid_check(db, rfid_uid, session_nik)
    if uid_reject is not None:
        status_, reason_ = uid_reject
        return _commit(
            _row(
                status_,
                validation_status=validation_status,
                reason=reason_,
                session=session,
            )
        )

    # 6. wajib ada sesi aktif
    if session is None:
        return _commit(
            _row(
                "REJECTED_NO_SESSION",
                validation_status=validation_status,
                reason="no_active_session",
            )
        )

    # 7. diterima
    return _commit(_row("ACCEPTED", validation_status=validation_status, session=session))
