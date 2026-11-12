import uuid

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.core.security import AdminUser, CurrentUser, DbSession, is_admin
from app.models.gejala import Camera, Gejala
from app.schemas.main import CameraCreate, CameraOut, GejalaCreate, GejalaOut

router = APIRouter(tags=["Gejala & Camera"])


# ---------------- Gejala ----------------
@router.post("/gejala", response_model=GejalaOut, status_code=201)
def catat_gejala(payload: GejalaCreate, db: DbSession, user: CurrentUser):
    """Catat gejala baru (batuk & suhu) atas NIK user yang sedang login."""
    gejala = Gejala(
        id_gejala=uuid.uuid4().hex[:20],
        NIK=user.NIK,
        Batuk=payload.Batuk,
        Suhu=payload.Suhu,
    )
    db.add(gejala)
    db.commit()
    db.refresh(gejala)
    return gejala


@router.get("/gejala/history", response_model=list[dict])
def history_gejala(
    db: DbSession,
    user: CurrentUser,
    limit: int = Query(50, ge=1, le=200),
    nik: str | None = Query(None, description="Hanya Admin: lihat history user lain"),
):
    """
    Riwayat gejala + hasil kamera.

    - User biasa: otomatis hanya riwayat miliknya sendiri.
    - Admin: semua user; boleh filter ?nik= untuk satu user.
    """
    stmt = select(Gejala).order_by(Gejala.Tanggal.desc()).limit(limit)
    if is_admin(user):
        if nik:
            stmt = stmt.where(Gejala.NIK == nik)
    else:
        if nik and nik != user.NIK:
            raise HTTPException(
                status_code=403, detail="Anda hanya boleh melihat riwayat sendiri"
            )
        stmt = stmt.where(Gejala.NIK == user.NIK)

    rows = db.execute(stmt).scalars().all()
    return [_serialize_history(db, g) for g in rows]


@router.get("/gejala/{id_gejala}", response_model=dict)
def detail_gejala(id_gejala: str, db: DbSession, user: CurrentUser):
    """Detail satu catatan gejala (milik sendiri, atau semua jika Admin)."""
    gejala = db.get(Gejala, id_gejala)
    if gejala is None:
        raise HTTPException(status_code=404, detail="Data gejala tidak ditemukan")
    if not is_admin(user) and gejala.NIK != user.NIK:
        raise HTTPException(
            status_code=403, detail="Anda hanya boleh mengakses riwayat sendiri"
        )
    return _serialize_history(db, gejala)


# ---------------- Camera ----------------
@router.post("/camera", response_model=CameraOut, status_code=201)
def catat_camera(payload: CameraCreate, db: DbSession, user: CurrentUser):
    """Rekam hasil deteksi kamera untuk satu catatan gejala."""
    gejala = db.get(Gejala, payload.id_gejala)
    if gejala is None:
        raise HTTPException(status_code=404, detail="id_gejala tidak ditemukan")
    if not is_admin(user) and gejala.NIK != user.NIK:
        raise HTTPException(
            status_code=403, detail="Anda hanya boleh menambah data pada gejala sendiri"
        )

    cam = Camera(id_cam=uuid.uuid4().hex[:20], **payload.model_dump())
    db.add(cam)
    db.commit()
    db.refresh(cam)
    return cam


@router.get("/camera", response_model=list[CameraOut])
def list_camera(db: DbSession, user: CurrentUser, limit: int = Query(50, ge=1, le=200)):
    """Daftar rekaman kamera (Admin: semua; user biasa: miliknya via gejala)."""
    stmt = select(Camera).order_by(Camera.Tanggal.desc()).limit(limit)
    if not is_admin(user):
        stmt = stmt.join(Gejala, Camera.id_gejala == Gejala.id_gejala).where(
            Gejala.NIK == user.NIK
        )
    return db.execute(stmt).scalars().all()


def _serialize_history(db, g: Gejala) -> dict:
    """Gabungkan gejala + kamera + laporan jadi satu item history."""
    owner = db.get(Gejala, g.id_gejala).user
    return {
        "id_gejala": g.id_gejala,
        "NIK": g.NIK,
        "nama_user": owner.Name if owner else None,
        "Batuk": g.Batuk,
        "Suhu": g.Suhu,
        "Tanggal": g.Tanggal,
        "cameras": [
            {
                "id_cam": c.id_cam,
                "Status": c.Status,
                "Tanggal": c.Tanggal,
                "reports": [{"id_rept": r.id_rept} for r in c.reports],
            }
            for c in g.cameras
        ],
    }
