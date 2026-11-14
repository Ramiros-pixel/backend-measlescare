# 06 — Perhitungan & hasil verifikasi

Semua angka di bawah ini **dihitung ulang dari model 3D**, bukan disalin dari
gambar. Jalankan sendiri:

```bash
~/.hermes/cad-venv/bin/python cad/verify.py     # harus "=== SEMUA PASS ==="
```

Hasil terakhir: **45 PASS / 0 FAIL.**

---

## 1. Perhitungan kritis: vignetting kamera & sensor IR

Lubang yang terlalu kecil akan **memotong sudut pandang** lensa (vignetting).
Rumusnya sederhana — sudut yang masih terlihat dari tepi can ke tepi lubang:

```
sudut_tersedia = atan( (r_lubang - r_lensa) / jarak_tenggelam )
```

| Sensor | FOV | r_lensa | r_lubang | Tenggelam | Sudut tersedia | Hasil |
|---|---|---|---|---|---|---|
| Kamera IMX415 (90° H) | butuh 45° | 8,0 mm (barrel+jam nut Ø16) | 12,0 (Ø24) | 3,0 mm | **53,1°** | aman, margin 8,1° |
| MLX90614 (90°) | butuh 45° | 4,55 mm (can Ø9,1) | 8,0 (Ø16) | 1,5 mm | **66,5°** | aman, margin 21,5° |

> **Catatan penting (kesalahan yang sudah diperbaiki).** Draf pertama memakai
> **Ø14 mm** untuk sensor IR. Dengan Ø14: `atan((7−4,55)/1,5) = 58,5°`, tapi
> begitu can ditenggelamkan lebih dalam (mis. 2,5 mm agar terlindung), sudutnya
> turun ke **43,6° < 45°** → **vignetting**. Karena itu Ø dinaikkan ke
> **Ø16 mm**. Kamera juga dinaikkan dari Ø22 ke **Ø24 mm** supaya marginnya
> cukup bila lensa duduk lebih dalam.

## 2. Uji sinar: lubang benar-benar tembus

Ray-casting dari dalam ke luar pada `01_front_bezel.stl`:

| Titik uji | Permukaan dipotong | Arti |
|---|---|---|
| kamera, IR, tombol, 2× LED, 3× mic, baut M3, post LCD | **0** | benar-benar berlubang |
| margin kiri/kanan, bawah layar, antara layar & IR | **2** | material padat (kontrol negatif) |
| sudut & tengah cutout layar | **0** | cutout tembus penuh |

Kontrol negatif ini penting: tanpa itu, "lubang tembus" bisa saja lolos karena
sinar keluar lewat sisi luar plat, bukan karena ada lubang. (Kasus itu memang
sempat terjadi pada titik uji (3,3) mm yang berada di radius pembulatan sudut
plat 8 mm — titik ujinya dipindah, bukan desainnya yang diubah.)

## 3. Uji sinar: bodi

| Uji | Hasil |
|---|---|
| kedalaman bodi | 54,00 mm (target 54,0) |
| rongga dalam (dari muka terbuka) | sinar memotong 0 permukaan → rongga benar kosong |
| dinding belakang ada | sinar memotong 2 permukaan |

## 4. Uji sinar: dinding belakang vs PCB Orange Pi

PCB Orange Pi 4 Pro (89 × 56) di center (110, 72) menempati
**x 65,5–154,5, y 44,0–100,0**.

| Lubang | Posisi | Bebas dari PCB? |
|---|---|---|
| Glad kabel Ø20 | (110, 24) | **ya** — 20 mm di bawah tepi PCB |
| Saklar Ø13 | (110, 200) | **ya** — 100 mm di atas tepi PCB |

> **Kesalahan yang sudah diperbaiki.** Draf pertama menaruh glad di (110, 60) —
> persis di tengah PCB → kabel akan menembus board. Dipindah ke **y = 24 mm**.

## 5. Kecocokan komponen

| Pemeriksaan | Hasil |
|---|---|
| Orange Pi 4 Pro (89 × 56) muat di rongga 212 × 292 × 50 | PASS (margin > 10 mm tiap sisi) |
| Modul LCD 7" (outline 164,9 × 107) muat di plat 220 × 300 | PASS |
| Cutout 158,21 × 89,92 mm | PASS, masih ada 30,9 mm margin kiri/kanan |
| Tinggi total board + header (± 28 mm) vs rongga 50 mm | PASS, sisa 22 mm |
| Jarak kamera ↔ IR | 41,0 mm (min 24 mm agar dinding antar-lubang ≥ 4 mm) |

## 6. Integritas berkas 3D

11 STL + 1 rakitan — semuanya **watertight** dan dimensinya persis sama
dengan `params.py`:

| Berkas | Dimensi (mm) | Watertight |
|---|---|---|
| `00_assembly_front_body` | 220 × 300 × 60 | ✓ |
| `01_front_bezel` | 220 × 300 × 6 | ✓ |
| `02_body_tray` | 220 × 300 × 54 | ✓ |
| `03_back_panel` | 220 × 300 × 6 | ✓ |
| `10_bracket_camera` | 46 × 46 × 4 | ✓ |
| `11_bracket_ir` | 26 × 20 × 4 | ✓ |
| `12_standoff_lcd_h16` | Ø16 × 16 | ✓ |
| `13_standoff_ir_h14` | Ø14 × 14 | ✓ |
| `14_corner_bracket` | 30 × 30 × 30 | ✓ |
| `15_foot` | 60 × 40 × 8 | ✓ |
| `16_boss_tripod` | Ø24 × 12 | ✓ |

## 7. Cara membaca hasil uji

- **PASS** = diukur ulang dari geometri dan sesuai.
- **FAIL** = ada ketidakcocokan → perbaiki `cad/params.py`, jangan tambal STL.

Kalau Anda mengubah satu angka di `params.py`, jalankan ulang berurutan:
`gen2d.py` → `gen3d.py` → `preview.py` → `verify.py`. Selama `verify.py`
masih "SEMUA PASS", 2D, 3D, preview, dan dokumen tetap sinkron.
