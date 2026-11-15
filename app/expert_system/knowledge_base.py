
from sqlalchemy.orm import Session

from app.models.pakar import (
    MasterGejala,
    AturanPakar,
    AturanPakarDetail,
)


def get_active_master_gejala(db: Session) -> list[dict]:
    """
    Mengambil seluruh master gejala yang aktif.
    """

    records = (
        db.query(MasterGejala)
        .filter(MasterGejala.aktif.is_(True))
        .order_by(MasterGejala.kode_gejala)
        .all()
    )

    return [
        {
            "kode_gejala": item.kode_gejala,
            "nama_gejala": item.nama_gejala,
            "jenis": item.jenis,
            "deskripsi": item.deskripsi,
        }
        for item in records
    ]


def get_knowledge_base(db: Session) -> list[dict]:
    """
    Mengambil aturan aktif beserta detail kondisinya
    dari database MySQL.

    Semua kondisi dalam satu aturan dievaluasi
    menggunakan logika AND.
    """

    aturan_list = (
        db.query(AturanPakar)
        .filter(AturanPakar.aktif.is_(True))
        .order_by(
            AturanPakar.prioritas.asc(),
            AturanPakar.id_aturan.asc(),
        )
        .all()
    )

    if not aturan_list:
        return []

    aturan_ids = [aturan.id_aturan for aturan in aturan_list]

    detail_list = (
        db.query(AturanPakarDetail)
        .filter(
            AturanPakarDetail.id_aturan.in_(aturan_ids)
        )
        .order_by(AturanPakarDetail.id_detail.asc())
        .all()
    )

    # Kelompokkan detail berdasarkan kode aturan.
    detail_map = {}

    for detail in detail_list:
        detail_map.setdefault(
            detail.id_aturan,
            [],
        ).append(
            {
                "kode_gejala": detail.kode_gejala,
                "operator": detail.operator_kondisi,
                "nilai_kondisi": detail.nilai_kondisi,
            }
        )

    knowledge_base = []

    for aturan in aturan_list:
        knowledge_base.append(
            {
                "id_aturan": aturan.id_aturan,
                "nama_aturan": aturan.nama_aturan,
                "kesimpulan": aturan.kesimpulan,
                "prioritas": aturan.prioritas,
                "keterangan": aturan.keterangan,
                "kondisi": detail_map.get(
                    aturan.id_aturan,
                    [],
                ),
            }
        )

    return knowledge_base
