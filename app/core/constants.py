"""Konstanta bersama untuk validasi sensor (Phase 5).

Satu sumber kebenaran untuk ambang suhu dan daftar perangkat MQTT yang diizinkan,
agar bridge, schema, dan reconciliation memakai nilai yang sama.
Nilai dapat di-override lewat environment variable.
"""
import os


def _f(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


# Suhu tubuh (objek) yang dianggap pembacaan manusia valid.
SUHU_MIN: float = _f("SUHU_MIN", 30.0)
SUHU_MAX: float = _f("SUHU_MAX", 45.0)

# Rentang suhu ambien (lingkungan) yang wajar untuk telemetri.
AMBIENT_MIN: float = _f("AMBIENT_MIN", -10.0)
AMBIENT_MAX: float = _f("AMBIENT_MAX", 60.0)

# Format UID RFID yang diterima (hex 4-32 karakter).
RFID_UID_PATTERN: str = r"^[0-9A-F]{4,32}$"

# device_id MQTT yang diizinkan (dipisah koma).
ALLOWED_DEVICES: frozenset[str] = frozenset(
    d.strip()
    for d in os.getenv("MQTT_ALLOWED_DEVICES", "ESP32_SENSOR_01").split(",")
    if d.strip()
)
