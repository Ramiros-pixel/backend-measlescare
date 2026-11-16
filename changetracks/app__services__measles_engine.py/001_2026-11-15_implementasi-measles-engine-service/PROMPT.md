# Track 001 — `app/services/measles_engine.py`

- **Waktu:** 2026-11-15T23:55:32+07:00
- **Berkas:** `app/services/measles_engine.py`
- **Ringkasan:** implementasi-measles-engine-service
- **Status sebelum:** BELUM ADA
- **Status sesudah:** ada
- **Ukuran:** 0 -> 17208 byte
- **SHA256 sesudah:** b96ca5dc0cb388f5ccaf36ef6001863253dba32fbbe46bbcabcda688c5e70b86

## Prompt asli

> PHASE 2: PREPROCESSING PIPELINE & INFERENCE ENGINE - Implementasi service inferensi ONNX MeaslesWatch AI (MobileNetV3 Small) dengan pra-pemrosesan citra deterministik dan manajemen siklus hidup singleton thread-safe.

## Alasan / konteks

Menyediakan modul inferensi mandiri CPU-only untuk mendeteksi 6 kelas penyakit ruam kulit menggunakan ONNX Runtime dan OpenCV, mematuhi spesifikasi arsitektur backend eksisting.

## Berkas lain yang ikut berubah pada prompt ini

- `tests/test_measles_engine.py`
- `app/models/weights/mobilenetv3_measleswatch.onnx`

## Cara memverifikasi

```bash
diff -u before.py after.py    # atau: cat diff.patch
```
