
import json

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import delete, select

from app.core.security import DbSession, get_current_user, is_admin

from app.models.gejala import Gejala, User
from app.routers.kiosk_session import _session_from_token
from app.models.pakar import (
    MasterGejala,
    JawabanGejala,
    HasilPakar,
)

from app.schemas.pakar import EvaluasiPakarRequest

from app.expert_system.inference_engine import run_forward_chaining
from app.expert_system.decision_tree import run_decision_tree


router = APIRouter(tags=["Sistem Pakar"])


def _resolve_pakar_user(
    db,
    authorization: str | None,
    kiosk_session_token: str | None,
) -> User:
    """Terima JWT user/admin atau token sesi kiosk yang valid."""
    if kiosk_session_token:
        _session, nik = _session_from_token(db, kiosk_session_token)
        user = db.get(User, nik)
        if user is None:
            raise HTTPException(status_code=401, detail="Pasien sesi tidak ditemukan")
        return user

    if authorization and authorization.lower().startswith("bearer "):
        return get_current_user(authorization.split(" ", 1)[1].strip(), db)

    raise HTTPException(status_code=401, detail="Autentikasi diperlukan")


def get_pakar_user(
    db: DbSession,
    authorization: str | None = Header(default=None, alias="Authorization"),
    kiosk_session_token: str | None = Header(default=None, alias="X-Kiosk-Session"),
) -> User:
    return _resolve_pakar_user(db, authorization, kiosk_session_token)



# KONFIGURASI FAKTA WAJIB

REQUIRED_FACTS = {
    "DEMAM",
    "RUAM",
    "RUAM_MENYELURUH",
    "BATUK",
    "PILEK",
    "MATA_MERAH",
    "SESAK",
    "KEJANG",
    "PENURUNAN_KESADARAN",
}


# 1. GET MASTER GEJALA

@router.get("/pakar/master-gejala")
def get_master_gejala(
    db: DbSession,
    user: User = Depends(get_pakar_user),
):
    """
    Mengambil daftar gejala aktif untuk ditampilkan
    pada kuesioner frontend.
    """

    records = (
        db.query(MasterGejala)
        .filter(MasterGejala.aktif.is_(True))
        .order_by(MasterGejala.kode_gejala)
        .all()
    )

    return {
        "total": len(records),
        "data": [
            {
                "kode_gejala": item.kode_gejala,
                "nama_gejala": item.nama_gejala,
                "deskripsi": item.deskripsi,
                "jenis": item.jenis,
            }
            for item in records
        ],
    }


# 2. POST EVALUASI SISTEM PAKAR

