# Track 001 — `app/seeders/seed_all.py`

- **Waktu:** 2026-11-18T17:04:11+00:00
- **Berkas:** `app/seeders/seed_all.py`
- **Ringkasan:** tambah-seeder-data-lengkap-dummy
- **Status sebelum:** BELUM ADA
- **Status sesudah:** ada
- **Ukuran:** 0 -> 11530 byte
- **SHA256 sesudah:** c7ffd811e73d2bb5e3de2c0e629ecbc2d3dfe75d9ebe3e75bbf69ae15b005dbf

## Prompt asli

> Buatkan seeder data agar backend-measlescare bisa di-run dengan data yang sama pada device manapun dengan data dummy.

## Alasan / konteks

Menambahkan seeder deterministik & idempoten untuk semua tabel agar data dummy identik di setiap device.

## Berkas lain yang ikut berubah pada prompt ini

- `app/seeders/pakar_seeder.py`

## Cara memverifikasi

```bash
diff -u before.py after.py    # atau: cat diff.patch
```
