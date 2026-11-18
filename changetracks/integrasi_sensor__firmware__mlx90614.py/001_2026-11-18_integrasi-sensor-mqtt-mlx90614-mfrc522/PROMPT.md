# Track 001 — `integrasi_sensor/firmware/mlx90614.py`

- **Waktu:** 2026-11-18T17:52:47+00:00
- **Berkas:** `integrasi_sensor/firmware/mlx90614.py`
- **Ringkasan:** integrasi-sensor-mqtt-mlx90614-mfrc522
- **Status sebelum:** BELUM ADA
- **Status sesudah:** ada
- **Ukuran:** 0 -> 3026 byte
- **SHA256 sesudah:** eaf39877d065b1c06e638fef3f6b2582d0a36f70863f971003e89f1cb0cc6f9d

## Prompt asli

> buatkan saya folder integrasi sensor - SENSOR SUHU IR NON CONTACT MLX90614 GY-906 HW-691 CONTACTLESS TEMPERATURE SENSOR MODULE - MODULE RFID MFRC522 MINI 13.56MHZ SPI CARD + KEYCHAIN dengan menggunakan mqtt mosquitto untuk nantinya distore ke db yang ada di backend-measlescare dari kolom db yang sudah disediakan seperti kolom rfid dan suhu

## Alasan / konteks

Folder integrasi_sensor/: publisher firmware Python (MLX90614 I2C + MFRC522 SPI) -> MQTT Mosquitto -> bridge subscriber yang menulis Gejala.Suhu berdasarkan rfid_uid di patient_cards. Jawaban konfirmasi pemilik: target Orange Pi/Raspberry Pi Python, bridge service terpisah, simpan baris Gejala baru (Batuk NULL), mosquitto ditambah ke docker-compose.yml.

## Berkas lain yang ikut berubah pada prompt ini

- (tidak ada)

## Cara memverifikasi

```bash
diff -u before.py after.py    # atau: cat diff.patch
```