@router.post("/pakar/evaluasi")
def evaluasi_pakar(
    payload: EvaluasiPakarRequest,
    db: DbSession,
    user: User = Depends(get_pakar_user),
):
    """
    Menjalankan Forward Chaining dan Decision Tree
    untuk satu pemeriksaan pasien.

    Hasil disimpan ke:
    - jawaban_gejala
    - hasil_pakar
    """

    try:
        # A. VALIDASI PEMERIKSAAN

        pemeriksaan = db.get(
            Gejala,
            payload.id_gejala,
        )

        if pemeriksaan is None:
            raise HTTPException(
                status_code=404,
                detail="Data pemeriksaan tidak ditemukan.",
            )

        # User hanya boleh mengevaluasi pemeriksaannya.
        if (
            not is_admin(user)
            and pemeriksaan.NIK != user.NIK
        ):
            raise HTTPException(
                status_code=403,
                detail="Tidak memiliki akses ke pemeriksaan ini.",
            )

        # B. VALIDASI JAWABAN

        facts = {}

        for jawaban in payload.jawaban:

            kode = jawaban.kode_gejala

            if kode in facts:
                raise HTTPException(
                    status_code=422,
                    detail=f"Jawaban duplikat untuk {kode}.",
                )

            facts[kode] = jawaban.nilai

        missing = REQUIRED_FACTS - set(facts.keys())

        if missing:
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "Jawaban gejala belum lengkap.",
                    "gejala_belum_dijawab": sorted(missing),
                },
            )

        # Pastikan semua kode gejala tersedia dan aktif.
        master_records = (
            db.query(MasterGejala)
            .filter(
                MasterGejala.aktif.is_(True),
                MasterGejala.kode_gejala.in_(facts.keys()),
            )
            .all()
        )

        valid_codes = {
            item.kode_gejala
            for item in master_records
        }

        invalid_codes = set(facts.keys()) - valid_codes

        if invalid_codes:
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "Kode gejala tidak valid atau tidak aktif.",
                    "kode_tidak_valid": sorted(invalid_codes),
                },
            )

        # Parameter numerik seperti SUHU tidak boleh
        # dimasukkan sebagai jawaban Ya/Tidak.
        parameter_codes = {
            item.kode_gejala
            for item in master_records
            if item.jenis == "PARAMETER"
        }

        if parameter_codes:
            raise HTTPException(
                status_code=422,
                detail="Parameter numerik tidak menerima jawaban Ya/Tidak.",
            )

        # C. SIMPAN JAWABAN KE DATABASE

        db.execute(
            delete(JawabanGejala).where(
                JawabanGejala.id_gejala == payload.id_gejala
            )
        )

        for kode, nilai in facts.items():

            db.add(
                JawabanGejala(
                    id_gejala=payload.id_gejala,
                    kode_gejala=kode,
                    nilai=nilai,
                )
            )

        db.flush()

        # D. FORWARD CHAINING

        hasil_forward = run_forward_chaining(
            db,
            facts,
        )

        # E. DECISION TREE

        hasil_tree = run_decision_tree(
            facts,
        )

        # F. RINGKASAN HASIL

        ringkasan = {
            "metode": [
                "Forward Chaining",
                "Decision Tree",
            ],

            "forward_chaining": hasil_forward,

            "decision_tree": hasil_tree,

            "catatan": (
                "Hasil merupakan skrining awal berdasarkan "
                "aturan dan pola gejala yang dimodelkan, "
                "bukan diagnosis medis."
            ),
        }

        # Simpan kode leaf dari kedua cabang.
        hasil_text = (
            f"{hasil_tree['main_leaf']} | "
            f"{hasil_tree['safety_leaf']}"
        )

        # Skor tidak dihitung karena sistem ini
        # belum memiliki model scoring tervalidasi.
        skor = None

        # G. SIMPAN HASIL PAKAR

        hasil_db = (
            db.query(HasilPakar)
            .filter(
                HasilPakar.id_gejala == payload.id_gejala
            )
            .first()
        )

        if hasil_db is None:

            hasil_db = HasilPakar(
                id_gejala=payload.id_gejala,
                hasil=hasil_text,
                skor=skor,
                ringkasan=json.dumps(
                    ringkasan,
                    ensure_ascii=False,
                ),
            )

            db.add(hasil_db)

        else:

            hasil_db.hasil = hasil_text
            hasil_db.skor = skor
            hasil_db.ringkasan = json.dumps(
                ringkasan,
                ensure_ascii=False,
            )

        db.commit()
        db.refresh(hasil_db)

        # H. RESPONSE

        return {
            "success": True,
            "message": "Evaluasi sistem pakar berhasil.",

            "data": {
                "id_hasil": hasil_db.id_hasil,
                "id_gejala": hasil_db.id_gejala,

                "hasil": hasil_db.hasil,

                "forward_chaining": {
                    "kategori": hasil_forward[
                        "screening_category"
                    ],

                    "aturan_aktif": [
                        rule["id_aturan"]
                        for rule in hasil_forward["matched_rules"]
                    ],

                    "clinical_pattern": hasil_forward[
                        "clinical_measles_pattern"
                    ],

                    "suspected_pattern": hasil_forward[
                        "suspected_case_finding_pattern"
                    ],
                },

                "decision_tree": {
                    "main_leaf": hasil_tree["main_leaf"],
                    "safety_leaf": hasil_tree["safety_leaf"],
                    "decision_path": hasil_tree["decision_path"],
                },

                "safety_alert": hasil_tree["safety_alert"],

                "skor": None,

                "catatan": ringkasan["catatan"],
            },
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise

# 3. GET HASIL PAKAR

@router.get("/pakar/hasil/{id_gejala}")
def get_hasil_pakar(
    id_gejala: str,
    db: DbSession,
    user: User = Depends(get_pakar_user),
):
    """
    Mengambil hasil evaluasi sistem pakar
    berdasarkan ID pemeriksaan.
    """

    pemeriksaan = db.get(
        Gejala,
        id_gejala,
    )

    if pemeriksaan is None:
        raise HTTPException(
            status_code=404,
            detail="Data pemeriksaan tidak ditemukan.",
        )

    if (
        not is_admin(user)
        and pemeriksaan.NIK != user.NIK
    ):
        raise HTTPException(
            status_code=403,
            detail="Tidak memiliki akses ke pemeriksaan ini.",
        )

    hasil = (
        db.query(HasilPakar)
        .filter(
            HasilPakar.id_gejala == id_gejala
        )
        .first()
    )

    if hasil is None:
        raise HTTPException(
            status_code=404,
            detail="Hasil sistem pakar belum tersedia.",
        )

    try:
        ringkasan = json.loads(hasil.ringkasan or "{}")
    except json.JSONDecodeError:
        ringkasan = {}

    return {
        "success": True,
        "data": {
            "id_hasil": hasil.id_hasil,
            "id_gejala": hasil.id_gejala,
            "hasil": hasil.hasil,
            "skor": hasil.skor,
            "ringkasan": ringkasan,
            "tanggal_evaluasi": hasil.tanggal_evaluasi,
        },
    }
