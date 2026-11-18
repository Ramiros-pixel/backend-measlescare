"""
Seeder data lengkap & deterministik untuk MeaslesCare Backend.

Cara menjalankan (dari folder backend-measlescare, gunakan interpreter yang
sudah menginstal `requirements.txt`):

    python -m app.seeders.seed_all

Fungsi:
- Membuat seluruh tabel jika belum tersedia (termasuk kolom hasil migrasi).
- Mengisi SEMUA tabel dengan data dummy yang SAMA di device manapun,
  karena memakai ID tetap (bukan uuid acak) dan tanggal tetap.
- Idempoten: aman dijalankan berulang kali; tidak menduplikasi / menghapus data.

Data dummy (khusus pengujian lokal / demo non-produksi):
    Akun admin dan user pengujian diinisialisasi untuk kebutuhan evaluasi lokal.
    Seluruh password dan secret di-hash menggunakan bcrypt sebelum disimpan ke database.
    Kredensial ini TIDAK BOLEH digunakan pada lingkungan produksi publik.
"""

from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.migrations import migrate_database
from app.db.session import Base, SessionLocal, engine
from app.models.gejala import (
    Camera,
    Gejala,
    KioskDevice,
    PatientCard,
    Role,
    Status,
    User,
)
from app.models.pakar import (
    AturanPakar,
    AturanPakarDetail,
    HasilPakar,
    JawabanGejala,
    MasterGejala,
)
from app.seeders.pakar_seeder import seed_aturan_pakar, seed_master_gejala


# ---------------------------------------------------------------------------
# DATA DUMMY (DETERMINISTIK)
# ---------------------------------------------------------------------------

DUMMY_USERS = [
    {
        "NIK": "3201234567890002",
        "Name": "Bagas Pratama",
        "Tempat_Tgl_Lahir": "Bandung, 1998-03-12",
        "Golongan_darah": "O",
        "Email": "bagas@example.com",
        "Alamat": "Jl. Merdeka No. 1, Bandung",
        "password": "rahasia123",
        "id_Role": "R2",
    },
    {
        "NIK": "3201234567890003",
        "Name": "Siti Rahayu",
        "Tempat_Tgl_Lahir": "Jakarta, 2001-07-25",
        "Golongan_darah": "A",
        "Email": "siti@example.com",
        "Alamat": "Jl. Sudirman No. 45, Jakarta",
        "password": "rahasia123",
        "id_Role": "R2",
    },
    {
        "NIK": "3201234567890004",
        "Name": "Dewi Lestari",
        "Tempat_Tgl_Lahir": "Surabaya, 1995-11-02",
        "Golongan_darah": "B",
        "Email": "dewi@example.com",
        "Alamat": "Jl. Pemuda No. 8, Surabaya",
        "password": "rahasia123",
        "id_Role": "R2",
    },
]

# id_gejala & id_cam & id_rept harus persis 20 karakter.
DUMMY_GEJALA = [
    {"id_gejala": "G0000000000000000001", "NIK": "3201234567890002",
     "Batuk": "kering", "Suhu": 38.5, "Tanggal": datetime(2026, 11, 1, 9, 30, 0)},
    {"id_gejala": "G0000000000000000002", "NIK": "3201234567890002",
     "Batuk": "berdahak", "Suhu": 39.0, "Tanggal": datetime(2026, 11, 5, 14, 10, 0)},
    {"id_gejala": "G0000000000000000003", "NIK": "3201234567890003",
     "Batuk": None, "Suhu": 37.2, "Tanggal": datetime(2026, 11, 8, 8, 0, 0)},
    {"id_gejala": "G0000000000000000004", "NIK": "3201234567890004",
     "Batuk": "parah", "Suhu": 40.0, "Tanggal": datetime(2026, 11, 10, 19, 45, 0)},
]

DUMMY_CAMERA = [
    {"id_cam": "C0000000000000000001", "Status": "mengantuk",
     "id_gejala": "G0000000000000000001", "Tanggal": datetime(2026, 11, 1, 9, 40, 0)},
    {"id_cam": "C0000000000000000002", "Status": "merah",
     "id_gejala": "G0000000000000000003", "Tanggal": datetime(2026, 11, 8, 8, 10, 0)},
    {"id_cam": "C0000000000000000003", "Status": "bengkak",
     "id_gejala": "G0000000000000000004", "Tanggal": datetime(2026, 11, 10, 19, 55, 0)},
]

DUMMY_STATUS = [
    {"id_rept": "R0000000000000000001", "id_cam": "C0000000000000000001"},
    {"id_rept": "R0000000000000000002", "id_cam": "C0000000000000000002"},
]

