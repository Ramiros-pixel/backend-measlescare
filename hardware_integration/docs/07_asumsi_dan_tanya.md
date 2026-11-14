# 07 — Asumsi desain & yang perlu Anda konfirmasi

## A. Asumsi yang dipakai (harus dikoreksi kalau salah)

Angka di bawah **tidak ada di RAB** dan tidak bisa dipastikan tanpa mengukur
unit fisik. Saya pilih nilai paling aman (menerima varian terbesar), lalu
dibuat toleran (slot oval, bracket dengan 2 set lubang) supaya tetap bisa
dipakai walau meleset.

| # | Asumsi | Nilai dipakai | Kalau salah, ubah di `params.py` |
|---|---|---|---|
| 1 | Jarak lubang baut Orange Pi 4 Pro | 82 × 49 mm (inset 3,5 mm) | `PI_BOARD_W/H`, `PI_HOLE_INSET` |
| 2 | Posisi PCB Orange Pi di dalam box | center (110, 72) | `PI_CX`, `PI_CY` |
| 3 | Modul kamera = PCB 38 × 38, lens holder M12, FOV 90° | Ø24 + chamfer 30 | `CAM_HOLE_D`, `CAM_CHAMFER_D` |
| 4 | Layar = 7" IPS 1024×600, active area 154,2144 × 85,92 | cutout 158,21 × 89,92 | `LCD_ACTIVE_W/H` |
| 5 | Tombol fisik Ø12 mm (RAB tidak mencantumkan tombol) | Ø12 | `BTN_HOLE_D`, `BTN_XY` |
| 6 | Glad kabel Ø20 mm (PG-9) untuk HDMI + USB-C + adaptor | Ø20 di (110, 24) | `GLAND_D`, `GLAND_XY` |
| 7 | Saklar daya utama Ø13 mm (opsi, RAB tidak mencantumkan) | Ø13 di (110, 200) | `SWITCH_D`, `SWITCH_XY` |
| 8 | Bahan: plat 6 mm, dinding 4 mm (FDM/akrilik) | 6 / 4 | `PANEL_T`, `WALL_T` |
| 9 | LED indikator Ø5 mm ×2 diletakkan di bawah layar | Ø5 | `LED_*` |
| 10 | Mic = 3 lubang Ø2,5 di atas layar (modul webcam punya mic) | Ø2,5 | `MIC_*` |

Semua asumsi ini dikumpulkan di `cad/params.py` dengan tanda `[DES]`, jadi
mudah dicari: `grep '\[DES\]' cad/params.py`.

## B. Pertanyaan yang perlu Anda jawab

Saya lanjutkan dengan asumsi di atas (sesuai permintaan: kalau lama, lanjut
dengan rekomendasi saya). Begitu Anda punya jawabannya, cukup beri tahu —
saya perbarui satu berkas dan hasilkan ulang semuanya.

1. **Orange Pi 4 Pro sudah di tangan?** Kalau ya, tolong ukur jarak keempat
   lubang bautnya (mm) — itu satu-satunya angka yang paling berisiko.
2. **Modul kamera mana yang dibeli** — IMX415 8MP (PCB besar) atau IMX219 CSI
   (PCB 25 × 24) atau webcam biasa? Bracket sudah punya 2 set lubang, tapi
   diameter lubang plat bisa berubah kalau lensanya lebih besar.
3. **Layar mana yang dipakai** — KLYSTR / LCD IPS / CNC Store? Ketiganya 7"
   1024×600 jadi cutout sama, tapi tebal bodi bisa beda. Boleh tolong ukur
   **lebar & tinggi kaca aktifnya** (bukan seluruh modul).
4. **Ada tombol fisik & saklar daya?** RAB tidak mencantumkan. Desain sudah
   menyiapkan Ø12 (tombol) dan Ø13 (saklar) — bilang saja kalau tidak dipakai,
   saya hapus lubangnya supaya box lebih rapat.
5. **Proses produksi** — 3D print FDM, atau akrilik/plywood potong laser?
   - FDM: pakai STL (`cad/out/stl/`), toleransi sudah +0,2 mm.
   - Laser: pakai `*_lasercut.svg`, dan **beri tahu kerf** mesin Anda.
6. **Unit dipasang di mana** — duduk di meja (pakai 2 kaki), ditempel dinding,
   atau di tripod? Kalau tripod, boss Ø24 (mur 1/4"-20) sudah ada.
7. **Ruangan berdebu / banyak cahaya?** Kalau ya, saya bisa tambahkan bibir
   lebih dalam di cutout kamera + filter kasa di ventilasi.
