# 01 — Komponen dari RAB → dimensi yang dipakai desain

Sumber: **RAB MeaslesWatchAI.pdf** (estimasi 1 prototipe, National Stage
21 November 2026). Hanya komponen **yang berhubungan langsung dengan box**
yang dibahas di sini. Kolom "dipakai" = angka yang benar-benar masuk ke
`cad/params.py`.

## A. Edge computing — board yang harus masuk box

| RAB | Komponen | Dimensi board (dipakai) | Catatan |
|---|---|---|---|
| 1 | **Orange Pi 4 Pro** (A733, 8-core, 3 TOPS NPU) — *Utama* | **89 × 56 mm**, 4 lubang baut inset 3,5 mm → jarak 82 × 49 mm | Board utama. Boss-nya dibuat dengan **lubang oval** karena jarak baut ini **belum diverifikasi ke unit fisik**. |
| 2 | Orange Pi Zero 3 (H618) — *Alternatif Hemat* | 65 × 30 mm | Jauh lebih kecil; kalau ini yang dipakai, boss 89×56 tetap aman (board lebih kecil dari boss). |

Tinggi komponen (untuk hitung kedalaman): board + header GPIO + konektor
USB/HDMI tertinggi ± **20 mm** dari PCB; dengan standoff 8 mm → total
± 28 mm dari dinding belakang. Rongga tersedia **50 mm** → aman.

## B. Kamera — penentu lubang besar di bagian atas plat muka

| RAB | Komponen | Dimensi | Dipakai di desain |
|---|---|---|---|
| 4 | **USB Camera Module IMX415 8MP** autofocus, UVC — *Alternatif Modul* | PCB umumnya **38 × 38 mm** (varian 32 × 32), lens holder **M12**, OD barrel + jam nut ± **16 mm** | Lubang kamera **Ø24 mm** + chamfer 45° Ø30 mm. Bracket 46×46 dengan lubang untuk **kedua** varian PCB (30 mm dan 24 mm antar-lubang-baut). |
| 5 | Modul Kamera CSI Sony IMX219 8MP, **FOV 77°** | PCB 25 × 24 mm | FOV lebih sempit dari 90° → lubang Ø24 mm **lebih** dari cukup. Bracket sama bisa dipakai. |
| 3 | USB Webcam 1080P — *Alternatif Hemat* | Body ± 65 × 45 × 30 mm | Terlalu besar untuk dijejalkan di balik plat muka; kalau ini yang dipakai, webcam dipasang **di luar** (di atas box) memakai boss tripod 1/4"-20. |

> **Penting:** angka **90° FOV** dipakai sebagai kasus terburuk (IMX415
> modul lebar). Bukaan Ø24 mm dipilih agar **tidak ada vignetting** sampai
> 90° — lihat perhitungan di [06_verifikasi.md](06_verifikasi.md).

## C. Sensor inframerah — wajib

| RAB | Komponen | Dimensi | Dipakai di desain |
|---|---|---|---|
| 6 | **MLX90614 GY-906 HW-691** — *Wajib* | PCB modul **17 × 11 mm**; can **TO-39 Ø 9,1 mm**; FOV 90° | Lubang **Ø16 mm**, bracket 26 × 20 × 4 dengan **pocket PCB 17,6 × 11,6 × 3 mm** supaya PCB-nya masuk rata. |

## D. Layar — penentu cutout terbesar

| RAB | Komponen | Active area (dipakai) | Modul |
|---|---|---|---|
| 5 | **KLYSTR LCD 7" HDMI IPS 1024×600, capacitive touch** — *Prioritas Utama* | **154,2144 × 85,92 mm** | Outline ± 164,9 × 106,96 × 8 mm (bagian bawah ada board konektor) |
| 6 | LCD IPS 7" HDMI capacitive 1024×600 — *Alternatif 1* | idem | idem |
| 7 | CNC Store LCD 7" HDMI — *Alternatif 2* | idem | idem |

Ketiganya modul 7" 1024×600 standar → **active area sama**, jadi satu cutout
cukup untuk ketiganya. Cutout desain = aktif + 2 mm tiap sisi =
**158,21 × 89,92 mm** (plat menutupi tepi kaca sehingga tidak ada celah bocor
cahaya).

## E. Kelistrikan & pendukung

| RAB | Komponen | Relevansi ke box |
|---|---|---|
| 9 | Adaptor USB-C Orange Pi 4 — 5V 3A | Kabel keluar lewat **lubang glad Ø20 mm** di dinding belakang |
| 10 | Adaptor LCD touchscreen 7" | idem |
| 11 | Mini LED Ring Light USB Ø30 cm | Diletakkan **di luar** box (di depan); tidak dipotong |
| 8 | SanDisk microSD 64GB | Slot microSD Orange Pi 4 Pro ada di tepi board → beri ruang ± 15 mm di sisi itu |
| 12 | Casing/rangka kiosk (akrilik/plywood/3D print) | **itu yang didesain folder ini** |
| 13 | Bracket, bauttie, spacer, cable | Disediakan: bracket kamera, bracket IR, standoff LCD, siku sudut, **slot cable tie** |
| 14 | Terminal listrik / power strip | Di luar box |
| 15 | Cadangan komponen kecil | Kasih ruang lebih di rongga (sudah tersedia) |

## F. Angka yang **belum** bisa dipastikan dari RAB

RAB mencantumkan beberapa *alternatif* per posisi dan tidak ada dimensi
mekanik. Karena itu desain dibuat **di tengah**: memilih komponen dengan
tuntutan ruang terbesar (kamera 90° FOV, layar 7" aktif penuh, board 89×56)
supaya semua alternatif tetap muat. Yang tetap perlu Anda ukur ke unit fisik:

1. Jarak lubang baut **Orange Pi 4 Pro** yang benar-benar dikirim.
2. Apakah modul kamera yang dikirim **PCB 38×38 atau 32×32**.
3. Diameter kaca aktif **persis** layar yang dikirim.
4. Apakah tombol fisik diperlukan (RAB tidak mencantumkan tombol/saklar —
   desain menyiapkan Ø12 mm tombol + Ø13 mm saklar sebagai opsi).

Rincian langkah verifikasinya: [07_asumsi_dan_tanya.md](07_asumsi_dan_tanya.md).
