"""Launcher: jalankan server dengan `python main.py` dari folder Backend.

Mode produksi (systemd) TIDAK memakai reload: reload men-spawn proses
reloader + child (dua proses), yang bertentangan dengan unit `Type=simple`
dan menyebabkan proses ganda. Untuk pengembangan lokal:

    UVICORN_RELOAD=1 python main.py
"""
import os

import uvicorn

RELOAD = os.getenv("UVICORN_RELOAD", "0") == "1"

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=RELOAD,
    )
