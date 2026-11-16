# Track 001 — `tests/test_http_client.py`

- **Waktu:** 2026-11-16T00:27:24+07:00
- **Berkas:** `tests/test_http_client.py`
- **Ringkasan:** http-integration-tests-testclient
- **Status sebelum:** BELUM ADA
- **Status sesudah:** ada
- **Ukuran:** 0 -> 9116 byte
- **SHA256 sesudah:** dcd2914d2d9b601df154b0890c917e10324be1ab4b9988311fc0d4ebbf8b8029

## Prompt asli

> PROMPT 25 — PHASE 3.6: POST-INSTALLATION DEPENDENCY & HTTP VERIFICATION - Pembuatan suite pengujian integrasi HTTP nyata via FastAPI TestClient setelah python-multipart==0.0.32 terpasang.

## Alasan / konteks

Menguji request upload multipart/form-data nyata melalui socket TestClient, memvalidasi inferensi model ONNX riil pada citra dataset, serta menguji status code HTTP 200, 400, 413, 415, 422, 503, dan 500.

## Berkas lain yang ikut berubah pada prompt ini

- `app/routers/measles.py`
- `tests/test_measles_router.py`

## Cara memverifikasi

```bash
diff -u before.py after.py    # atau: cat diff.patch
```
