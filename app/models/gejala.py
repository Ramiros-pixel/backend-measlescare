from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

class Role(Base):
    __tablename__ = "Role"

    id_Role: Mapped[str] = mapped_column(String(10), primary_key=True)
    Name: Mapped[str] = mapped_column(String(50), nullable=False)

    users: Mapped[list["User"]] = relationship(back_populates="role")


class User(Base):
    __tablename__ = "Users"

    NIK: Mapped[str] = mapped_column(String(16), primary_key=True)
    Name: Mapped[str] = mapped_column(String(100), nullable=False)
    Tempat_Tgl_Lahir: Mapped[str | None] = mapped_column(String(150), nullable=True)
    Golongan_darah: Mapped[str | None] = mapped_column(String(2), nullable=True)
    Email: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    Alamat: Mapped[str | None] = mapped_column(Text)
    # Kolom tambahan (di luar ERD awal): password di-hash bcrypt
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    id_Role: Mapped[str] = mapped_column(
        String(10), ForeignKey("Role.id_Role"), nullable=False
    )

    role: Mapped["Role"] = relationship(back_populates="users")
    gejala: Mapped[list["Gejala"]] = relationship(back_populates="user")
    cards: Mapped[list["PatientCard"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Gejala(Base):
    __tablename__ = "Gejala"

    id_gejala: Mapped[str] = mapped_column(String(20), primary_key=True)
    NIK: Mapped[str] = mapped_column(ForeignKey("Users.NIK"), nullable=False)
    Batuk: Mapped[str | None] = mapped_column(String(20))
    Suhu: Mapped[float | None] = mapped_column(Float)
    Tanggal: Mapped[object] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="gejala")
    cameras: Mapped[list["Camera"]] = relationship(back_populates="gejala")


class Camera(Base):
    __tablename__ = "Camera"

    id_cam: Mapped[str] = mapped_column(String(20), primary_key=True)
    Status: Mapped[str | None] = mapped_column(String(50))
    id_gejala: Mapped[str] = mapped_column(
        ForeignKey("Gejala.id_gejala"), nullable=False
    )
    Tanggal: Mapped[object] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    gejala: Mapped["Gejala"] = relationship(back_populates="cameras")
    reports: Mapped[list["Status"]] = relationship(back_populates="camera")


class KioskDevice(Base):
    __tablename__ = "kioskdevices"

    id_device: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )
    nama_device: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    secret_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    aktif: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )


class KioskSession(Base):
    __tablename__ = "kiosksessions"

    id_session: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )
    id_device: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("kioskdevices.id_device"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )
    revoked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

class Status(Base):
    __tablename__ = "Status"

    id_rept: Mapped[str] = mapped_column(String(20), primary_key=True)
    id_cam: Mapped[str] = mapped_column(ForeignKey("Camera.id_cam"), nullable=False)

    camera: Mapped["Camera"] = relationship(back_populates="reports")


class PatientCard(Base):
    __tablename__ = "patient_cards"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    rfid_uid: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    NIK: Mapped[str] = mapped_column(ForeignKey("Users.NIK"), nullable=False)
    created_at: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="cards")
