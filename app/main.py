
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.session import Base, SessionLocal, engine

# Import model agar SQLAlchemy mengenali semua tabel
from app.models import gejala as models
from app.models import pakar as pakar_models

# Import seeder sistem pakar
from app.seeders.pakar_seeder import seed_master_gejala

from app.routers import auth, face, gejala, users


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description=(
        "Backend FastAPI untuk pencatatan gejala kesehatan dengan deteksi kamera. "
        "Role Admin dapat melihat history seluruh user; "
        "user biasa hanya riwayatnya sendiri."
    ),
)


# ==============================
# CORS CONFIGURATION
# ==============================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================
# ROUTERS
# ==============================

app.include_router(auth.router, prefix=settings.API_PREFIX)
app.include_router(users.router, prefix=settings.API_PREFIX)
app.include_router(gejala.router, prefix=settings.API_PREFIX)
app.include_router(face.router, prefix=settings.API_PREFIX)


# ==============================
# DATABASE INITIALIZATION
# ==============================

@app.on_event("startup")
def on_startup() -> None:
    """
    Membuat tabel database jika belum tersedia,
    melakukan seeding role, admin, dan master gejala.
    """

    from app.core.security import hash_password
    from app.models.gejala import Role, User

    # 1. Membuat tabel yang belum tersedia
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        # 2. Seeder Role
        for rid, name in (
            ("R1", "Admin"),
            ("R2", "User"),
        ):
            if db.get(Role, rid) is None:
                db.add(
                    Role(
                        id_Role=rid,
                        Name=name,
                    )
                )

        db.commit()

        # 3. Seeder Akun Admin Awal
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

            print(
                ">> Akun admin default dibuat: "
                "NIK=admin / password=admin123"
            )

        # 4. Seeder Master Gejala Sistem Pakar
        seed_master_gejala(db)

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


# ==============================
# ROOT / HEALTH CHECK
# ==============================

@app.get("/", tags=["Meta"])
def root():
    """Health check sederhana."""

    return {
        "status": "ok",
        "app": settings.APP_NAME,
    }


# ==============================
# RUN APPLICATION
# ==============================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
    )
