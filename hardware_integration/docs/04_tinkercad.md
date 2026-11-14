# 04 — Memakai desain ini di Tinkercad

Tinkercad 3D Design **menerima impor SVG dan STL**. Itu jalur yang dipakai di
sini. Codeblocks (mode script) hanya drag-block, **tidak** menerima tempelan
JavaScript, jadi jangan diandalkan untuk presisi — pakai SVG/STL.

## Ringkasan tiga jalur

| Jalur | Presisi | Hasil | Pakai kalau |
|---|---|---|---|
| **A. Impor SVG 1:1 lalu extrude** | tinggi (angka mm) | plat/dinding 2D → 3D | mau ubah-ubah cepat di Tinkercad |
| **B. Impor STL siap pakai** | tertinggi | model 3D lengkap | langsung cetak / render |
| **C. OpenSCAD** (bukan Tinkercad) | tertinggi, parametrik | STL apa pun | mau ubah ukuran lewat satu angka |

---

## A. Impor SVG lalu extrude (disarankan untuk Tinkercad)

Berkas: `cad/out/01_front_bezel_1to1.svg`, `02_back_panel_1to1.svg`,
`03_side_panel_left_1to1.svg`, `04_top_bottom_1to1.svg`, `05_brackets_1to1.svg`

1. Buka <https://www.tinkercad.com> → **Create** → **3D Design**.
2. Klik **Import** (kanan atas) → **Choose a file** → pilih SVG.
3. Objek muncul. SVG ini sudah memakai `fill-rule="evenodd"`, jadi **lubang
   sudah benar-benar berlubang** — Tinkercad tidak perlu dikurangi satu per satu.
4. Atur ketebalan: klik objek → tarik handle putih ke atas → ketik angka:
   - plat muka / plat belakang: **6**
   - dinding samping / atas-bawah: **4**
5. **Cek skala.** Tinkercad kadang menganggap 1 satuan = 1 px. Setelah impor,
   lihat kotak ukuran: harus tertulis **220 × 300** (plat muka). Kalau angkanya
   lain, klik objek → **Edit → Scale** → masukkan 220 pada sisi yang sesuai.
   Alternatif paling aman: pakai berkas **STL** (jalur B) yang skalanya pasti.

> Tips: simpan satu salinan plat muka apa adanya sebagai "master", lalu
> duplikat untuk eksperimen.

## B. Impor STL siap pakai

Berkas: `cad/out/stl/*.stl` (11 part + 1 rakitan).

1. **Create → 3D Design → Import** → pilih mis. `01_front_bezel.stl`.
2. Dimensi sudah pasti (lihat tabel di `documentation.md` bagian 7).
3. Untuk merakit: impor part satu per satu, lalu pakai **Align** (tombol L)
   untuk memusatkan, dan **Ruler** (tombol R) untuk memberi jarak presisi.
4. Export: **Export → .STL / .OBJ** untuk cetak.

**Rakitan tampak depan + bodi:** `00_assembly_front_body.stl` (220 × 300 × 60).

## C. OpenSCAD (kalau ingin parametrik penuh)

`cad/openscad/01_front_bezel.scad` dan `02_body_tray.scad` berisi angka yang
sama dengan `params.py`. Jalankan:

```bash
openscad -o bezel.stl -D 'FRONT_W=220' cad/openscad/01_front_bezel.scad
```

Tidak punya OpenSCAD? Berkas itu tetap berguna sebagai rujukan angka.

---

## Bagaimana kalau ukuran komponen berubah?

Jangan menambal gambar. Ubah **satu** tempat saja:

```bash
cd hardware_integration
# 1) ubah angka (mis. jarak lubang baut Orange Pi)
$EDITOR cad/params.py
# 2) hasilkan ulang 2D
python3 cad/gen2d.py
# 3) hasilkan ulang 3D + preview
~/.hermes/cad-venv/bin/python cad/gen3d.py
~/.hermes/cad-venv/bin/python cad/preview.py
# 4) verifikasi ulang
~/.hermes/cad-venv/bin/python cad/verify.py     # harus "=== SEMUA PASS ==="
```

Semua SVG, DXF, STL, dan dokumen mengikuti angka itu, sehingga tidak ada
versi yang basi.

---

## Catatan Codeblocks (biar tidak salah harap)

Tinkercad **menghapus** fitur "Custom Shape Generator" berbasis JavaScript.
Codeblocks sekarang memakai blok seret (Scratch-like): tersedia shapes
primitif, `count`/`repeat` loop, variabel, dan operasi matematika.
Cukup untuk pola berulang, **tidak** nyaman untuk lubang presisi 0,1 mm.

Karena itu, untuk desain ini selalu pakai **SVG** atau **STL**. Kalau tetap
ingin alur "script", pakai OpenSCAD (bagian C).
