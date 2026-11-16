"""API kiosk untuk menghubungkan RFID, email pasien, dan enrollment wajah.

Gunakan KIOSK_API_KEY di environment backend dan VITE_KIOSK_API_KEY di frontend
hanya untuk demo jaringan tertutup. Untuk produksi, letakkan kiosk di belakang
gateway/perangkat tepercaya; secret yang dikirim browser bukan secret kuat.
"""
import hmac
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.security import DbSession
from app.models.gejala import User, PatientCard
from app.routers.face import _decode_frame
from app.services import face_engine
from app.services.face_engine import SAMPLE_TARGET

router = APIRouter(prefix="/kiosk", tags=["Kiosk"])


def verify_kiosk_key(x_kiosk_key: str | None = Header(default=None)):
    expected = settings.KIOSK_API_KEY
    if not expected or not x_kiosk_key or not hmac.compare_digest(x_kiosk_key, expected):
        raise HTTPException(status_code=401, detail="Kiosk tidak terautentikasi")


class IdentifyRFIDIn(BaseModel):
    rfid_uid: str = Field(min_length=2, max_length=64)


class PatientOut(BaseModel):
    NIK: str
    Name: str
    Tempat_Tgl_Lahir: str | None = None
    Golongan_darah: str | None = None
    Email: str | None = None
    Alamat: str | None = None
    face_samples: int
    face_target: int


class EmailIn(BaseModel):
    NIK: str = Field(min_length=16, max_length=16)
    Email: str

    @field_validator("Email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        import re
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
            raise ValueError("Format email tidak valid")
        return value


class FaceCaptureIn(BaseModel):
    NIK: str = Field(min_length=16, max_length=16)
    image: str

class PatientNIKIn(BaseModel):
    NIK: str = Field(min_length=16, max_length=16)

@router.post("/identify-rfid", response_model=PatientOut, dependencies=[Depends(verify_kiosk_key)])
def identify_rfid(payload: IdentifyRFIDIn, db: DbSession):
    card = db.query(PatientCard).filter(PatientCard.rfid_uid == payload.rfid_uid.strip().upper()).first()
    if card is None:
        raise HTTPException(status_code=404, detail="Kartu RFID belum terdaftar")
    user = db.get(User, card.NIK)
    if user is None:
        raise HTTPException(status_code=404, detail="Data pasien untuk kartu ini tidak ditemukan")
    return PatientOut(
        NIK=user.NIK, Name=user.Name, Tempat_Tgl_Lahir=user.Tempat_Tgl_Lahir,
        Golongan_darah=user.Golongan_darah, Email=user.Email, Alamat=user.Alamat,
        face_samples=face_engine.count_samples(user.NIK), face_target=SAMPLE_TARGET,
    )


@router.post("/email", dependencies=[Depends(verify_kiosk_key)])
def save_email(payload: EmailIn, db: DbSession):
    user = db.get(User, payload.NIK)
    if user is None or user.id_Role != "R2":
        raise HTTPException(status_code=404, detail="Pasien tidak ditemukan")
    duplicate = db.query(User).filter(User.Email == str(payload.Email), User.NIK != payload.NIK).first()
    if duplicate:
        raise HTTPException(status_code=409, detail="Email sudah digunakan akun lain")
    user.Email = str(payload.Email)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email sudah digunakan akun lain")
    return {"success": True, "Email": user.Email}


@router.post("/face/recognize", dependencies=[Depends(verify_kiosk_key)])
def kiosk_face_recognize(payload: FaceCaptureIn, db: DbSession):
    user = db.get(User, payload.NIK)
    if user is None or user.id_Role != "R2":
        raise HTTPException(status_code=404, detail="Pasien tidak ditemukan")
    frame = _decode_frame(payload.image)
    result = face_engine.recognize(frame)
    if result is None:
        return {"recognized": False, "match": False, "user_id": None, "name": None, "confidence": None}
    return {
        "recognized": True,
        "match": result["user_id"] == user.NIK,
        "user_id": result["user_id"],
        "name": result["name"],
        "confidence": result["confidence"],
    }


@router.post("/face/capture", dependencies=[Depends(verify_kiosk_key)])
def kiosk_face_capture(payload: FaceCaptureIn, db: DbSession):
    user = db.get(User, payload.NIK)
    if user is None or user.id_Role != "R2":
        raise HTTPException(status_code=404, detail="Pasien tidak ditemukan")
    frame = _decode_frame(payload.image)
    stored, detected = face_engine.save_sample(user.NIK, frame)
    return {
        "nik": user.NIK, "stored": stored, "target": SAMPLE_TARGET,
        "face_detected": detected, "completed": stored >= SAMPLE_TARGET,
        "message": "Target sampel tercapai." if stored >= SAMPLE_TARGET else
        ("Wajah tertangkap." if detected else "Wajah tidak terdeteksi."),
    }


@router.post("/face/train", dependencies=[Depends(verify_kiosk_key)])
def kiosk_face_train(payload: PatientNIKIn, db: DbSession):
    user = db.get(User, payload.NIK)
    if user is None or user.id_Role != "R2":
        raise HTTPException(status_code=404, detail="Pasien tidak ditemukan")
    stored = face_engine.count_samples(user.NIK)
    if stored < SAMPLE_TARGET:
        raise HTTPException(status_code=400, detail=f"Sampel belum cukup: {stored}/{SAMPLE_TARGET}")
    try:
        result = face_engine.train_model()
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {
        "nik": user.NIK, "my_samples": stored,
        "total_samples": result["total_samples"], "total_users": result["total_users"],
        "message": "Training model selesai.",
    }
