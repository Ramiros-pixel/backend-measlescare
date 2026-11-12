"""
Router face recognition:
  - /face/status      : status sampel & model untuk user yang login
  - /face/capture     : simpan 1 frame wajah (dipanggil berkala oleh browser)
  - /face/train       : training LBPH sinkron (wajib sampel >= target)
  - /face/model       : info model aktif (Admin)
  - /face/retrain     : training ulang penuh (Admin)
  - /face/reset       : hapus sampel user sendiri / user lain (Admin)
  - /face/recognize   : identifikasi siapa dalam 1 frame (tanpa login)
  - /face/login       : login dengan wajah -> JWT
"""

import base64

import cv2
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import (
    AdminUser,
    CurrentUser,
    create_access_token,
    get_db,
    role_name,
)
from app.schemas.face import (
    CaptureOut,
    CaptureRequest,
    FaceLoginRequest,
    ModelStatus,
    RecognizeOut,
    RecognizeRequest,
    RetrainOut,
    TokenFace,
    TrainOut,
    UserOutFace,
)
from app.services import face_engine
from app.services.face_engine import SAMPLE_TARGET
from app.models.gejala import User

router = APIRouter(prefix="/face", tags=["Face Recognition"])


# ==========================================
# Helper
# ==========================================

def _decode_frame(image_b64: str) -> np.ndarray:
    """Decode base64 (boleh dengan prefix data URL) menjadi citra grayscale."""
    raw = image_b64.strip()
    if "," in raw[:64]:  # buang prefix "data:image/jpeg;base64,"
        raw = raw.split(",", 1)[1]
    try:
        buf = base64.b64decode(raw)
        frame = cv2.imdecode(np.frombuffer(buf, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Image base64 tidak valid",
        )
    if frame is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Frame tidak dapat didekode (harus JPEG/PNG base64)",
        )
    return frame


def _model_status(user: User) -> ModelStatus:
    """Status dataset & model untuk seorang user (dipakai /face/status & /face/model)."""
    import json

    from app.db.session import SessionLocal

    model_exists = face_engine.MODEL_PATH.exists()
    model_users = 0
    if model_exists and face_engine.LABEL_PATH.exists():
        with open(face_engine.LABEL_PATH) as f:
            mapping = json.load(f)
        model_users = len(mapping)

    db = SessionLocal()
    try:
        known = {u.NIK for u in db.query(User).all()}
    finally:
        db.close()
    labeled, unlabeled = face_engine.dataset_counts(known)

    return ModelStatus(
        model_exists=model_exists,
        model_users=model_users,
        total_samples=labeled,
        unlabeled_samples=unlabeled,
        my_samples=face_engine.count_samples(user.NIK),
        target=SAMPLE_TARGET,
        trained_at=face_engine.model_trained_at(),
    )


# ==========================================
# Endpoint
# ==========================================

@router.get("/status", response_model=ModelStatus)
def face_status(user: CurrentUser):
    """Status pengumpulan sampel & model untuk user yang sedang login."""
    return _model_status(user)


@router.post("/capture", response_model=CaptureOut)
def capture(payload: CaptureRequest, user: CurrentUser):
    """
    Simpan SATU frame wajah user yang sedang login.
    Frontend memanggil endpoint ini berulang (mis. tiap 100-200 ms) selama
    sesi pengambilan data; tidak ada input ketik sama sekali.
    """
    frame = _decode_frame(payload.image)
    stored, detected = face_engine.save_sample(user.NIK, frame)
    completed = stored >= SAMPLE_TARGET
    return CaptureOut(
        nik=user.NIK,
        stored=stored,
        target=SAMPLE_TARGET,
        face_detected=detected,
        completed=completed,
        message=(
            "Target sampel tercapai, lanjut ke training."
            if completed
            else "Wajah tertangkap, teruskan sesi pengambilan data."
            if detected
            else "Wajah tidak terdeteksi, dekatkan wajah ke kamera."
        ),
    )


@router.post("/train", response_model=TrainOut)
def train(user: CurrentUser):
    """
    Training model LBPH (sinkron). Hanya boleh jika sampel user ini
    sudah mencapai target. Label otomatis dari tabel Users (NIK + Name).
    """
    stored = face_engine.count_samples(user.NIK)
    if stored < SAMPLE_TARGET:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Sampel belum cukup: {stored}/{SAMPLE_TARGET}. Selesaikan capture dulu.",
        )
    try:
        result = face_engine.train_model()
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return TrainOut(
        nik=user.NIK,
        my_samples=face_engine.count_samples(user.NIK),
        total_samples=result["total_samples"],
        total_users=result["total_users"],
        message=(
            f"Training selesai: {result['total_samples']} sampel dari "
            f"{result['total_users']} user. Sekarang Anda bisa login dengan wajah."
        ),
    )


@router.get("/model", response_model=ModelStatus)
def model_info(admin: AdminUser):
    """Info model aktif (khusus Admin)."""
    return _model_status(admin)


@router.post("/retrain", response_model=RetrainOut)
def retrain(admin: AdminUser):
    """Training ulang seluruh dataset tanpa syarat target (khusus Admin)."""
    try:
        result = face_engine.train_model()
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return RetrainOut(
        total_samples=result["total_samples"],
        total_users=result["total_users"],
        message="Training ulang selesai.",
    )


@router.delete("/reset/{nik}", response_model=dict)
def reset_samples(nik: str, user: CurrentUser):
    """
    Hapus seluruh sampel wajah.
    User biasa hanya boleh hapus sampelnya sendiri; Admin bebas.
    """
    from app.core.security import is_admin

    if not is_admin(user) and user.NIK != nik:
        raise HTTPException(status_code=403, detail="Anda hanya boleh menghapus sampel sendiri")

    removed = face_engine.reset_samples(nik)
    return {"detail": f"{removed} sampel dihapus untuk NIK {nik}"}


@router.post("/recognize", response_model=RecognizeOut)
def recognize(payload: RecognizeRequest):
    """
    Identifikasi siapa yang ada dalam satu frame (tanpa perlu login).
    Return recognized=false bila wajah tidak ada / tidak dikenali.
    """
    frame = _decode_frame(payload.image)
    result = face_engine.recognize(frame)
    if result is None:
        return RecognizeOut(recognized=False)
    return RecognizeOut(
        recognized=True,
        user_id=result["user_id"],
        name=result["name"],
        confidence=result["confidence"],
    )


@router.post("/login", response_model=TokenFace)
def face_login(payload: FaceLoginRequest, db: Session = Depends(get_db)):
    """
    Login menggunakan wajah: kirim 1 frame, bila cocok (confidence <=
    CONFIDENCE_THRESHOLD) server mengembalikan JWT + profil user.
    """
    frame = _decode_frame(payload.image)
    result = face_engine.recognize(frame)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Wajah tidak dikenali atau model belum dilatih",
        )

    user = db.get(User, result["user_id"])
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User hasil pengenalan tidak ditemukan di database",
        )

    return TokenFace(
        access_token=create_access_token(nik=user.NIK, id_role=user.id_Role),
        user=UserOutFace(NIK=user.NIK, Name=user.Name, role_name=role_name(db, user.id_Role)),
    )
