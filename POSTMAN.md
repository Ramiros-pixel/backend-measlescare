# Panduan Postman — Huawei ICT Backend

## Import Koleksi

1. Buka Postman → **Import** → pilih file `postman_collection.json` (ada di folder Backend ini).
2. Koleksi **Huawei ICT Backend API** muncul dengan 5 folder: Meta, Auth, Users, Gejala, Camera.

## Menjalankan Server

```
py main.py
```

Server di `http://127.0.0.1:8000` (sudah jadi variabel `base_url` di koleksi).

## Alur Pengujian

1. **Meta > Health Check** — pastikan server hidup.
2. **Auth > Login (Admin)** atau **Login (User)** —
   token **otomatis tersimpan** ke variabel koleksi `access_token`
   (script test di request login). Tidak perlu copy-paste manual.
3. Semua request berlabel Bearer otomatis memakai token itu.

### Contoh urutan lengkap

| # | Request | Hasil yang diharapkan |
| :-- | :--- | :--- |
| 1 | Auth > Login (Admin) | 200, token tersimpan |
| 2 | Gejala > Catat Gejala | 201, `id_gejala` tersimpan |
| 3 | Camera > Catat Camera | 201, `id_cam` tersimpan |
| 4 | Gejala > History (Admin) | 200, riwayat **semua user** |
| 5 | Gejala > History (Admin - filter NIK) | 200, riwayat 1 user |
| 6 | Auth > Login (User) | 200, token berganti ke user |
| 7 | Gejala > History (User) | 200, **hanya riwayat sendiri** |
| 8 | Gejala > History (Admin - filter NIK) | **403** — user biasa dilarang filter NIK orang lain |
| 9 | Users > List Users (Admin only) | **403** — akses khusus Admin |
| 10 | Users > Detail User by NIK | 200 bila NIK sendiri, **403** bila orang lain |

## Variabel Koleksi

| Variabel | Isi | Diatur oleh |
| :--- | :--- | :--- |
| `base_url` | `http://127.0.0.1:8000` | manual (bila port beda) |
| `access_token` | JWT login terakhir | otomatis saat login |
| `nik_user` | `3201234567890001` | manual (akun uji user) |
| `pass_user` | `rahasia123` | manual |
| `id_gejala` | id gejala terakhir | otomatis saat Catat Gejala |
| `id_cam` | id camera terakhir | otomatis saat Catat Camera |

Akun seed: **admin / admin123** (R1). Akun user uji dibuat lewat
**Auth > Register** dengan `id_Role: R2`.

## Kode Status

| Kode | Arti |
| :--- | :--- |
| 200 / 201 | Sukses |
| 401 | Token hilang/salah/kedaluwarsa (login lagi) |
| 403 | Bukan Admin, atau mengakses data user lain |
| 404 | Data tidak ditemukan |
| 409 | NIK sudah terdaftar |
| 422 | Body tidak sesuai skema (cek Suhu 30-45, NIK 16 digit, dll.) |
