# Track 002 — `integrasi_sensor/README.md`

- **Waktu:** 2026-11-18T18:18:24+00:00
- **Berkas:** `integrasi_sensor/README.md`
- **Ringkasan:** hardware-doc-dan-auto-registrasi-rfid
- **Status sebelum:** ada
- **Status sesudah:** ada
- **Ukuran:** 6575 -> 6873 byte
- **SHA256 sesudah:** 97789214a393defeed26daaffe0f7f188f52902916af433535a864986f6ae00c

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
