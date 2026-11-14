
from sqlalchemy.orm import Session

from app.models.pakar import MasterGejala


# DATA MASTER GEJALA MEASLESCARE

MASTER_GEJALA = [
    {
        "kode_gejala": "DEMAM",
        "nama_gejala": "Demam",
        "jenis": "GEJALA",
        "deskripsi": "Pasien mengalami demam.",
    },
    {
        "kode_gejala": "BATUK",
        "nama_gejala": "Batuk",
        "jenis": "GEJALA",
        "deskripsi": "Pasien mengalami batuk.",
    },
    {
        "kode_gejala": "PILEK",
        "nama_gejala": "Pilek",
        "jenis": "GEJALA",
        "deskripsi": "Pasien mengalami pilek atau coryza.",
    },
    {
        "kode_gejala": "MATA_MERAH",
        "nama_gejala": "Mata Merah",
        "jenis": "GEJALA",
        "deskripsi": "Gejala konjungtivitis.",
    },
    {
        "kode_gejala": "RUAM",
        "nama_gejala": "Ruam Kulit",
        "jenis": "GEJALA",
        "deskripsi": "Terdapat ruam pada kulit.",
    },
    {
        "kode_gejala": "RUAM_MENYELURUH",
        "nama_gejala": "Ruam Menyeluruh",
        "jenis": "GEJALA",
        "deskripsi": "Ruam tersebar pada tubuh.",
    },
    {
        "kode_gejala": "KOPLIK",
        "nama_gejala": "Bercak Koplik",
        "jenis": "GEJALA",
        "deskripsi": "Terdapat bercak Koplik.",
    },
    {
        "kode_gejala": "DIARE",
        "nama_gejala": "Diare",
        "jenis": "GEJALA",
        "deskripsi": "Pasien mengalami diare.",
    },
    {
        "kode_gejala": "SESAK",
        "nama_gejala": "Sesak Napas",
        "jenis": "TANDA_BAHAYA",
        "deskripsi": "Pasien mengalami kesulitan bernapas.",
    },
    {
        "kode_gejala": "KEJANG",
        "nama_gejala": "Kejang",
        "jenis": "TANDA_BAHAYA",
        "deskripsi": "Pasien mengalami kejang.",
    },
    {
        "kode_gejala": "PENURUNAN_KESADARAN",
        "nama_gejala": "Penurunan Kesadaran",
        "jenis": "TANDA_BAHAYA",
        "deskripsi": "Terdapat perubahan tingkat kesadaran.",
    },
    {
        "kode_gejala": "SUHU",
        "nama_gejala": "Suhu Tubuh",
        "jenis": "PARAMETER",
        "deskripsi": "Nilai suhu diambil dari kolom Gejala.Suhu.",
    },
]


# SEEDER MASTER GEJALA

def seed_master_gejala(db: Session) -> None:
    """
    Memasukkan master gejala yang belum tersedia.

    Seeder aman dijalankan berulang kali:
    data dengan kode yang sudah ada tidak akan diduplikasi
    atau ditimpa.
    """

    jumlah_baru = 0
    jumlah_sudah_ada = 0

    try:
        for item in MASTER_GEJALA:

            existing = db.get(
                MasterGejala,
                item["kode_gejala"],
            )

            if existing is None:
                db.add(
                    MasterGejala(**item)
                )
                jumlah_baru += 1
            else:
                jumlah_sudah_ada += 1

        db.commit()

        print(" MEASLESCARE - MASTER GEJALA SEEDER")
        print(f"Data baru       : {jumlah_baru}")
        print(f"Sudah tersedia  : {jumlah_sudah_ada}")
        print(f"Total master    : {len(MASTER_GEJALA)}")
        print("Seeder berhasil dijalankan.")

    except Exception:
        db.rollback()
        raise
