# Track 002 — `Documentation.md`

- **Waktu:** 2026-11-18T18:18:24+00:00
- **Berkas:** `Documentation.md`
- **Ringkasan:** hardware-doc-dan-auto-registrasi-rfid
- **Status sebelum:** ada
- **Status sesudah:** ada
- **Ukuran:** 8141 -> 8379 byte
- **SHA256 sesudah:** d936b207f48fe7cfc09b6d7e49bd66e1fb04cb28fc51840c8a6461fe142e0503

## Prompt asli

> buatkan documentation pada folder HARDWARE_DOCUMENTATION.md isinya gpio setiap sensor dan buatkan saya cara run dan sistem kerja kemudian ganti juga buat inisialisasi rfid dengan component yang diperlukan pada database jadi ketika pembacaan code hex rfid terbaca otomatis mengisi labeling data yang sudah diberikan pada hexa chip kartu rfid tersebut (jadi buat seolah olah kartu itu udah punya data berdasarkan hex yang ada di chip rfid)

## Alasan / konteks

Auto-registrasi kartu RFID di bridge MQTT: kartu tak dikenal otomatis dibuatkan Users (NIK 16 digit deterministik dari hash SHA-256 hex UID, Name 'Pasien <HEX>', role R2, password RFID_DEFAULT_PASSWORD default rfid123) + PatientCard, lalu Gejala tetap disimpan. Env baru: RFID_AUTO_REGISTER, RFID_DEFAULT_PASSWORD. Dokumentasi disinkronkan.

## Berkas lain yang ikut berubah pada prompt ini

- `HARDWARE_DOCUMENTATION.md` (baru)

## Cara memverifikasi

```bash
diff -u before.md after.md
```
