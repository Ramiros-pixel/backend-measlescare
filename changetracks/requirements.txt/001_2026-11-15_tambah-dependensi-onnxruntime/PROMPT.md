# Track 001 — `requirements.txt`

- **Waktu:** 2026-11-15T23:44:31+07:00
- **Berkas:** `requirements.txt`
- **Ringkasan:** tambah-dependensi-onnxruntime
- **Status sebelum:** ada
- **Status sesudah:** ada
- **Ukuran:** 351 -> 432 byte
- **SHA256 sesudah:** a116564db0360790958a01e3653fdd413cede9bf4b7068b6246f24ad57f40c49

## Prompt asli

> PHASE 1: ENVIRONMENT & MODEL PREPARATION - Menambahkan dependensi onnxruntime>=1.18.0,<2.0 untuk MeaslesWatch AI ONNX inference engine.

## Alasan / konteks

Mempersiapkan dependensi ONNX Runtime CPU untuk inference model MeaslesWatch AI (mobilenetv3_measleswatch.onnx) tanpa mengikutsertakan PyTorch atau dependensi GPU.

## Berkas lain yang ikut berubah pada prompt ini

- `app/models/weights/mobilenetv3_measleswatch.onnx`

## Cara memverifikasi

```bash
diff -u before.txt after.txt    # atau: cat diff.patch
```