DUMMY_PATIENT_CARDS = [
    {"rfid_uid": "E0040100ABCDEF0001", "NIK": "3201234567890002"},
    {"rfid_uid": "E0040100ABCDEF0002", "NIK": "3201234567890003"},
    {"rfid_uid": "E0040100ABCDEF0003", "NIK": "3201234567890004"},
]

# Kiosk device dummy (secret ditampilkan agar bisa dikonfigurasi di device lain).
DUMMY_KIOSK = {
    "id_device": "c0ffee00-0000-4000-8000-000000000001",
    "nama_device": "MeaslesCare Kiosk Demo 01",
    "secret": "kiosk-secret-demo-2026",
}

# Jawaban kuesioner sistem pakar per catatan gejala.
# kode_gejala harus sudah ada di master_gejala.
DUMMY_JAWABAN = [
    ("G0000000000000000001", "DEMAM", 1),
    ("G0000000000000000001", "BATUK", 1),
    ("G0000000000000000001", "RUAM", 1),
    ("G0000000000000000002", "DEMAM", 1),
    ("G0000000000000000002", "MATA_MERAH", 1),
    ("G0000000000000000003", "DEMAM", 0),
    ("G0000000000000000004", "SESAK", 1),
]

# Hasil sistem pakar per catatan gejala (id_gejala unik).
DUMMY_HASIL_PAKAR = [
    {"id_gejala": "G0000000000000000001",
     "hasil": "CLINICAL_MEASLES_PATTERN", "skor": 3,
     "ringkasan": "Demam + ruam + batuk sesuai pola klinis campak.",
     "tanggal_evaluasi": datetime(2026, 11, 1, 9, 45, 0)},
    {"id_gejala": "G0000000000000000002",
     "hasil": "CLINICAL_MEASLES_PATTERN", "skor": 3,
     "ringkasan": "Demam + ruam + konjungtivitis sesuai pola klinis campak.",
     "tanggal_evaluasi": datetime(2026, 11, 5, 14, 20, 0)},
    {"id_gejala": "G0000000000000000004",
     "hasil": "SAFETY_ALERT", "skor": 1,
     "ringkasan": "Terdapat tanda bahaya (kesulitan bernapas).",
     "tanggal_evaluasi": datetime(2026, 11, 10, 20, 0, 0)},
]


# ---------------------------------------------------------------------------
# HELPER IDEMPOTEN
# ---------------------------------------------------------------------------

def _add_if_missing(db: Session, model, pk_value: object, fields: dict) -> int:
    """Insert satu baris bila belum ada. Kembalikan 1 = baru, 0 = sudah ada."""
    if db.get(model, pk_value) is not None:
        return 0
    db.add(model(**fields))
    return 1


# ---------------------------------------------------------------------------
# SEEDER PER TABEL
# ---------------------------------------------------------------------------

def seed_roles(db: Session) -> int:
    return sum(
        _add_if_missing(db, Role, rid, {"id_Role": rid, "Name": name})
        for rid, name in (("R1", "Admin"), ("R2", "User"))
    )


def seed_admin(db: Session) -> int:
    if db.get(User, "admin") is not None:
        return 0
    db.add(User(
        NIK="admin",
        Name="Administrator",
        Tempat_Tgl_Lahir="-",
        Golongan_darah=None,
        Email=None,
        Alamat="-",
        password=hash_password("admin123"),
        id_Role="R1",
    ))
    return 1


def seed_users(db: Session) -> int:
    total = 0
    for u in DUMMY_USERS:
        fields = dict(u)
        fields["password"] = hash_password(u["password"])
        total += _add_if_missing(db, User, u["NIK"], fields)
    return total


def seed_gejala(db: Session) -> int:
    return sum(
        _add_if_missing(db, Gejala, g["id_gejala"], g)
        for g in DUMMY_GEJALA
    )


def seed_camera(db: Session) -> int:
    return sum(
        _add_if_missing(db, Camera, c["id_cam"], c)
        for c in DUMMY_CAMERA
    )


def seed_status(db: Session) -> int:
    return sum(
        _add_if_missing(db, Status, s["id_rept"], s)
        for s in DUMMY_STATUS
    )


def seed_patient_cards(db: Session) -> int:
    total = 0
    for card in DUMMY_PATIENT_CARDS:
        exists = (
            db.query(PatientCard)
            .filter(PatientCard.rfid_uid == card["rfid_uid"])
            .first()
        )
        if exists is None:
            db.add(PatientCard(**card))
            total += 1
    return total


def seed_kiosk_device(db: Session) -> int:
    k = DUMMY_KIOSK
    if db.get(KioskDevice, k["id_device"]) is not None:
        return 0
    db.add(KioskDevice(
        id_device=k["id_device"],
        nama_device=k["nama_device"],
        secret_hash=hash_password(k["secret"]),
        aktif=True,
    ))
    return 1


