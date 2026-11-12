"""Schema Pydantic untuk modul face recognition."""

from pydantic import BaseModel, Field


# ---------- Capture ----------
class CaptureRequest(BaseModel):
    """Satu frame kamera (JPEG base64) dikirim berkala oleh frontend."""

    image: str = Field(
        examples=["data:image/jpeg;base64,/9j/4AAQ... atau /9j/4AAQ..."],
        description="Frame JPEG base64, dengan atau tanpa prefix data URL.",
    )


class CaptureOut(BaseModel):
    nik: str
    stored: int          # jumlah sampel tersimpan saat ini
    target: int          # target sampel (SAMPLE_TARGET)
    face_detected: bool  # apakah frame terakhir memuat wajah
    completed: bool      # True bila stored >= target
    message: str


# ---------- Train ----------
class TrainOut(BaseModel):
    status: str = "trained"
    nik: str
    my_samples: int      # sampel milik user ini
    total_samples: int   # total sampel SEMUA user yang ikut training
    total_users: int     # jumlah user (label) dalam model
    message: str


class ModelStatus(BaseModel):
    model_exists: bool
    model_users: int = 0          # jumlah user (label) di dalam model
    total_samples: int = 0        # sampel yang IKUT training (user terdaftar)
    unlabeled_samples: int = 0    # sampel di folder tanpa user terdaftar (dilewati)
    my_samples: int = 0           # sampel milik user yang login
    target: int = 0               # target sampel untuk boleh training
    trained_at: str | None = None


class RetrainOut(BaseModel):
    status: str = "trained"
    total_samples: int
    total_users: int
    message: str


# ---------- Recognize / login wajah ----------
class RecognizeRequest(BaseModel):
    image: str = Field(
        examples=["data:image/jpeg;base64,/9j/4AAQ... atau /9j/4AAQ..."],
        description="Frame JPEG base64, dengan atau tanpa prefix data URL.",
    )


class RecognizeOut(BaseModel):
    recognized: bool
    user_id: str | None = None
    name: str | None = None
    confidence: float | None = Field(
        default=None,
        description="LBPH distance — semakin kecil semakin mirip (<= 70 dianggap cocok).",
    )


class FaceLoginRequest(BaseModel):
    image: str


class TokenFace(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOutFace"


class UserOutFace(BaseModel):
    NIK: str
    Name: str
    role_name: str | None = None


TokenFace.model_rebuild()
