import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.security import DbSession, verify_password
from app.core.rate_limit import rate_limit_sensor_reading, rate_limit_session_create
from app.models.gejala import Gejala, User
from app.models.kiosk_session import KioskDevice, KioskSession
from app.routers.face import _decode_frame
from app.services import face_engine
from app.services.sensor_service import ingest_sensor_reading

router = APIRouter(prefix="/kiosk-session", tags=["Kiosk Session"])


class CreateSessionIn(BaseModel):
    NIK: str = Field(min_length=16, max_length=16)
    image: str = Field(min_length=20)


class IdentifyFaceSessionIn(BaseModel):
    image: str = Field(min_length=20, description="Citra wajah pasien base64 JPEG/PNG")


class CreateGejalaIn(BaseModel):
    Suhu: float | None = Field(default=None, ge=30, le=45)
    Batuk: str | None = Field(default=None, max_length=20)


class SensorReadingIn(BaseModel):
    event_id: str = Field(min_length=1, max_length=64)
    device_id: str = Field(min_length=1, max_length=64)
    rfid_uid: str | None = Field(default=None, max_length=64)
    object_temp: float | None = None
    ambient_temp: float | None = None
    uptime_ms: int | None = None
    source_format: str = Field(default="esp32", max_length=20)
    raw_payload: str | None = None


def _device_from_key(db: Session, x_kiosk_key: str | None) -> KioskDevice:
    if not x_kiosk_key:
        raise HTTPException(status_code=401, detail="Kiosk tidak terautentikasi")
    devices = db.query(KioskDevice).filter(KioskDevice.aktif.is_(True)).all()
    for device in devices:
        if verify_password(x_kiosk_key, device.secret_hash):
            return device
    raise HTTPException(status_code=401, detail="Kunci perangkat kiosk tidak valid")


def _session_from_token(
    db: Session,
    token: str | None,
    calling_device: KioskDevice | None = None,
) -> tuple[KioskSession, str]:
    if not token:
        raise HTTPException(status_code=401, detail="Sesi kiosk tidak ditemukan")

    # Format token: id_session|NIK|secret. Hash seluruh token disimpan di DB.
    parts = token.split("|", 2)
    if len(parts) != 3:
        raise HTTPException(status_code=401, detail="Token sesi kiosk tidak valid")
    session_id, nik, _secret = parts

    session = db.get(KioskSession, session_id)
    if session is None:
        raise HTTPException(status_code=401, detail="Sesi kiosk tidak ditemukan")

    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    if not hmac.compare_digest(session.token_hash, token_hash):
        raise HTTPException(status_code=401, detail="Token sesi kiosk tidak valid")
    if session.revoked:
        raise HTTPException(status_code=401, detail="Sesi kiosk sudah ditutup")
    if session.expires_at <= datetime.utcnow():
        raise HTTPException(status_code=401, detail="Sesi kiosk sudah kedaluwarsa")

    device = db.get(KioskDevice, session.id_device)
    if device is None or not device.aktif:
        raise HTTPException(status_code=401, detail="Perangkat kiosk tidak aktif")

    # Session Device Binding: Validasi bahwa sesi digunakan oleh perangkat pembuatnya
    if calling_device is not None:
        if session.id_device != calling_device.id_device:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Sesi tidak terikat pada perangkat kiosk ini",
            )

    return session, nik


@router.post("/create", dependencies=[Depends(rate_limit_session_create)])
def create_kiosk_session(
    payload: CreateSessionIn,
    db: DbSession,
    x_kiosk_key: str | None = Header(default=None, alias="X-Kiosk-Key"),
):
    device = _device_from_key(db, x_kiosk_key)

    patient = db.get(User, payload.NIK)
    if patient is None or patient.id_Role != "R2":
        raise HTTPException(status_code=404, detail="Pasien tidak ditemukan")

    # Wajah diperiksa ulang di backend. Jangan percaya status match dari frontend.
    frame = _decode_frame(payload.image)
    result = face_engine.recognize(frame)
    if not result or result.get("user_id") != patient.NIK:
        raise HTTPException(status_code=403, detail="Verifikasi wajah gagal untuk pasien ini")

    session_id = str(uuid.uuid4())
    secret = secrets.token_urlsafe(32)
    token = f"{session_id}|{patient.NIK}|{secret}"
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

    row = KioskSession(
        id_session=session_id,
        id_device=device.id_device,
        NIK=patient.NIK,
        token_hash=token_hash,
        expires_at=datetime.utcnow() + timedelta(minutes=20),
        revoked=False,
    )
    db.add(row)
    db.commit()

    return {
        "access_token": token,
        "token_type": "Kiosk",
        "expires_in": 1200,
        "patient": {"NIK": patient.NIK, "Name": patient.Name},
    }


