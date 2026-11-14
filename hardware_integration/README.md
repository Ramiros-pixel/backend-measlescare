# hardware_integration

Desain mekanik (enclosure / box custom) untuk **MeaslesWatch AI** — kiosk
screening IoT 1 prototipe. Folder ini **hanya menambah** berkas desain; tidak
mengubah kode backend, tidak mengubah tabel/kolom database, tidak menyentuh
`app/`, `Rules.md`, atau `dokumentasi_database_erd.md`.

Baca dulu: **[documentation.md](documentation.md)** (rincian lengkap,
sumber tiap angka, cara pakai di Tinkercad, dan daftar yang masih perlu
diverifikasi ke unit fisik).

## Isi singkat

```
hardware_integration/
├─ documentation.md            <- DOKUMENTASI UTAMA (mulai dari sini)
├─ docs/01..07_*.md            <- dokumen pendukung (komponen, dimensi, lubang, tinkercad, rakit, verifikasi, asumsi)
├─ cad/
│  ├─ params.py                <- SATU-SATUNYA sumber angka (satuan mm)
│  ├─ gen2d.py                 <- hasilkan SVG 1:1 + DXF (tanpa dependensi)
│  ├─ gen3d.py                 <- hasilkan STL siap cetak/impor
│  ├─ preview.py               <- gambar PNG tampak depan + isometrik
│  ├─ verify.py                <- uji otomatis 45 pemeriksaan
│  ├─ svgkit.py                <- helper path SVG/DXF
│  ├─ openscad/*.scad          <- skrip CAD parametrik (OpenSCAD)
│  └─ out/                     <- HASIL (SVG, DXF, STL, PNG) - siap dipakai
└─ reference/                  <- RAB asli + teks ekstraknya
```

## Ukuran kotak

| Bagian | Ukuran | Keterangan |
|---|---|---|
| **Plat muka (front bezel)** | **220 x 300 x 6 mm** | semua lubang komponen ada di sini |
| Kedalaman total kiosk | **60 mm** | body 54 mm + plat muka 6 mm |
| Rongga dalam | 212 x 292 x 50 mm | cukup untuk Orange Pi 4 Pro (89x56) + layar + kabel |

## Lubang pada plat muka (ringkas)

| Komponen | Bentuk | Ukuran | Posisi (X, Y) dari kiri-bawah |
|---|---|---|---|
| Layar 7" IPS 1024x600 | lubang persegi | **158.21 x 89.92 mm** | center (110.0, 118.0) |
| Kamera IMX415 (PCB 38x38, lens M12) | bulat + chamfer 45° | **Ø24.0 mm** | center (110.0, 246.0) |
| Sensor suhu MLX90614 (GY-906) | bulat | **Ø16.0 mm** | center (110.0, 205.0) |
| Mikrofon (3 lubang) | bulat | Ø2.5 mm | X 96 / 110 / 124, Y 222.0 |
| Tombol daya | bulat | Ø12.0 mm | (160.0, 34.0) |
| LED daya & status | bulat | Ø5.0 mm | (85.0, 34.0) & (105.0, 34.0) |
| Baut plat muka (6x) | bulat | Ø3.4 mm (M3) | inset 8 mm dari tepi |

Angka di atas **sudah dihitung agar lensa tidak terpotong (vignetting)**
oleh tepi lubang — perhitungannya ada di
[docs/06_verifikasi.md](docs/06_verifikasi.md). Kalau ukuran/tipe komponen
yang benar-benar dibeli berbeda, cukup ubah `cad/params.py` lalu jalankan
ulang `python3 cad/gen2d.py` — semua gambar ikut berubah.

## Hasil sekali jalan

```bash
cd hardware_integration
python3 cad/gen2d.py                     # SVG + DXF (tanpa dependensi, pakai python3 apa saja)

# untuk STL / preview / verifikasi, buat venv terpisah (backend tidak tersentuh):
python3 -m venv ~/.hermes/cad-venv
~/.hermes/cad-venv/bin/pip install -r cad/requirements-cad.txt
~/.hermes/cad-venv/bin/python cad/gen3d.py
~/.hermes/cad-venv/bin/python cad/preview.py
~/.hermes/cad-venv/bin/python cad/verify.py     # harus "=== SEMUA PASS ==="
```

## Masuk ke Tinkercad (cara tercepat)

1. Tinkercad → **New 3D Design** → **Import**
2. Pilih `cad/out/01_front_bezel_1to1.svg` (atau salah satu STL di `cad/out/stl/`)
3. Karena SVG-nya memakai `fill-rule="evenodd"`, **semua lubang otomatis
   berlubang** — tinggal tentukan ketebalan (Extrude 6 mm) lalu Export STL.

Langkah rinci + potongan kode untuk **Tinkercad Codeblocks** ada di
[docs/04_tinkercad.md](docs/04_tinkercad.md).
