# Track 001 — `HARDWARE_DOCUMENTATION.md`

- **Waktu:** 2026-11-18T18:18:24+00:00
- **Berkas:** `HARDWARE_DOCUMENTATION.md`
- **Ringkasan:** hardware-doc-dan-auto-registrasi-rfid
- **Status sebelum:** BELUM ADA
- **Status sesudah:** ada
- **Ukuran:** 0 -> 7989 byte
- **SHA256 sesudah:** 5bf775b567ddeb861bc33f9fc20b80f82815ee404159c128cf5a259c92afdacc

## Prompt asli

> buatkan documentation pada folder HARDWARE_DOCUMENTATION.md isinya gpio setiap sensor dan buatkan saya cara run dan sistem kerja kemudian ganti juga buat inisialisasi rfid dengan component yang diperlukan pada database jadi ketika pembacaan code hex rfid terbaca otomatis mengisi labeling data yang sudah diberikan pada hexa chip kartu rfid tersebut (jadi buat seolah olah kartu itu udah punya data berdasarkan hex yang ada di chip rfid)

## Alasan / konteks

Dokumentasi GPIO tiap sensor + cara run + sistem kerja. Auto-registrasi kartu RFID: kartu tak dikenal otomatis didaftarkan (Users + PatientCard) dengan data diturunkan dari hex UID (NIK 16 digit deterministik hash SHA-256, Name 'Pasien <HEX>', password rfid123, role R2).

## Berkas lain yang ikut berubah pada prompt ini

- `integrasi_sensor/bridge/mqtt_bridge.py`
- `integrasi_sensor/README.md`
- `integrasi_sensor/config.example.env`
- `Documentation.md`

## Cara memverifikasi

```bash
diff -u before.md after.md    # atau: cat diff.patch
```
