# Track 001 — `.env.example`

- **Waktu:** 2026-11-18T17:54:18+00:00
- **Berkas:** `.env.example`
- **Ringkasan:** integrasi-sensor-mqtt-mlx90614-mfrc522
- **Status sebelum:** ada
- **Status sesudah:** ada
- **Ukuran:** 193 -> 425 byte
- **SHA256 sesudah:** 5df25b27ff123e089d76e8a7080e2797f7d0c6d090f60f88cd59ec606f02f5f1

## Prompt asli

> buatkan saya folder integrasi sensor - SENSOR SUHU IR NON CONTACT MLX90614 GY-906 HW-691 CONTACTLESS TEMPERATURE SENSOR MODULE - MODULE RFID MFRC522 MINI 13.56MHZ SPI CARD + KEYCHAIN dengan menggunakan mqtt mosquitto untuk nantinya distore ke db yang ada di backend-measlescare dari kolom db yang sudah disediakan seperti kolom rfid dan suhu

## Alasan / konteks

Tambah service mosquitto (eclipse-mosquitto:2) ke compose + variabel MQTT_* di .env.example + bagian 'Integrasi Sensor (MQTT)' di Documentation.md, sebagai bagian dari prompt integrasi sensor yang sama.

## Berkas lain yang ikut berubah pada prompt ini

- `integrasi_sensor/` (folder baru)
- `mosquitto/config/mosquitto.conf`

## Cara memverifikasi

```bash
diff -u before.example after.example
```