@router.post("/identify-face", dependencies=[Depends(rate_limit_session_create)])
def identify_face_and_create_session(
    payload: IdentifyFaceSessionIn,
    db: DbSession,
    x_kiosk_key: str | None = Header(default=None, alias="X-Kiosk-Key"),
):
    """
    Identifikasi pasien langsung dari citra wajah (OpenCV LBPH) server-side
    dan langsung menerbitkan sesi kiosk jika wajah dikenali dan terdaftar.
    Tidak menerima klaim NIK dari client (anti-spoofing).
    """
    device = _device_from_key(db, x_kiosk_key)

    frame = _decode_frame(payload.image)
    result = face_engine.recognize(frame)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wajah tidak dikenali atau belum terdaftar",
        )

    recognized_nik = result["user_id"]
    confidence = result["confidence"]

    patient = db.get(User, recognized_nik)
    if patient is None or patient.id_Role != "R2":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pasien hasil pengenalan wajah tidak ditemukan atau bukan pasien terdaftar",
        )

    session_id = str(uuid.uuid4())
    secret = secrets.token_urlsafe(32)
    token = f"{session_id}|{patient.NIK}|{secret}"
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

    row = KioskSession(
        id_session=session_id,
        id_device=device.id_device,
        NIK=patient.NIK,
        token_hash=token_hash,
        expires_at=datetime.utcnow() + timedelta(minutes=20),
        revoked=False,
    )
    db.add(row)
    db.commit()

    return {
        "access_token": token,
        "token_type": "Kiosk",
        "expires_in": 1200,
        "patient": {
            "NIK": patient.NIK,
            "Name": patient.Name,
            "Tempat_Tgl_Lahir": patient.Tempat_Tgl_Lahir,
            "Golongan_darah": patient.Golongan_darah,
            "Email": patient.Email,
            "Alamat": patient.Alamat,
        },
        "confidence": confidence,
    }


@router.post("/gejala", status_code=201)
def create_gejala_from_kiosk(
    payload: CreateGejalaIn,
    db: DbSession,
    x_kiosk_session: str | None = Header(default=None, alias="X-Kiosk-Session"),
    x_kiosk_key: str | None = Header(default=None, alias="X-Kiosk-Key"),
):
    calling_device = _device_from_key(db, x_kiosk_key)
    _session, nik = _session_from_token(db, x_kiosk_session, calling_device=calling_device)

    patient = db.get(User, nik)
    if patient is None or patient.id_Role != "R2":
        raise HTTPException(status_code=404, detail="Pasien sesi tidak ditemukan")

    row = Gejala(
        id_gejala=uuid.uuid4().hex[:20],
        NIK=nik,
        Batuk=payload.Batuk,
        Suhu=payload.Suhu,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.post("/revoke")
def revoke_kiosk_session(
    db: DbSession,
    x_kiosk_session: str | None = Header(default=None, alias="X-Kiosk-Session"),
    x_kiosk_key: str | None = Header(default=None, alias="X-Kiosk-Key"),
):
    """Cabut / tutup sesi kiosk aktif."""
    calling_device = _device_from_key(db, x_kiosk_key)
    session, _nik = _session_from_token(db, x_kiosk_session, calling_device=calling_device)
    session.revoked = True
    db.commit()
    return {"message": "Sesi kiosk berhasil ditutup", "revoked": True}


@router.post("/reading", dependencies=[Depends(rate_limit_sensor_reading)])
def ingest_sensor_reading_endpoint(
    payload: SensorReadingIn,
    db: DbSession,
    x_kiosk_key: str | None = Header(default=None, alias="X-Kiosk-Key"),
):
    """Endpoint internal telemetri sensor (dipanggil bridge, bukan publik).

    Autentikasi perangkat via X-Kiosk-Key; identitas pasien diambil dari
    sesi aktif perangkat (bukan dari rfid_uid). Seluruh keputusan status
    direkam di tabel sensor_readings.
    """
    device = _device_from_key(db, x_kiosk_key)
    return ingest_sensor_reading(db, payload.model_dump(), device)

