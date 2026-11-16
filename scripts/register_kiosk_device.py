"""Daftarkan/perbarui perangkat kiosk berdasarkan KIOSK_API_KEY di .env."""
import os
import uuid
from app.core.config import settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.gejala import KioskDevice

def main():
    secret = settings.KIOSK_API_KEY
    if not secret:
        raise SystemExit("KIOSK_API_KEY belum diatur di .env backend.")
    name = os.getenv("KIOSK_DEVICE_NAME", "MeaslesCare Kiosk 01")
    db = SessionLocal()
    try:
        device = db.query(KioskDevice).filter(KioskDevice.nama_device == name).first()
        if device:
            device.secret_hash = hash_password(secret)
            device.aktif = True
            message = "Perangkat diperbarui"
        else:
            device = KioskDevice(
                id_device=str(uuid.uuid4()),
                nama_device=name,
                secret_hash=hash_password(secret),
                aktif=True,
            )
            db.add(device)
            message = "Perangkat didaftarkan"
        db.commit()
        print(f"{message}: {device.nama_device} ({device.id_device})")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
