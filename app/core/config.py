import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Konfigurasi aplikasi, dibaca dari environment / file .env."""

    APP_NAME: str = "Huawei ICT Backend"
    API_PREFIX: str = os.getenv("API_PREFIX", "/api")

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://root:orangepi@127.0.0.1:3306/db_huawei",
    )

    # Keamanan JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))
    KIOSK_API_KEY: str = os.getenv("KIOSK_API_KEY", "")

    # Rate Limiting Kiosk (Permintaan per menit)
    RATE_LIMIT_RFID_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_RFID_PER_MINUTE", "60"))
    RATE_LIMIT_SESSION_CREATE_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_SESSION_CREATE_PER_MINUTE", "30"))

settings = Settings()
