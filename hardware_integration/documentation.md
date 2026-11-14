# Documentation — Hardware Integration (Enclosure MeaslesWatch AI)

Dokumen ini merinci **desain box custom** untuk perangkat MeaslesWatch AI,
lengkap dengan **posisi & diameter tiap lubang**, dasar perhitungannya, dan
cara memakainya di **Tinkercad**.

> Ruang lingkup: folder ini **hanya menambah**. Tidak ada berkas backend,
> tabel, atau kolom yang diubah. Semua angka berasal dari komponen yang
> benar-benar ada di RAB, lalu diverifikasi perhitungan geometri (lihat
> [docs/06_verifikasi.md](docs/06_verifikasi.md)).

---

## 1. Ringkasan cepat

| Item | Nilai |
|---|---|
| Dimensi kotak (dipakai kerja) | **220 × 300 × 60 mm** (L × T × D) |
| Plat muka (front bezel) | 220 × 300 × **6 mm** |
| Bodi / tray | 220 × 300 × **54 mm**, buka di sisi muka |
| Rongga dalam | 212 × 292 × 50 mm |
| Berat perkiraan (3D print PLA 20% infill) | ± 0,9 kg |
| Jumlah berkas 2D siap potong | 6 (SVG 1:1 + DXF) |
| Jumlah part 3D | 11 (STL, semuanya watertight) |
| Jumlah lubang tembus plat muka | 15 |
| Berkas preview (PNG, lihat hasil tanpa CAD) | 4 |

---

## 2. Daftar isi dokumen

| Dokumen | Isi |
|---|---|
| [docs/01_komponen.md](docs/01_komponen.md) | Komponen dari RAB → dimensi yang dipakai (dengan sumber) |
| [docs/02_dimensi_box.md](docs/02_dimensi_box.md) | Kenapa 220 × 300 × 60 mm; perhitungan rongga |
| [docs/03_tata_letak_lubang.md](docs/03_tata_letak_lubang.md) | **Tabel lengkap posisi & diameter 17 lubang** |
| [docs/04_tinkercad.md](docs/04_tinkercad.md) | Cara impor SVG/STL ke Tinkercad + kode Codeblocks |
| [docs/05_assembly.md](docs/05_assembly.md) | Urutan rakit, baut, torsi, jalur kabel |
| [docs/06_verifikasi.md](docs/06_verifikasi.md) | Perhitungan vignetting & hasil uji otomatis |
| [docs/07_asumsi_dan_tanya.md](docs/07_asumsi_dan_tanya.md) | Asumsi desain + **yang perlu Anda konfirmasi** |

---

## 3. Geometri: kerangka koordinat

Semua angka memakai kerangka yang sama (supaya tidak salah tafsir saat
memotong):

```
        Y (ke atas, 300 mm)
        ^
        |     ┌──────────────────────────────┐  ← tepi atas plat
        |     │  ● kamera   (110, 246)       │
        |     │  ● sensor IR (110, 205)      │
        |     │  ┌────────────────────────┐  │
        |     │  │   LAYAR 7" (landscape) │  │
        |     │  │   cutout 158.2 × 89.9  │  │
        |     │  └────────────────────────┘  │
        |     │  ● LED LED        [tombol]   │
        |     └──────────────────────────────┘
        +---------------------------------------> X (ke kanan, 220 mm)
      (0,0) = sudut KIRI-BAWAH plat muka

   Z = kedalaman: 0 di permukaan depan plat, +54 mm ke arah belakang.
   Pengamat / pasien berada di sisi Z negatif.
```

**Cara membaca posisi:** `(X, Y)` selalu dari **sudut kiri-bawah** plat muka,
diukur ke **titik pusat** lubang (bukan ke tepi lubang). Semua dalam mm.

---

## 4. Tiga cara memakai desain ini di Tinkercad

### Cara A — impor STL (paling cepat, hasil pasti)

1. Buka <https://www.tinkercad.com> → **Create** → **3D Design**
2. **Import** → pilih `cad/out/stl/01_front_bezel.stl` (atau `02_body_tray.stl`)
3. Objek muncul siap diedit. Export ulang bila perlu:
   **Export → .STL / .OBJ**

### Cara B — impor SVG 1:1 lalu extrude (paling enak untuk dimodifikasi)

