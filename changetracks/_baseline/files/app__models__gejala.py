from datetime import date

from sqlalchemy import Date, DateTime, Float, ForeignKey, String, Text, func
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
    Tgl_lahir: Mapped[date] = mapped_column(Date, nullable=False)
    Alamat: Mapped[str | None] = mapped_column(Text)
    # Kolom tambahan (di luar ERD awal): password di-hash bcrypt
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    id_Role: Mapped[str] = mapped_column(
        String(10), ForeignKey("Role.id_Role"), nullable=False
    )

    role: Mapped["Role"] = relationship(back_populates="users")
    gejala: Mapped[list["Gejala"]] = relationship(back_populates="user")


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


class Status(Base):
    __tablename__ = "Status"

    id_rept: Mapped[str] = mapped_column(String(20), primary_key=True)
    id_cam: Mapped[str] = mapped_column(ForeignKey("Camera.id_cam"), nullable=False)

    camera: Mapped["Camera"] = relationship(back_populates="reports")
