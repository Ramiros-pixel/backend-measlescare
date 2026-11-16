from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ---------- Auth ----------
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    NIK: str = Field(min_length=1, max_length=16, examples=["3201234567890001"])
    password: str = Field(min_length=1, examples=["rahasia123"])


# ---------- User ----------
class UserBase(BaseModel):
    NIK: str = Field(min_length=16, max_length=16, examples=["3201234567890001"])
    Name: str = Field(min_length=1, max_length=100, examples=["Bagas Pratama"])
    Tempat_Tgl_Lahir: str | None = Field(default=None, max_length=150)
    Golongan_darah: str | None = Field(default=None, pattern="^(A|B|AB|O)$")
    Email: str | None = Field(default=None, max_length=255)
    Alamat: str | None = None
    id_Role: str = Field(min_length=1, max_length=10, examples=["R2"])


class UserCreate(UserBase):
    password: str = Field(min_length=6, examples=["rahasia123"])


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    NIK: str
    Name: str
    Tempat_Tgl_Lahir: str | None = None
    Golongan_darah: str | None = None
    Email: str | None = None
    Alamat: str | None
    id_Role: str
    role_name: str | None = None


# ---------- Gejala ----------
class GejalaCreate(BaseModel):
    Batuk: str | None = Field(
        default=None, max_length=20, examples=["kering"]
    )
    Suhu: float | None = Field(default=None, ge=30, le=45, examples=[38.5])


class GejalaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_gejala: str
    NIK: str
    Batuk: str | None
    Suhu: float | None
    Tanggal: datetime


# ---------- Camera ----------
class CameraCreate(BaseModel):
    Status: str | None = Field(default=None, max_length=50, examples=["mengantuk"])
    id_gejala: str = Field(min_length=1, max_length=20)


class CameraOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_cam: str
    Status: str | None
    id_gejala: str
    Tanggal: datetime


# ---------- Status / Report ----------
class StatusCreate(BaseModel):
    id_cam: str = Field(min_length=1, max_length=20)


class StatusOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_rept: str
    id_cam: str


# ---------- Umum ----------
class HistoryGejalaOut(BaseModel):
    """Item history gabungan gejala + deteksi kamera + laporan."""

    model_config = ConfigDict(from_attributes=True)

    id_gejala: str
    NIK: str
    nama_user: str | None = None
    Batuk: str | None
    Suhu: float | None
    Tanggal: datetime
    cameras: list[dict[str, Any]] = []


class Message(BaseModel):
    detail: str
