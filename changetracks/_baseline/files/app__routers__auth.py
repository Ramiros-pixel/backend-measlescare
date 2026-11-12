from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.core.security import (
    CurrentUser,
    DbSession,
    create_access_token,
    hash_password,
    role_name,
    verify_password,
)
from app.models.gejala import User
from app.schemas.main import LoginRequest, Token, UserCreate, UserOut

router = APIRouter(prefix="/auth", tags=["Auth"])


def _to_user_out(db, user: User) -> UserOut:
    data = UserOut.model_validate(user)
    data.role_name = role_name(db, user.id_Role)
    return data


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: DbSession):
    """Daftar akun baru. id_Role harus sudah ada di tabel Role (mis. R1=Admin, R2=User)."""
    if db.get(User, payload.NIK):
        raise HTTPException(status_code=409, detail="NIK sudah terdaftar")

    user = User(
        NIK=payload.NIK,
        Name=payload.Name,
        Tgl_lahir=payload.Tgl_lahir,
        Alamat=payload.Alamat,
        password=hash_password(payload.password),
        id_Role=payload.id_Role,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="id_Role tidak valid")
    db.refresh(user)
    return _to_user_out(db, user)


@router.post("/login", response_model=Token)
def login(payload: LoginRequest, db: DbSession):
    """Login dengan NIK + password. Mengembalikan JWT (pakai header Bearer)."""
    user = db.get(User, payload.NIK)
    if user is None or not verify_password(payload.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="NIK atau password salah",
        )
    return Token(access_token=create_access_token(nik=user.NIK, id_role=user.id_Role))


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser, db: DbSession):
    """Profil user yang sedang login."""
    return _to_user_out(db, user)