def seed_jawaban_gejala(db: Session) -> int:
    total = 0
    for id_gejala, kode_gejala, nilai in DUMMY_JAWABAN:
        exists = (
            db.query(JawabanGejala)
            .filter(
                JawabanGejala.id_gejala == id_gejala,
                JawabanGejala.kode_gejala == kode_gejala,
            )
            .first()
        )
        if exists is None:
            db.add(JawabanGejala(
                id_gejala=id_gejala,
                kode_gejala=kode_gejala,
                nilai=nilai,
            ))
            total += 1
    return total


def seed_hasil_pakar(db: Session) -> int:
    total = 0
    for h in DUMMY_HASIL_PAKAR:
        exists = (
            db.query(HasilPakar)
            .filter(HasilPakar.id_gejala == h["id_gejala"])
            .first()
        )
        if exists is not None:
            continue
        db.add(HasilPakar(
            id_gejala=h["id_gejala"],
            hasil=h["hasil"],
            skor=h["skor"],
            ringkasan=h["ringkasan"],
            tanggal_evaluasi=h["tanggal_evaluasi"],
        ))
        total += 1
    return total


# ---------------------------------------------------------------------------
# ORKESTRATOR
# ---------------------------------------------------------------------------

def run_all_seeders(db_session: Session | None = None) -> dict:
    """Jalankan seluruh seeder dengan pengurutan dependensi aman (idempoten)."""

    # 1. Buat tabel yang belum tersedia + migrasi kolom tambahan.
    Base.metadata.create_all(bind=engine)
    migrate_database()

    db = db_session if db_session is not None else SessionLocal()
    counts = {}
    try:
        def _count(tbl) -> int:
            return db.query(func.count()).select_from(tbl).scalar() or 0

        mg_before = _count(MasterGejala)
        at_before = _count(AturanPakar)
        det_before = _count(AturanPakarDetail)

        # Tahap 1: Role (Prasyarat Users)
        counts["Role"] = seed_roles(db)
        db.flush()

        # Tahap 2: Users (Admin & Dummy Patients - Prasyarat Gejala & PatientCard)
        counts["Users (admin)"] = seed_admin(db)
        counts["Users (dummy)"] = seed_users(db)
        db.flush()

        # Tahap 3: Master Gejala & Aturan Pakar (Prasyarat JawabanGejala & AturanPakarDetail)
        seed_master_gejala(db, commit=False)
        seed_aturan_pakar(db, commit=False)
        counts["MasterGejala"] = _count(MasterGejala) - mg_before
        counts["AturanPakar+Detail"] = (
            (_count(AturanPakar) - at_before)
            + (_count(AturanPakarDetail) - det_before)
        )

        # Tahap 4: Gejala (Prasyarat Camera, JawabanGejala, HasilPakar)
        counts["Gejala"] = seed_gejala(db)
        db.flush()

        # Tahap 5: Camera, PatientCards, KioskDevice
        counts["Camera"] = seed_camera(db)
        db.flush()
        counts["Status"] = seed_status(db)
        counts["PatientCard"] = seed_patient_cards(db)
        counts["KioskDevice"] = seed_kiosk_device(db)
        db.flush()

        # Tahap 6: Jawaban Gejala & Hasil Pakar (Tabel anak dari Gejala & MasterGejala)
        counts["JawabanGejala"] = seed_jawaban_gejala(db)
        counts["HasilPakar"] = seed_hasil_pakar(db)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        if db_session is None:
            db.close()

    print("\n=== SEEDER DATA LENGKAP MEASLESCARE ===")
    print("Status: idempoten (baru ditambahkan = >0, sudah ada = 0).")
    for nama, jumlah in counts.items():
        print(f"{nama:<24}: {jumlah} baris baru")
    print("\nStatus Kredensial Dummy (Khusus Pengujian Non-Produksi):")
    print("  [OK] Akun Administrator lokal dikonfigurasi (password terenkripsi bcrypt).")
    for u in DUMMY_USERS:
        print(f"  [OK] Akun Pasien {u['Name']} (NIK: {u['NIK']}) dikonfigurasi (password terenkripsi bcrypt).")
    print(f"  [OK] Perangkat Kiosk Demo terdaftar (device_id: {DUMMY_KIOSK['id_device']}, secret terenkripsi).")
    print("  Catatan Keamanan: Kredensial dummy hanya untuk pengujian lokal/demo internal non-produksi.")
    print("Seeder selesai.")
    return counts


def main() -> None:
    run_all_seeders()


if __name__ == "__main__":
    main()