1. **Import** → pilih `cad/out/01_front_bezel_1to1.svg`
2. SVG-nya sudah memakai `fill-rule="evenodd"`, jadi **semua lubang sudah
   berlubang di dalam shape** — tidak perlu dikurangi satu per satu.
3. Atur ketebalan: klik shape → tarik handle putih ke atas → ketik **6**
   (mm) di kotak ukuran, atau pakai **Shape → Solid → Extrude**.
4. Skala: SVG sudah **1:1 mm**, jadi setelah impor pastikan dimensinya
   tertulis 220 × 300 mm (Tinkercad kadang memakai skala 1:1 px → cek angka).

### Cara C — jalur "script CAD" yang sebenarnya (OpenSCAD / Python)

Tinkercad **sudah menghapus** Custom Shape Generator berbasis JavaScript;
Codeblocks sekarang murni blok seret dan tidak menerima tempelan kode. Jadi
untuk alur *script*, dipakai dua ini:

- **Python parametrik** — `cad/params.py` → `gen2d.py` / `gen3d.py`
  (menghasilkan SVG, DXF, STL, dan PNG; ada verifikasi otomatis).
- **OpenSCAD** — `cad/openscad/*.scad`, bisa di-*render* ke STL tanpa Tinkercad.

Detail di [docs/04_tinkercad.md](docs/04_tinkercad.md) bagian C.

---

## 5. Alur kerja yang disarankan

```bash
cd hardware_integration

# 1) ubah angka bila perlu (SATU-SATUNYA tempat mengubah ukuran)
$EDITOR cad/params.py

# 2) hasilkan ulang gambar 2D (SVG 1:1 + DXF) — tanpa dependensi
python3 cad/gen2d.py

# 3) hasilkan ulang model 3D (STL) — butuh venv (lihat requirements-cad.txt)
python3 cad/gen3d.py

# 4) VERIFIKASI: ukur ulang hasil, jangan percaya gambar
python3 cad/verify.py      # harus "=== SEMUA PASS ==="
```

Kalau ada komponen yang ukurannya berbeda dari yang di RAB (mis. modul kamera
yang dibeli ternyata PCB 32×32), **cukup ubah `cad/params.py`** lalu jalankan
kedua generator — semua gambar dan STL ikut berubah konsisten.

---

## 6. Berkas script CAD

| Berkas | Fungsi | Butuh instalasi? |
|---|---|---|
| `cad/params.py` | Sumber tunggal semua angka (mm) | tidak |
| `cad/gen2d.py` | SVG 1:1, SVG laser-cut, SVG A3 berdimensi, DXF | **tidak** (Python stdlib) |
| `cad/gen3d.py` | 11 STL (plat muka, bodi, bracket, dll.) | ya — `cad/requirements-cad.txt` |
| `cad/preview.py` | PNG tampak depan + isometrik (lihat hasil tanpa CAD) | ya — idem |
| `cad/verify.py` | Uji otomatis 45 pemeriksaan | ya — idem |
| `cad/svgkit.py` | Helper pembuat path SVG/DXF | tidak |
| `cad/openscad/01_front_bezel.scad` | Plat muka parametrik (OpenSCAD / Codeblocks) | OpenSCAD (opsional) |
| `cad/openscad/02_body_tray.scad` | Bodi parametrik | OpenSCAD (opsional) |

Pemasangan dependensi 3D (di venv terpisah, **backend tidak tersentuh**):

```bash
python3 -m venv ~/.hermes/cad-venv
~/.hermes/cad-venv/bin/pip install -r cad/requirements-cad.txt
~/.hermes/cad-venv/bin/python cad/gen3d.py
~/.hermes/cad-venv/bin/python cad/verify.py
```

---

## 7. Hasil yang sudah ada di `cad/out/`

**2D (`cad/out/`)** — satuan mm, skala 1:1:

