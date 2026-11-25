"""Unit test murni (tanpa I/O) untuk normalisasi payload bridge."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from integrasi_sensor.bridge.mqtt_bridge import normalize_payload


def test_esp32_payload_normalized():
    out = normalize_payload({
        "event_id": "4bfed264-11648", "device_id": "ESP32_SENSOR_01",
        "rfid_uid": "b1056b66", "ambient_temp": 27.67, "object_temp": 28.17,
        "uptime_ms": 11649,
    })
    assert out["event_id"] == "4bfed264-11648"
    assert out["device_id"] == "ESP32_SENSOR_01"
    assert out["rfid_uid"] == "B1056B66"  # uppercase
    assert out["object_temp"] == 28.17
    assert out["ambient_temp"] == 27.67
    assert out["uptime_ms"] == 11649
    assert out["source_format"] == "esp32"


def test_legacy_suhu_backward_compat():
    out = normalize_payload({
        "device_id": "kiosk-01", "rfid_uid": "E0040100ABCDEF0001",
        "suhu": 36.7, "sensor": "mlx90614", "ts": "2026-11-18T15:04:05+00:00",
    })
    assert out["object_temp"] == 36.7
    assert out["source_format"] == "python_publisher"
    assert out["event_id"]  # fallback hash generated


def test_missing_temp_becomes_none():
    out = normalize_payload({"device_id": "ESP32_SENSOR_01", "rfid_uid": "B1056B66"})
    assert out["object_temp"] is None


def test_missing_event_id_fallback_hash():
    a = normalize_payload({"device_id": "x", "rfid_uid": "AABB", "object_temp": 36.7})
    b = normalize_payload({"device_id": "x", "rfid_uid": "AABB", "object_temp": 36.7})
    assert a["event_id"] == b["event_id"]  # deterministik
    assert len(a["event_id"]) == 64


def test_bad_temp_type_becomes_none():
    out = normalize_payload({"device_id": "x", "object_temp": "abc"})
    assert out["object_temp"] is None


def test_non_dict_returns_none():
    assert normalize_payload(["not", "a", "dict"]) is None
    assert normalize_payload(None) is None


def test_uid_uppercased_and_trimmed():
    out = normalize_payload({
        "device_id": "x", "rfid_uid": "  b1056b66  ", "object_temp": 36.7
    })
    assert out["rfid_uid"] == "B1056B66"
