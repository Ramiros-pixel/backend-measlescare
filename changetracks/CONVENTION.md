# Konvensi `changetracks/` — pelacakan perubahan per prompt

Tujuan: setiap prompt yang mengubah berkas meninggalkan jejak yang bisa diaudit —
**apa sebelum**, **apa sesudah**, **apa bedanya**, dan **prompt mana yang menyebabkannya**.

## Aturan inti (ringkas)

1. **Satu folder per berkas.** Nama folder = path berkas dengan `/` diganti `__`.
   Contoh: `app/routers/auth.py` → `app__routers__auth.py/`.
2. **Satu subfolder per prompt.** Format: `NNN_YYYY-MM-DD_slug-singkat/`, `NNN` urut naik
   (3 digit) per berkas.
3. Setiap subfolder prompt berisi:
   - `before.<ext>` — isi berkas sebelum perubahan (absen → `before.MISSING`)
   - `after.<ext>`  — isi berkas sesudah perubahan (dihapus → `after.DELETED`)
   - `diff.patch`   — unified diff `before` → `after`
   - `PROMPT.md`    — prompt asli, ringkasan, alasan, berkas lain yang ikut berubah
4. **Tidak boleh** ada berkas yang berubah tanpa track. Bila satu prompt mengubah 5 berkas,
   lahir 5 folder track (satu di bawah tiap berkas).

## Cakupan & pengecualian

| Hal | Perlakuan |
| :--- | :--- |
| Semua berkas di root repo (kode, docs, tools, config) | **dilacak** |
| `.env` | isi **tidak pernah** disalin (rahasia) — hanya dicatat "changed" |
| Biner / >512 KB (`face_model.yml` 13 MB, dataset `.jpg`) | metadata + hash saja, isi tidak disalin |
| `changetracks/` sendiri | dikecualikan (kecuali indeks `MANIFEST.json`, `INDEX.md`) |
| `.git/`, `.venv/`, `__pycache__/` | dikecualikan |

## Baseline

`_baseline/` = snapshot teks saat pelacakan dimulai (lihat `_baseline/MANIFEST.json`).
Track `001` memakai baseline sebagai `before` bila berkas sudah ada sebelumnya.

## Alur kerja (dijalankan setiap prompt)

1. Tentukan berkas yang akan berubah; catat isi lamanya sebagai `before`.
2. Lakukan perubahan.
3. Tulis `after`, buat `diff.patch` (`diff -u`), tulis `PROMPT.md`.
4. Perbarui `MANIFEST.json` (daftar track) dan `INDEX.md` (ringkasan).
5. Kalau perubahannya layak di-commit: commit di **branch baru** (bukan `main`),
   push, lalu serahkan ke pemilik untuk merge manual.

## Alat bantu

```bash
# 1) buat track untuk satu berkas (after diambil dari isi berkas di disk)
python3 changetracks/tools/track.py --file app/routers/auth.py \
    --prompt "<prompt asli pemilik>" --summary "slug-singkat" \
    --reason "kenapa diubah" --related "app/services/foo.py,Documentation.md"

# berkas baru -> before otomatis MISSING; berkas yang sudah ada di baseline -> tambahkan
#   --before-from-baseline
# pratinjau tanpa menulis apa pun -> tambahkan --dry-run

# 2) bangun ulang indeks
python3 changetracks/tools/index.py
```

## Penamaan branch

```
track/<slug-prompt>          contoh: track/tambah-endpoint-ringkasan-tren
```

Satu branch per prompt/pekerjaan; `main` hanya diperbarui lewat merge manual pemilik.