| Berkas | Ukuran | Untuk apa |
|---|---|---|
| `01_front_bezel_1to1.svg` | 220 × 300 | impor Tinkercad / CNC |
| `01_front_bezel_lasercut.svg` | 220 × 300 | laser cut (garis potong saja) |
| `01_front_bezel_A3_dimensi.svg` | A3 | gambar kerja untuk tukang |
| `01_front_bezel.dxf` | 220 × 300 | CAD 2D (AutoCAD/LibreCAD) |
| `02_back_panel_1to1.svg`, `.dxf` | 220 × 300 | plat belakang |
| `03_side_panel_left_1to1.svg`, `.dxf` | 54 × 300 | dinding samping ×2 |
| `04_top_bottom_1to1.svg`, `.dxf` | 54 × 212 | dinding atas/bawah ×2 |
| `05_brackets_1to1.svg`, `05_brackets_A3_label.svg` | — | bracket & standoff |

**3D (`cad/out/stl/`)** — semuanya `watertight = True`:

| Berkas | Dimensi (mm) | Qty |
|---|---|---|
| `01_front_bezel.stl` | 220 × 300 × 6 | 1 |
| `02_body_tray.stl` | 220 × 300 × 54 | 1 |
| `03_back_panel.stl` | 220 × 300 × 6 | 1 |
| `10_bracket_camera.stl` | 46 × 46 × 4 | 1 |
| `11_bracket_ir.stl` | 26 × 20 × 4 | 1 |
| `12_standoff_lcd_h16.stl` | Ø16 × 16 | 4 |
| `13_standoff_ir_h14.stl` | Ø14 × 14 | 4 |
| `14_corner_bracket.stl` | 30 × 30 × 30 | 4 |
| `15_foot.stl` | 60 × 40 × 8 | 2 |
| `16_boss_tripod.stl` | Ø24 × 12 | 1 |
| `00_assembly_front_body.stl` | 220 × 300 × 60 | tampilan rakitan |

**Preview (`cad/out/*.png`)** — untuk dilihat cepat tanpa Tinkercad/CAD:

| Berkas | Isi |
|---|---|
| `preview_front.png` | tampak depan plat muka + label semua lubang |
| `preview_iso.png` | isometrik rakitan plat + bodi |
| `preview_bezel_iso.png` | isometrik plat muka |
| `preview_body_iso.png` | isometrik bodi |

---

## 8. Yang sudah diverifikasi & yang belum

**Sudah diverifikasi otomatis** (`cad/verify.py` → **45 PASS / 0 FAIL**):

- 11 STL watertight + dimensi persis sama dengan `params.py`
- 10 lubang plat muka benar-benar **tembus** (uji sinar)
- 4 titik material benar-benar **padat** (kontrol negatif)
- cutout layar benar-benar tembus di tengah & di sudutnya
- lubang dinding belakang tidak tertutup PCB Orange Pi
- bukaan kamera (53,1°) dan sensor IR (66,5°) **lebih besar** dari FOV 45°
  → **tidak ada vignetting**
- Orange Pi 4 Pro & modul layar muat di rongga/plat

**Belum diverifikasi — butuh Anda** (detail di
[docs/07_asumsi_dan_tanya.md](docs/07_asumsi_dan_tanya.md)):

1. **Jarak lubang baut Orange Pi 4 Pro board Anda.** Angka 82 × 49 mm
   dipakai dari standar SBC; boss sudah dibuat lubang **oval** supaya masih
   bisa dipakai bila meleset ± 2 mm. Kalau ada board-nya, ukur dengan
   jangka sorong.
2. **Tipe modul kamera yang dibeli** (PCB 38×38 atau 32×32) — bracket sudah
   punya lubang untuk keduanya.
3. **Tipe layar** — angka cutout memakai active area 154,21 × 85,92 mm
   (7" IPS 1024×600 standar). Kalau layarnya 7" 1024×600 lain, ukur kaca
   aktifnya.
4. **Tombol daya** yang dipakai (Ø12 mm diasumsikan) dan apakah perlu saklar
   utama di belakang (Ø13 mm sudah disiapkan).
5. **Bahan & proses**: 3D print (FDM) atau akrilik/plywood potong laser?
   Angka tebal plat 6 mm & dinding 4 mm bisa diubah di `params.py`.

> **Prinsip:** kalau ada keraguan pada satu angka, ukur unit fisiknya, ubah
> `cad/params.py`, jalankan ulang generator + verifikasi. Jangan menambal
> gambar secara manual — supaya 2D, 3D, dan dokumen tetap sinkron.
