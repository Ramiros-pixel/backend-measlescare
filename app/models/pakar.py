
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


# 1. MASTER GEJALA
# Menyimpan daftar gejala yang digunakan sistem pakar.

class MasterGejala(Base):
    __tablename__ = "master_gejala"

    kode_gejala: Mapped[str] = mapped_column(
        String(30),
        primary_key=True,
    )

    nama_gejala: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    deskripsi: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    jenis: Mapped[str] = mapped_column(
        Enum("GEJALA", "TANDA_BAHAYA", "PARAMETER"),
        nullable=False,
        default="GEJALA",
    )

    aktif: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )


# 2. JAWABAN GEJALA
# Menyimpan jawaban kuesioner setiap pemeriksaan.
# nilai: 1 = Ya, 0 = Tidak.

class JawabanGejala(Base):
    __tablename__ = "jawaban_gejala"

    __table_args__ = (
        UniqueConstraint(
            "id_gejala",
            "kode_gejala",
            name="uq_jawaban_pemeriksaan_gejala",
        ),
    )

    id_jawaban: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    id_gejala: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("Gejala.id_gejala"),
        nullable=False,
    )

    kode_gejala: Mapped[str] = mapped_column(
        String(30),
        ForeignKey("master_gejala.kode_gejala"),
        nullable=False,
    )

    nilai: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    tanggal_input: Mapped[object] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )


# 3. ATURAN PAKAR
# Menyimpan aturan IF-THEN sistem pakar.

class AturanPakar(Base):
    __tablename__ = "aturan_pakar"

    id_aturan: Mapped[str] = mapped_column(
        String(20),
        primary_key=True,
    )

    nama_aturan: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    kesimpulan: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    prioritas: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    keterangan: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    aktif: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )


# 4. DETAIL ATURAN PAKAR
# Menyimpan kondisi gejala untuk setiap aturan.

class AturanPakarDetail(Base):
    __tablename__ = "aturan_pakar_detail"

    id_detail: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    id_aturan: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("aturan_pakar.id_aturan"),
        nullable=False,
    )

    kode_gejala: Mapped[str] = mapped_column(
        String(30),
        ForeignKey("master_gejala.kode_gejala"),
        nullable=False,
    )

    operator_kondisi: Mapped[str] = mapped_column(
        Enum("=", ">", "<", ">=", "<="),
        nullable=False,
        default="=",
    )

    nilai_kondisi: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )


# 5. HASIL PAKAR
# Menyimpan hasil evaluasi sistem pakar setiap pemeriksaan.

class HasilPakar(Base):
    __tablename__ = "hasil_pakar"

    id_hasil: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    id_gejala: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("Gejala.id_gejala"),
        nullable=False,
        unique=True,
    )

    hasil: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    skor: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    ringkasan: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    tanggal_evaluasi: Mapped[object] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
