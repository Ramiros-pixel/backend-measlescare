import bcrypt
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.gejala import Gejala, Role, User

def hash_password(password: str) -> str:
    """Hash password dengan bcrypt (bcrypt v5, tanpa passlib)."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except ValueError:
        return False


# Token dikirim via header Authorization: Bearer <token>
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_PREFIX}/auth/login")


def create_access_token(nik: str, id_role: str) -> str:
    """Buat JWT berisi identitas user + role-nya."""
    from datetime import datetime, timedelta, timezone

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": nik, "id_role": id_role, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def get_db() -> Session:
    """Dependency: satu sesi database per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DbSession = Annotated[Session, Depends(get_db)]
Token = Annotated[str, Depends(oauth2_scheme)]


def get_current_user(token: Token, db: DbSession) -> User:
    """Validasi JWT lalu ambil data user dari database."""
    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token tidak valid atau kedaluwarsa",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        nik: str | None = payload.get("sub")
        if nik is None:
            raise cred_exc
    except JWTError:
        raise cred_exc

    user = db.get(User, nik)
    if user is None:
        raise cred_exc
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def is_admin(user: User) -> bool:
    """Cek apakah user memiliki role Admin (berdasar nama role di tabel Role)."""
    role = user.role.Name if user.role is not None else ""
    return role.strip().lower() == "admin"


def require_admin(user: CurrentUser) -> User:
    """Dependency: endpoint hanya boleh diakses role Admin."""
    if not is_admin(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses khusus Admin",
        )
    return user


AdminUser = Annotated[User, Depends(require_admin)]


def role_name(db: Session, id_role: str) -> str:
    """Ambil nama role dari DB; fallback ke id_role-nya langsung."""
    row = db.get(Role, id_role)
    return row.Name if row else id_role


def get_gejala_or_403(db: Session, gejala_id: str, user: User) -> Gejala:
    """Ambil satu Gejala; user biasa hanya boleh mengakses miliknya sendiri."""
    gejala = db.get(Gejala, gejala_id)
    if gejala is None:
        raise HTTPException(status_code=404, detail="Data gejala tidak ditemukan")
    if not is_admin(user) and gejala.NIK != user.NIK:
        raise HTTPException(
            status_code=403, detail="Anda hanya boleh mengakses riwayat sendiri"
        )
    return gejala
