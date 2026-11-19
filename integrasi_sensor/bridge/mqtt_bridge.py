"""Bridge MQTT -> MySQL: subscriber topik `measlescare/+/reading`.

Menerima JSON dari publisher sensor lalu menyimpan ke tabel `Gejala` (kolom
`Suhu`) atas NIK pemilik kartu (`patient_cards.rfid_uid`). Proses ini berjalan
TERPISAH dari backend FastAPI; skema database dibaca dari `app.models` (sumber
kebenaran yang sama dengan backend) dan `DATABASE_URL` dari `.env` root.

Jalankan dari root repo:
    python3 -m integrasi_sensor.bridge.mqtt_bridge [--verbose]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

log = logging.getLogger("mqtt-bridge")

SUHU_MIN_DEFAULT = 25.0
SUHU_MAX_DEFAULT = 45.0


def _cfg(name: str, default: str) -> str:
    return os.getenv(name, default)


def validate_reading(data: object) -> tuple[str, float] | None:
    """Validasi payload sensor -> (rfid_uid, suhu) atau None bila tidak valid.

    Murni (tanpa I/O) agar mudah diuji. Aturan:
    - `rfid_uid`: string, 2-64 karakter, dinormalisasi huruf besar.
    - `suhu`: angka dalam rentang SUHU_MIN..SUHU_MAX (default 25-45 C).
    """
    if not isinstance(data, dict):
        return None
    rfid = data.get("rfid_uid")
    if not isinstance(rfid, str) or not (2 <= len(rfid.strip()) <= 64):
        return None
    suhu_raw = data.get("suhu")
    if suhu_raw is None:
        return None
    try:
        suhu = float(suhu_raw)
    except (TypeError, ValueError):
        return None
    suhu_min = float(_cfg("SUHU_MIN", str(SUHU_MIN_DEFAULT)))
    suhu_max = float(_cfg("SUHU_MAX", str(SUHU_MAX_DEFAULT)))
    if not (suhu_min <= suhu <= suhu_max):
        return None
    return rfid.strip().upper(), round(suhu, 2)


class RecentSeen:
    """Cegah duplikat dari pengiriman ulang MQTT QoS 1 (window waktu).

    Kunci = rfid_uid + suhu + `ts` payload; pengiriman ulang QoS 1 membawa
    payload identik sehingga kunci sama dan dilewati.
    """

    def __init__(self, window_sec: float = 60.0, max_items: int = 500) -> None:
        self.window_sec = window_sec
        self._items: dict[str, float] = {}

    def seen(self, key: str, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        cutoff = now - self.window_sec
        stale = [k for k, t in self._items.items() if t < cutoff]
        for k in stale:
            del self._items[k]
        if key in self._items:
            return True
        if len(self._items) >= 500:
            self._items.pop(next(iter(self._items)))
        self._items[key] = now
        return False


def nik_from_rfid(rfid_uid: str) -> str:
    """NIK 16 digit numerik deterministik dari hex UID kartu.

    Hash SHA-256 dari UID, 8 byte pertama diubah ke bilangan lalu di-mod 10^16.
    Kartu yang sama selalu menghasilkan NIK yang sama (tidak dobel daftar).
    """
    digest = hashlib.sha256(rfid_uid.upper().encode("ascii")).digest()
    value = int.from_bytes(digest[:8], "big") % 10**16
    return f"{value:016d}"


def store_reading(db, rfid_uid: str, suhu: float, payload: dict) -> tuple[str, str | None, bool]:
    """Simpan baris Gejala atas NIK pemilik kartu; kartu baru didaftarkan otomatis.

    Kartu yang belum ada di `patient_cards` dibuatkan pasien baru (Users role R2,
    data diturunkan dari hex UID; password default RFID_DEFAULT_PASSWORD) lalu
    disimpan. Matikan perilaku ini dengan env `RFID_AUTO_REGISTER=false`.

    Kembalikan (status, NIK, auto_registered):
    - ("saved", nik, False)         -> kartu sudah terdaftar, gejala tersimpan
    - ("saved", nik, True)          -> kartu baru didaftarkan lalu gejala tersimpan
    - ("card_unknown", None, False) -> kartu tak dikenal & auto-register mati

    Import `app.models` dilakukan di sini agar modul tetap bisa diimpor tanpa
    dependensi backend terpasang (mis. untuk unit test validasi).
    """
    from app.core.security import hash_password
    from app.models.gejala import Gejala, PatientCard, User

    card = db.query(PatientCard).filter(PatientCard.rfid_uid == rfid_uid).first()
    if card is None and _cfg("RFID_AUTO_REGISTER", "true").lower() not in (
        "1", "true", "yes", "on"
    ):
        return ("card_unknown", None, False)

    auto_registered = card is None
    if card is None:
        nik = nik_from_rfid(rfid_uid)
        db.add(
            User(
                NIK=nik,
                Name=f"Pasien {rfid_uid}",
                Tempat_Tgl_Lahir="-",
                Golongan_darah=None,
                Email=None,
                Alamat="-",
                password=hash_password(_cfg("RFID_DEFAULT_PASSWORD", "rfid123")),
                id_Role="R2",
            )
        )
        card = PatientCard(rfid_uid=rfid_uid, NIK=nik)
        db.add(card)

    gejala = Gejala(
        id_gejala=uuid.uuid4().hex[:20],
        NIK=card.NIK,
        Suhu=suhu,
        Batuk=None,
    )
    db.add(gejala)
    db.commit()
    return ("saved", card.NIK, auto_registered)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verbose", action="store_true", help="log debug")
    args = parser.parse_args(argv)

    # Prioritas konfigurasi:
    # 1. Environment variable sistem (tidak dioverride, override=False)
    # 2. integrasi_sensor/config.env (konfigurasi lokal integrasi sensor)
    # 3. .env root backend (hanya mengisi variabel yang belum tersedia)
    from dotenv import load_dotenv

    load_dotenv(ROOT / "integrasi_sensor" / "config.env", override=False)
    load_dotenv(ROOT / ".env", override=False)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    mqtt_host = _cfg("MQTT_HOST", "127.0.0.1")
    mqtt_port = int(_cfg("MQTT_PORT", "1883"))
    mqtt_user = _cfg("MQTT_USER", "") or None
    mqtt_password = _cfg("MQTT_PASSWORD", "") or None
    subscribe_topic = _cfg("MQTT_SUBSCRIBE_TOPIC", "measlescare/+/reading")

    import paho.mqtt.client as mqtt

    from app.db.session import SessionLocal

    recent = RecentSeen()

    def on_connect(client, userdata, flags, reason_code, properties=None) -> None:
        if reason_code != 0:
            log.error("koneksi ditolak broker: %s", reason_code)
            return
        client.subscribe(subscribe_topic, qos=1)
        log.info("subscribed: %s", subscribe_topic)

    def on_message(client, userdata, msg) -> None:
        try:
            data = json.loads(msg.payload.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            log.warning("payload bukan JSON valid dari %s: %.200s", msg.topic, msg.payload)
            return

        parsed = validate_reading(data)
        if parsed is None:
            log.warning("payload tidak valid dari %s: %.200s", msg.topic, msg.payload)
            return
        rfid_uid, suhu = parsed

        key = f"{rfid_uid}:{suhu}:{data.get('ts', '')}"
        if recent.seen(key):
            log.debug("duplikat dilewati (rfid=%s suhu=%.2f)", rfid_uid, suhu)
            return

        db = SessionLocal()
        try:
            status, nik, auto_registered = store_reading(db, rfid_uid, suhu, data)
        except Exception:
            db.rollback()
            log.exception("gagal menyimpan pembacaan rfid=%s", rfid_uid)
            return
        finally:
            db.close()

        if status == "card_unknown":
            log.warning(
                "kartu %s belum terdaftar dan auto-register mati - dilewati", rfid_uid
            )
        else:
            log.info(
                "tersimpan: rfid=%s NIK=%s suhu=%.2f C%s",
                rfid_uid,
                nik,
                suhu,
                " (kartu baru didaftarkan otomatis)" if auto_registered else "",
            )

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"bridge-{uuid.uuid4().hex[:8]}",
    )
    if mqtt_user:
        client.username_pw_set(mqtt_user, mqtt_password)
    client.on_connect = on_connect
    client.on_message = on_message
    client.reconnect_delay_set(min_delay=1, max_delay=30)
    client.connect(mqtt_host, mqtt_port, keepalive=60)
    log.info("bridge terhubung ke %s:%d, subscribe %s", mqtt_host, mqtt_port, subscribe_topic)
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        pass
    finally:
        client.disconnect()
        log.info("bridge berhenti")
    return 0


if __name__ == "__main__":
    sys.exit(main())