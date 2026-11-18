
from sqlalchemy.orm import Session

from app.models.pakar import (
    MasterGejala,
    AturanPakar,
    AturanPakarDetail,
)


# 1. MASTER GEJALA MEASLESCARE

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
        "nama_gejala": "Ruam Makulopapular",
        "jenis": "GEJALA",
        "deskripsi": "Terdapat ruam makulopapular pada kulit.",
    },
    {
        "kode_gejala": "RUAM_MENYELURUH",
        "nama_gejala": "Ruam Menyeluruh",
        "jenis": "GEJALA",
        "deskripsi": "Ruam tersebar secara menyeluruh pada tubuh.",
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


# 2. ATURAN PAKAR

ATURAN_PAKAR = [
    {
        "id_aturan": "R01",
        "nama_aturan": "Clinical Pattern - Batuk",
        "kesimpulan": "CLINICAL_MEASLES_PATTERN",
        "prioritas": 1,
        "keterangan": (
            "Demam, ruam makulopapular, dan batuk."
        ),
        "kondisi": [
            ("DEMAM", "=", "1"),
            ("RUAM", "=", "1"),
            ("BATUK", "=", "1"),
        ],
    },
    {
        "id_aturan": "R02",
        "nama_aturan": "Clinical Pattern - Pilek",
        "kesimpulan": "CLINICAL_MEASLES_PATTERN",
        "prioritas": 1,
        "keterangan": (
            "Demam, ruam makulopapular, dan pilek."
        ),
        "kondisi": [
            ("DEMAM", "=", "1"),
            ("RUAM", "=", "1"),
            ("PILEK", "=", "1"),
        ],
    },
    {
        "id_aturan": "R03",
        "nama_aturan": "Clinical Pattern - Konjungtivitis",
        "kesimpulan": "CLINICAL_MEASLES_PATTERN",
        "prioritas": 1,
        "keterangan": (
            "Demam, ruam makulopapular, dan konjungtivitis."
        ),
        "kondisi": [
            ("DEMAM", "=", "1"),
            ("RUAM", "=", "1"),
            ("MATA_MERAH", "=", "1"),
        ],
    },
    {
        "id_aturan": "R04",
        "nama_aturan": "Suspected Case-Finding Pattern",
        "kesimpulan": "SUSPECTED_CASE_FINDING_PATTERN",
        "prioritas": 2,
        "keterangan": (
            "Demam, ruam makulopapular, dan ruam menyeluruh."
        ),
        "kondisi": [
            ("DEMAM", "=", "1"),
            ("RUAM", "=", "1"),
            ("RUAM_MENYELURUH", "=", "1"),
        ],
    },
    {
        "id_aturan": "R05A",
        "nama_aturan": "Safety Alert - Kesulitan Bernapas",
        "kesimpulan": "SAFETY_ALERT",
        "prioritas": 1,
        "keterangan": "Pasien mengalami kesulitan bernapas.",
        "kondisi": [
            ("SESAK", "=", "1"),
        ],
    },
    {
        "id_aturan": "R05B",
        "nama_aturan": "Safety Alert - Kejang",
        "kesimpulan": "SAFETY_ALERT",
        "prioritas": 1,
        "keterangan": "Pasien mengalami kejang.",
        "kondisi": [
            ("KEJANG", "=", "1"),
        ],
    },
    {
        "id_aturan": "R05C",
        "nama_aturan": "Safety Alert - Penurunan Kesadaran",
        "kesimpulan": "SAFETY_ALERT",
        "prioritas": 1,
        "keterangan": "Pasien mengalami penurunan kesadaran.",
        "kondisi": [
            ("PENURUNAN_KESADARAN", "=", "1"),
        ],
    },
]


# 3. SEEDER MASTER GEJALA

def seed_master_gejala(db: Session, commit: bool = True) -> None:
    """
    Memasukkan master gejala yang belum tersedia.
    Aman dijalankan berulang kali.
    Jika commit=True, commit langsung dijalankan.
    Jika commit=False, flush dijalankan dan commit diserahkan ke pemanggil.
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
                db.add(MasterGejala(**item))
                jumlah_baru += 1
            else:
                jumlah_sudah_ada += 1

        if commit:
            db.commit()
        else:
            db.flush()

        print("\n=== MASTER GEJALA SEEDER ===")
        print(f"Data baru      : {jumlah_baru}")
        print(f"Sudah tersedia : {jumlah_sudah_ada}")
        print(f"Total master   : {len(MASTER_GEJALA)}")

    except Exception:
        if commit:
            db.rollback()
        raise


# 4. SEEDER ATURAN PAKAR DAN DETAIL ATURAN

def seed_aturan_pakar(db: Session, commit: bool = True) -> None:
    """
    Memasukkan aturan IF-THEN dan detail kondisinya.

    Setiap detail dalam satu aturan menggunakan
    operator AND.

    Aturan R05A, R05B, dan R05C mewakili OR
    antar tanda bahaya.
    Jika commit=True, commit langsung dijalankan.
    Jika commit=False, flush dijalankan dan commit diserahkan ke pemanggil.
    """

    jumlah_aturan_baru = 0
    jumlah_detail_baru = 0

    try:
        # Pastikan semua master gejala sudah tersedia.
        for item in MASTER_GEJALA:
            if db.get(MasterGejala, item["kode_gejala"]) is None:
                raise ValueError(
                    f"Master gejala {item['kode_gejala']} belum tersedia."
                )

        # Masukkan aturan utama.
        for item in ATURAN_PAKAR:

            existing = db.get(
                AturanPakar,
                item["id_aturan"],
            )

            if existing is None:
                db.add(
                    AturanPakar(
                        id_aturan=item["id_aturan"],
                        nama_aturan=item["nama_aturan"],
                        kesimpulan=item["kesimpulan"],
                        prioritas=item["prioritas"],
                        keterangan=item["keterangan"],
                        aktif=True,
                    )
                )
                jumlah_aturan_baru += 1

        # Flush agar data aturan tersedia sebelum detail dibuat.
        db.flush()

        # Masukkan detail kondisi aturan.
        for item in ATURAN_PAKAR:

            for kode_gejala, operator, nilai in item["kondisi"]:

                existing_detail = (
                    db.query(AturanPakarDetail)
                    .filter(
                        AturanPakarDetail.id_aturan
                        == item["id_aturan"],
                        AturanPakarDetail.kode_gejala
                        == kode_gejala,
                        AturanPakarDetail.operator_kondisi
                        == operator,
                        AturanPakarDetail.nilai_kondisi
                        == nilai,
                    )
                    .first()
                )

                if existing_detail is None:
                    db.add(
                        AturanPakarDetail(
                            id_aturan=item["id_aturan"],
                            kode_gejala=kode_gejala,
                            operator_kondisi=operator,
                            nilai_kondisi=nilai,
                        )
                    )
                    jumlah_detail_baru += 1

        if commit:
            db.commit()
        else:
            db.flush()

        print("\nATURAN PAKAR SEEDER")
        print(f"Aturan baru   : {jumlah_aturan_baru}")
        print(f"Detail baru   : {jumlah_detail_baru}")
        print(f"Total aturan  : {len(ATURAN_PAKAR)}")
        print("Seeder aturan berhasil.")

    except Exception:
        if commit:
            db.rollback()
        raise


def main() -> None:
    from app.db.session import SessionLocal
    db = SessionLocal()
    try:
        seed_master_gejala(db)
        seed_aturan_pakar(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
