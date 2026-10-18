from fastapi import APIRouter, HTTPException, Query, status

from app.core.security import AdminUser, CurrentUser, DbSession, is_admin, role_name
from app.models.gejala import User
from app.schemas.main import UserOut

router = APIRouter(prefix="/users", tags=["Users"])


def _to_out(db, user: User) -> UserOut:
    data = UserOut.model_validate(user)
    data.role_name = role_name(db, user.id_Role)
    return data


@router.get("", response_model=list[UserOut])
def list_users(db: DbSession, admin: AdminUser, limit: int = Query(50, ge=1, le=200)):
    """Daftar semua user (khusus Admin)."""
    return [_to_out(db, u) for u in db.query(User).limit(limit).all()]


@router.get("/me", response_model=UserOut)
def my_profile(db: DbSession, user: CurrentUser):
    """Profil user yang sedang login."""
    return _to_out(db, user)


@router.get("/{nik}", response_model=UserOut)
def get_user(nik: str, db: DbSession, user: CurrentUser):
    """Detail user. User biasa hanya boleh melihat dirinya sendiri; Admin bebas."""
    if not is_admin(user) and user.NIK != nik:
        raise HTTPException(status_code=403, detail="Anda hanya boleh melihat data sendiri")
    target = db.get(User, nik)
    if target is None:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    return _to_out(db, target)
