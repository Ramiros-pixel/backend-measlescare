"""Bridge MQTT -> Backend: adapter tipis.

Subscribe topik `measlescare/+/reading`, parse JSON, normalisasi field
`object_temp` (backward-compat `suhu`), lalu kirim ke backend FastAPI melalui
endpoint internal `POST /api/kiosk-session/reading` (header `X-Kiosk-Key`).

Bridge TIDAK menulis ke database dan TIDAK melakukan auto-registrasi pasien.
Backend adalah validator otoritatif; seluruh keputusan status direkam di tabel
`sensor_readings`.

Jalankan dari root repo:
    python3 -m integrasi_sensor.bridge.mqtt_bridge [--verbose]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import queue
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

log = logging.getLogger("mqtt-bridge")

COUNTERS = {"received": 0, "accepted": 0, "rejected": 0, "duplicate": 0, "error": 0}
_COUNTER_LOCK = threading.Lock()


def _cfg(name: str, default: str) -> str:
    return os.getenv(name, default)


def _bump(key: str) -> None:
    with _COUNTER_LOCK:
        COUNTERS[key] += 1


def normalize_payload(data: object) -> dict | None:
    """Normalisasi payload sensor ke kontrak kanonik internal.

    - `object_temp` = suhu tubuh kanonik; fallback `suhu` (backward compat).
    - `ambient_temp`, `device_id`, `uptime_ms` dipertahankan.
    - `event_id` fallback: sha256(payload) bila tidak ada/tidak string.
    Kembalikan dict kanonik, atau None bila bukan dict.
    """
    if not isinstance(data, dict):
        return None

    event_id = data.get("event_id")
    if not isinstance(event_id, str) or not event_id.strip():
        canonical_str = json.dumps(data, sort_keys=True, default=str)
        event_id = hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()[:64]

    device_id = data.get("device_id")
    device_id = device_id if isinstance(device_id, str) else ""

    rfid_uid = data.get("rfid_uid")
    rfid_uid = (
        rfid_uid.strip().upper()
        if isinstance(rfid_uid, str) and rfid_uid.strip()
        else None
    )

    object_temp = data.get("object_temp")
    if object_temp is None and "suhu" in data:
        object_temp = data.get("suhu")
    try:
        object_temp = float(object_temp) if object_temp is not None else None
    except (TypeError, ValueError):
        object_temp = None

    ambient_temp = data.get("ambient_temp")
    try:
        ambient_temp = float(ambient_temp) if ambient_temp is not None else None
    except (TypeError, ValueError):
        ambient_temp = None

    uptime_ms = data.get("uptime_ms")
    try:
        uptime_ms = int(uptime_ms) if uptime_ms is not None else None
    except (TypeError, ValueError):
        uptime_ms = None

    source_format = (
        "python_publisher" if ("suhu" in data and "object_temp" not in data) else "esp32"
    )

    return {
        "event_id": event_id,
        "device_id": device_id,
        "rfid_uid": rfid_uid,
        "object_temp": object_temp,
        "ambient_temp": ambient_temp,
        "uptime_ms": uptime_ms,
        "source_format": source_format,
    }


def post_reading(
    backend_url: str, kiosk_key: str, canonical: dict, timeout: float = 5.0
) -> tuple[bool, dict]:
    """Kirim satu pembacaan ke backend. Return (ok, response_dict)."""
    body = json.dumps(canonical).encode("utf-8")
    req = urllib.request.Request(
        f"{backend_url.rstrip('/')}/api/kiosk-session/reading",
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Kiosk-Key": kiosk_key,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return True, data
    except urllib.error.HTTPError as e:
        return False, {
            "http_status": e.code,
            "detail": e.read().decode("utf-8", "replace")[:200],
        }
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return False, {"error": str(e)[:200]}


def _is_retryable(resp: dict) -> bool:
    code = resp.get("http_status")
    # 401/403/404/422 = error permanen (config/schema), jangan retry
    return code not in (401, 403, 404, 422)


def worker(backend_url: str, kiosk_key: str, q: queue.Queue, stop: threading.Event) -> None:
    """Worker thread: kirim pembacaan ke backend dengan retry + backoff."""
    while not stop.is_set():
        try:
            canonical = q.get(timeout=1.0)
        except queue.Empty:
            continue

        delay = 1.0
        sent = False
        for _attempt in range(4):
            ok, resp = post_reading(backend_url, kiosk_key, canonical)
            if ok:
                status = resp.get("status", "unknown")
                if status == "duplicate":
                    _bump("duplicate")
                    log.debug("duplikat (event_id=%s)", canonical.get("event_id"))
                elif status == "ACCEPTED":
                    _bump("accepted")
                    log.info(
                        "ACCEPTED rfid=%s suhu=%s nik=%s",
                        canonical.get("rfid_uid"),
                        canonical.get("object_temp"),
                        resp.get("nik"),
                    )
                else:
                    _bump("rejected")
                    log.warning(
                        "%s rfid=%s reason=%s",
                        status,
                        canonical.get("rfid_uid"),
                        resp.get("reason"),
                    )
                sent = True
                break
            if not _is_retryable(resp):
                _bump("error")
                log.error(
                    "backend menolak permanen (%s): %s",
                    resp.get("http_status"),
                    resp.get("detail") or resp.get("error"),
                )
                sent = True
                break
            log.warning("kirim gagal (%s), retry %.0fs", resp, delay)
            time.sleep(delay)
            delay = min(delay * 2, 30.0)

        if not sent:
            _bump("error")
            log.error("gagal kirim setelah retry: %s", canonical.get("event_id"))
        q.task_done()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verbose", action="store_true", help="log debug")
    args = parser.parse_args(argv)

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
    backend_url = _cfg("BACKEND_URL", "http://127.0.0.1:8000")
    kiosk_key = _cfg("KIOSK_API_KEY", "")

    if not kiosk_key:
        log.error(
            "KIOSK_API_KEY belum diatur di config.env; bridge tidak bisa "
            "autentikasi ke backend."
        )
        return 2

    import paho.mqtt.client as mqtt

    q: queue.Queue = queue.Queue()
    stop = threading.Event()
    t = threading.Thread(
        target=worker,
        args=(backend_url, kiosk_key, q, stop),
        name="bridge-http-worker",
        daemon=True,
    )
    t.start()

    def on_connect(client, userdata, flags, reason_code, properties=None) -> None:
        if reason_code != 0:
            log.error("koneksi ditolak broker: %s", reason_code)
            return
        client.subscribe(subscribe_topic, qos=1)
        log.info("subscribed: %s", subscribe_topic)

    def on_disconnect(client, userdata, reason_code, properties=None) -> None:
        log.warning("terputus dari broker (reason=%s); menunggu reconnect", reason_code)

    def on_message(client, userdata, msg) -> None:
        _bump("received")
        try:
            data = json.loads(msg.payload.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            log.warning(
                "payload bukan JSON valid dari %s: %.200s", msg.topic, msg.payload
            )
            _bump("rejected")
            return

        canonical = normalize_payload(data)
        if canonical is None:
            log.warning(
                "payload bukan objek JSON dari %s: %.200s", msg.topic, msg.payload
            )
            _bump("rejected")
            return

        canonical["raw_payload"] = msg.payload.decode("utf-8", "replace")
        q.put(canonical)

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"bridge-{uuid.uuid4().hex[:8]}",
    )
    if mqtt_user:
        client.username_pw_set(mqtt_user, mqtt_password)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    client.reconnect_delay_set(min_delay=1, max_delay=30)

    # connect_async + loop_start: tahan terhadap broker yang belum siap.
    client.connect_async(mqtt_host, mqtt_port, keepalive=60)
    client.loop_start()
    log.info(
        "bridge terhubung ke %s:%d, subscribe %s", mqtt_host, mqtt_port, subscribe_topic
    )

    try:
        while True:
            time.sleep(5)
            log.debug("counter=%s", COUNTERS)
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        client.loop_stop()
        client.disconnect()
        log.info("bridge berhenti. counter=%s", COUNTERS)
    return 0


if __name__ == "__main__":
    sys.exit(main())
