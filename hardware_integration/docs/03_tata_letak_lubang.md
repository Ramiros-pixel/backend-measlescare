# 03 — Tabel lengkap tata letak lubang

Kerangka: origin **(0,0) = sudut kiri-bawah plat muka**, X ke kanan, Y ke atas,
melihat dari **depan**. Z = kedalaman (0 di permukaan muka, +60 ke belakang).
Semua angka mm dan diukur ke **pusat lubang**.

## A. Plat muka (220 × 300 × 6)

Tebal 6 mm; semua lubang **tembus**.

| # | Elemen | X | Y | Ø / ukuran | Keterangan |
|---|---|---|---|---|---|
| 1 | Cutout layar | 110,0 | 118,0 | 158,21 × 89,92, R3 | active area + 2 mm tiap sisi |
| 2 | Lubang kamera | 110,0 | 246,0 | **Ø24** | + chamfer 45° Ø30 × 3 mm di sisi dalam |
| 3 | Lubang sensor IR | 110,0 | 205,0 | **Ø16** | MLX90614 (can Ø9,1) |
| 4 | Mic kiri | 96,0 | 222,0 | Ø2,5 | jalur suara modul kamera |
| 5 | Mic tengah | 110,0 | 222,0 | Ø2,5 | idem |
| 6 | Mic kanan | 124,0 | 222,0 | Ø2,5 | idem |
| 7 | LED daya | 85,0 | 34,0 | Ø5 | pilot lamp 5 mm |
| 8 | LED aktivitas | 105,0 | 34,0 | Ø5 | pilot lamp 5 mm |
| 9 | Tombol fisik (opsi) | 160,0 | 34,0 | Ø12 | push button metal |
| 10 | Baut sudut LB | 8,0 | 8,0 | Ø3,4 | M3 |
| 11 | Baut sudut RB | 212,0 | 8,0 | Ø3,4 | M3 |
| 12 | Baut sudut LT | 8,0 | 292,0 | Ø3,4 | M3 |
| 13 | Baut sudut RT | 212,0 | 292,0 | Ø3,4 | M3 |
| 14 | Baut tengah kiri | 8,0 | 150,0 | Ø3,4 | M3 |
| 15 | Baut tengah kanan | 212,0 | 150,0 | Ø3,4 | M3 |
| 16 | Area logo | 110,0 | 52,0 | 60 × 14 (tidak dipotong) | sablon/stiker |

## B. Plat belakang (220 × 300 × 6)

| # | Elemen | X | Y | Ø / ukuran | Keterangan |
|---|---|---|---|---|---|
| 1 | Glad kabel | 110,0 | **24,0** | **Ø20** | PG-7/PG-9 + HDMI + USB-C |
| 2 | Saklar daya (opsi) | 110,0 | 200,0 | Ø13 | rocker KCD1 |
| 3–16 | Ventilasi atas | 50 + 20·n (n=0..6) | 262 & 284 | slot 20 × 4 | 7 kolom × 2 baris = 14 slot |
| 17–22 | Baut ke bodi | sama seperti plat muka | — | Ø3,4 | 6× M3 |

> Verifikasi otomatis memastikan glad (y=24) berada **di bawah** tepi bawah PCB
> Orange Pi (y=44), jadi kabel tidak menembus board.

## C. Dinding samping kiri & kanan (54 × 300, 2×)

Pada gambar 2D `03_side_panel_*`, sumbu gambar: **X = kedalaman (54)**,
**Y = tinggi (300)**.

| # | Elemen | X (kedalaman) | Y (tinggi) | Ukuran |
|---|---|---|---|---|
| 1 | Ventilasi (6 slot) | 12 … 42 | 60, 74, 88, 102, 116, 130 | slot 30 (X) × 4 (Y) |
| 2 | Baut sudut | 8 & 46 | 8 & 292 | Ø3,4 ×4 |

## D. Dinding atas & bawah (54 × 212, 2×)

| # | Elemen | X | Y | Ukuran |
|---|---|---|---|---|
| 1 | Baut sudut | 8 & 46 | 8 & 204 | Ø3,4 ×4 |

## E. Bracket dalam (tampak atas)

| Bracket | Lubang | Posisi | Ukuran |
|---|---|---|---|
| Dudukan Orange Pi | 4× oval | center (110, 72) ± 41 / ± 24,5 | slot 3,4 × 4 |
| Bracket kamera | 1 center + 8 baut | center (110, 246) | Ø16 + Ø2,7 (2 set: 30 & 24 mm) |
| Bracket IR | 1 center + pocket | center (110, 205) | Ø16 + pocket 17,6 × 11,6 × 3 |
| Standoff LCD | 4× | sudut cutout layar + 6 mm ke luar | Ø3,4, tinggi 16 |

## F. Ringkasan jumlah lubang

| Bagian | Jumlah lubang tembus |
|---|---|
| Plat muka | 15 (plus 1 area logo tanpa potong) |
| Plat belakang | 22 (6 baut + 1 glad + 1 saklar + 14 ventilasi) |
| Dinding samping (×2) | 10 per sisi (6 ventilasi + 4 baut) |
| Dinding atas/bawah (×2) | 4 per sisi |

Titik-titik ini diekspor otomatis ke `cad/out/` dalam tiga format:
SVG 1:1 (Tinkercad/CNC), SVG garis potong (laser), dan DXF (CAD 2D).
