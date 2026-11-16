# Track 001 — `tests/test_measles_router.py`

- **Waktu:** 2026-11-16T00:14:37+07:00
- **Berkas:** `tests/test_measles_router.py`
- **Ringkasan:** unit-tests-measles-router
- **Status sebelum:** BELUM ADA
- **Status sesudah:** ada
- **Ukuran:** 0 -> 14104 byte
- **SHA256 sesudah:** 3f85cfd8e4698b55084620ac0d9f9fca01c3a133c94ce647b8e757148720d1fe

## Prompt asli

> PROMPT 23 — PHASE 3: FASTAPI INFERENCE API DEVELOPMENT - Implementasi 10 unit dan integration test otomatis untuk memvalidasi router, skema, penolakan file kosong, oversized file, format tidak didukung, citra rusak, kegagalan model, dan isolasi modul.

## Alasan / konteks

Menjamin keandalan fungsional endpoint POST /v1/measles/predict, kepatuhan batas HTTP, dan penanganan exception yang aman.

## Berkas lain yang ikut berubah pada prompt ini

- `app/routers/measles.py`
- `app/schemas/measles.py`

## Cara memverifikasi

```bash
diff -u before.py after.py    # atau: cat diff.patch
```
