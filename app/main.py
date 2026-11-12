from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.session import Base, SessionLocal, engine
from app.models import gejala as models  # pastikan semua model terdaftar
from app.routers import auth, face, gejala, users

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description=(
        "Backend FastAPI untuk pencatatan gejala kesehatan dengan deteksi kamera. "
        "Role Admin dapat melihat history seluruh user; user biasa hanya riwayatnya sendiri."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ganti ke domain frontend di production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=settings.API_PREFIX)
app.include_router(users.router, prefix=settings.API_PREFIX)
app.include_router(gejala.router, prefix=settings.API_PREFIX)
app.include_router(face.router, prefix=settings.API_PREFIX)


@app.on_event("startup")
def on_startup() -> None:
    """Buat tabel bila belum ada + seed role & akun admin pertama."""
    from app.core.security import hash_password
    from app.models.gejala import Role, User

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        for rid, name in (("R1", "Admin"), ("R2", "User")):
            if db.get(Role, rid) is None:
                db.add(Role(id_Role=rid, Name=name))
        db.commit()

        if db.get(User, "admin") is None:
            db.add(
                User(
                    NIK="admin",
                    Name="Administrator",
                    Tgl_lahir="2000-01-01",
                    Alamat="-",
                    password=hash_password("admin123"),
                    id_Role="R1",
                )
            )
            db.commit()
            print(">> Akun admin default dibuat: NIK=admin / password=admin123")
    finally:
        db.close()


@app.get("/", tags=["Meta"])
def root():
    """Health check sederhana."""
    return {"status": "ok", "app": settings.APP_NAME}
