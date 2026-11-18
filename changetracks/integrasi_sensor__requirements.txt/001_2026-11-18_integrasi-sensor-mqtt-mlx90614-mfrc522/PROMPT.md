# Track 001 — `integrasi_sensor/requirements.txt`

- **Waktu:** 2026-11-18T17:52:47+00:00
- **Berkas:** `integrasi_sensor/requirements.txt`
- **Ringkasan:** integrasi-sensor-mqtt-mlx90614-mfrc522
- **Status sebelum:** BELUM ADA
- **Status sesudah:** ada
- **Ukuran:** 0 -> 371 byte
- **SHA256 sesudah:** 81af9726f23177069f626519ad6e53b5f8e28b1988ac7116da252986e5ad6f13

## Prompt asli

> buatkan saya folder integrasi sensor - SENSOR SUHU IR NON CONTACT MLX90614 GY-906 HW-691 CONTACTLESS TEMPERATURE SENSOR MODULE - MODULE RFID MFRC522 MINI 13.56MHZ SPI CARD + KEYCHAIN dengan menggunakan mqtt mosquitto untuk nantinya distore ke db yang ada di backend-measlescare dari kolom db yang sudah disediakan seperti kolom rfid dan suhu

## Alasan / konteks

Folder integrasi_sensor/: publisher firmware Python (MLX90614 I2C + MFRC522 SPI) -> MQTT Mosquitto -> bridge subscriber yang menulis Gejala.Suhu berdasarkan rfid_uid di patient_cards. Jawaban konfirmasi pemilik: target Orange Pi/Raspberry Pi Python, bridge service terpisah, simpan baris Gejala baru (Batuk NULL), mosquitto ditambah ke docker-compose.yml.

## Berkas lain yang ikut berubah pada prompt ini

- (tidak ada)

## Cara memverifikasi

```bash
diff -u before.txt after.txt    # atau: cat diff.patch
```
