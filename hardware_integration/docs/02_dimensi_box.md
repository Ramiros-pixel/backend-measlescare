# 02 — Dimensi & tata letak box

Semua satuan **milimeter (mm)**. Sumber angka: `cad/params.py`
(satu-satunya tempat mengubah dimensi — script lain membacanya).

## 1. Ukuran luar box

| Bagian | Ukuran | Keterangan |
|---|---|---|
| Plat muka (bezel) | **220 × 300 × 6 mm** | sisi yang menghadap pasien |
| Bodi/tray | **220 × 300 × 54 mm** | terbuka di sisi muka |
| **Total kedalaman** | **60 mm** | 6 (plat) + 54 (bodi) |
| Rongga dalam | **212 × 292 × 50 mm** | setelah tebal dinding 4 mm |

Plat muka dan bodi **sama besar** (220 × 300). Sisi-sisi bodi dilapisi dinding
4 mm, jadi rongganya 212 × 292 × 50 mm. Kedalaman 60 mm dipilih supaya modul
layar (kaca + board konektor ± 8 mm) + standoff 16 mm + board Orange Pi
(± 28 mm dari dinding belakang) masih sisa ruang.

**Berat perkiraan** (3D print PLA, infill 20%): ± 0,9 kg.

## 2. Plat muka — peta lubang

Origin `(0,0)` = **sudut kiri-bawah** plat muka. X ke kanan, Y ke atas.
Melihat dari **depan** (arah pasien).

| Elemen | Pusat (x, y) | Ukuran | Jenis |
|---|---|---|---|
| Layar (cutout) | 110,0 · 118,0 | **158,21 × 89,92** (sudut R3) | tembus plat |
| Kamera | 110,0 · **246,0** | **Ø24** + chamfer 45° **Ø30** × 3 mm | tembus |
| Sensor IR (MLX90614) | 110,0 · **205,0** | **Ø16** | tembus |
| Mikrofon (3 lubang) | **96 / 110 / 124** · 222,0 | Ø2,5 ×3 | tembus |
| LED daya | 85,0 · 34,0 | Ø5 | tembus |
| LED aktivitas | 105,0 · 34,0 | Ø5 | tembus |
| Tombol fisik (opsi) | 160,0 · 34,0 | Ø12 | tembus |
| Baut plat↔bodi (6×) | 8/212 · 8/150/292 | Ø3,4 (M3) | tembus |

Area **logo** (tidak dipotong) di sekitar (110, 52), kotak 60 × 14 mm.

Jarak aman antar elemen (hasil verifikasi otomatis):
- kamera → cutout layar **83,0 mm**
- IR → cutout layar **42,0 mm**
- mic → cutout layar **59,0 mm**
- tombol → cutout layar **39,0 mm**

## 3. Dinding belakang (plat belakang 220 × 300 × 6)

| Elemen | Posisi (x, y) | Ukuran | Keterangan |
|---|---|---|---|
| Glad kabel | **110 · 24** | Ø20 | Di **bawah** tepi bawah PCB Orange Pi (y = 44) — supaya kabel tidak menembus board |
| Saklar daya (opsi) | **110 · 200** | Ø13 | rocker KCD1 |
| Ventilasi | 7 kolom × 2 baris | slot 20 × 4 | di area atas (y 262 & 284), di atas PCB |
| Baut bodi↔plat | mengikuti 6 lubang plat | Ø3,4 | |

PCB Orange Pi menempati **x 65,5–154,5, y 44–100** — verifikasi otomatis
memastikan glad & saklar tidak tertutup board ini.

## 4. Dinding kiri & kanan (54 × 300 mm, ×2)

- **Ventilasi:** 6 slot **4 × 30 mm** (tegak), mulai y = 60, jarak antar-slot
  14 mm, pada kedalaman z 12–42 mm dari plat muka.
- **Baut sudut** M3 di 4 sudut (inset 8 mm).

## 5. Dinding atas & bawah (54 × 212 mm, ×2)

- Plat penutup sederhana, baut M3 di 4 sudut.
- Slot **cable tie** 4 × 8 mm di 4 titik rongga (60/160 · 20/280) untuk
  merapikan kabel — sesuai RAB no. 13.

## 6. Bodi & bracket dalam

| Bracket | Ukuran | Isi |
|---|---|---|
| Dudukan Orange Pi 4 Pro | plate 95 × 62 × 3, boss 8 mm | 4 **lubang oval** 3,4 × 4 mm agar jarak baut tak terverifikasi tetap bisa dipasang |
| Bracket kamera | 46 × 46 × 4 | lubang Ø16 + **dua set** lubang baut PCB: 30 mm & 24 mm antar-lubang |
| Bracket IR MLX90614 | 26 × 20 × 4 | pocket PCB 17,6 × 11,6 × 3 mm |
| Landasan LCD | 4 × standoff Ø16 × 16 mm | menahan modul 7" dari belakang |
| Siku sudut | 30 × 30 × 30, t 4 | 4×, memperkuat sambungan |
| Kaki | 60 × 40 × 8 | 2× |
| Boss tripod | Ø24 × 12 | 1×, mur 1/4"-20 (opsi pasang di tripod) |

## 7. Lubang baut (spesifikasi bor)

| Sambungan | Baut | Lubang "female" | Lubang lewat |
|---|---|---|---|
| Plat ↔ bodi | M3 × 16 | Ø2,5 (tap M3) | Ø3,4 |
| Bracket ke bodi | M3 × 8 | Ø2,5 (tap) | Ø3,4 |
| Modul LCD ke standoff | M3 × 6 | — | Ø3,4 |
| PCB & sensor ke bracket | M2,5 / M3 self-tapping | Ø2,1 | Ø2,7 |

Toleransi cetak FDM sudah diperhitungkan: tambah **+0,2 mm** pada lubang baut
dan **+0,3 mm** pada pocket jika hasil cetak Anda ternyata rapat. Untuk potong
laser akrilik/plywood, pakai **kerf** alat Anda (biasanya 0,1–0,2 mm) — SVG
`*_lasercut.svg` sudah memisahkan garis potong saja.
