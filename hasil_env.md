# HASIL DEPLOY — backend-measlescare (Docker)

Tanggal: 18 Oktober 2026 (WIB)
Host: ramirosservers (Linux, 2 GB RAM / 2 core)
Folder: /compe-rams/huawei-inv/backend-measlescare

## 1. Status: BERHASIL DEPLOY & PUBLIK

| Item | Nilai |
|---|---|
| Container backend | `huawei-backend` (Up) |
| Container database | `huawei-db` — MySQL 8.4 (Up, healthy) |
| Image | `backend-measlescare-backend:latest` (FROM python:3.11-slim) |
| Port container | 8000 |
| Binding host | `127.0.0.1:8000` (loopback saja, tidak terbuka ke publik langsung) |
| Volume DB | `backend-measlescare_db_data` -> `/var/lib/mysql` |
| URL publik (internet) | `https://ramirosservers.tail2d4b04.ts.net/api` |
| Swagger docs | `https://ramirosservers.tail2d4b04.ts.net/api/docs` |
| OpenAPI JSON | `https://ramirosservers.tail2d4b04.ts.net/api/openapi.json` |
| Health check | `https://ramirosservers.tail2d4b04.ts.net/api/` |

Basis URL yang dipakai frontend:
```
https://ramirosservers.tail2d4b04.ts.net/api
```

## 2. Environment (.env) — file dibuat di repo, JANGAN di-commit

`.env` dibuat (berada di `.gitignore`) dengan nilai acak hasil `openssl rand`:

```
DB_ROOT_PW=<64 hex acak, lihat /compe-rams/huawei-inv/backend-measlescare/.env>
SECRET_KEY=<64 byte hex acak, lihat .env>
ACCESS_TOKEN_EXPIRE_MINUTES=120
```

Isi persisnya lihat: `/compe-rams/huawei-inv/backend-measlescare/.env` (2 nilai acak terpisah dari `openssl rand -hex`).

Environment yang di-inject ke container backend (via docker-compose.yml):

| Variabel | Nilai | Keterangan |
|---|---|---|
| `DATABASE_URL` | `mysql+pymysql://root:${DB_ROOT_PW}@db:3306/db_huawei` | `db` = nama service MySQL di network compose |
| `SECRET_KEY` | dari `.env` | signing JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `120` | masa berlaku token |
| `API_PREFIX` | `""` (kosong) | **perubahan kode**: dibaca dari env, lihat bagian 4 |

## 3. Yang diubah di repo

1. `docker-compose.yml`
   - Port MySQL `3306:3306` DIHAPUS → DB tidak lagi terekspos ke host/internet,
     hanya bisa diakses lewat network internal compose (lebih aman).
   - Port backend diubah `8000:8000` → `127.0.0.1:8000:8000` (loopback only,
     akses publik lewat Tailscale funnel).
   - `mem_limit: 512m` untuk `db` dan `backend` (RAM host cuma 1.8 GB, sudah dipakai
     stack `mqtt-golang-*`).
   - MySQL tuning hemat RAM: `--innodb-buffer-pool-size=128MB`, `--performance-schema=OFF`.
2. `app/core/config.py`
   - `API_PREFIX` sekarang `os.getenv("API_PREFIX", "/api")`.
     Di container diset `""` supaya tidak muncul path ganda `/api/api/...`
     (funnel me-mount service di path `/api` dan melepas prefix sebelum proxy).
     Default `/api` tetap, jadi pengembangan lokal tidak berubah.

## 4. Routing publik (Tailscale)

Sebelum: `/` -> 127.0.0.1:3000, `/monitor` -> 127.0.0.1:8099
Sesudah (tambah satu path, dua lainnya utuh):

```
https://ramirosservers.tail2d4b04.ts.net        -> 127.0.0.1:3000   (tetap)
https://ramirosservers.tail2d4b04.ts.net/monitor -> 127.0.0.1:8099   (tetap)
https://ramirosservers.tail2d4b04.ts.net/api     -> 127.0.0.1:8000   (backend ini, FUNNEL ON)
```

Perintah yang dipakai:
```bash
tailscale serve --bg http://127.0.0.1:3000
tailscale serve --bg --set-path=/monitor http://127.0.0.1:8099
tailscale funnel --bg --set-path=/api http://127.0.0.1:8000
```
Catatan: `tailscale funnel --bg http://127.0.0.1:8000` TANPA `--set-path` akan merebut
path `/` dan menimpa app lain — selalu pakai `--set-path`.

## 5. Database di Docker

Database MySQL 8.4 berjalan di container `huawei-db` (volume persisten, data aman
saat container di-recreate).

```
mysql+pymysql://root:<DB_ROOT_PW>@127.0.0.1:3306/db_huawei   # hanya dari dalam network docker
```

Akses shell DB:
```bash
docker exec -it huawei-db mysql -uroot -p"$(grep DB_ROOT_PW .env | cut -d= -f2)" db_huawei
```

Tabel yang sudah terbentuk (auto `create_all` saat startup backend):
`Users`, `Role`, `Gejala`, `Camera`, `Status`

Akun default hasil seed: `NIK=admin` / `password=admin123` (role Admin) —
**ganti segera setelah login pertama.**

## 6. Verifikasi yang benar-benar dijalankan

| Tes | Hasil |
|---|---|
| `docker compose build` | sukses (image built) |
| `docker compose up -d` | `huawei-db` healthy, `huawei-backend` Up |
| Log startup | `>> Akun admin default dibuat: NIK=admin / password=admin123`, `Application startup complete` |
| `GET http://127.0.0.1:8000/` (loopback) | `{"status":"ok","app":"Huawei ICT Backend"}` |
| `POST https://.../api/auth/login` (admin/admin123) | 200, `access_token` JWT panjang 144 karakter |
| `GET https://.../api/users/me` + Bearer token | 200 — `{"NIK":"admin","Name":"Administrator","id_Role":"R1","role_name":"Admin"}` |
| `GET https://.../api/openapi.json` | 200 |
| `SHOW TABLES` di `db_huawei` | Camera, Gejala, Role, Status, Users |
| Port 3306 di host | tidak listened (DB tidak publik) |

## 7. Cara pakai dari frontend

```
POST {BASE}/auth/login     {"NIK": "...", "password": "..."}   -> {access_token}
POST {BASE}/auth/register  UserCreate (id_Role R1=Admin, R2=User)
GET  {BASE}/users/me       Authorization: Bearer <token>
GET  {BASE}/openapi.json   untuk generate client / import Postman
```
`{BASE}` = `https://ramirosservers.tail2d4b04.ts.net/api`

CORS sudah `allow_origins=["*"]` di `app/main.py`, jadi frontend dari domain manapun
bisa langsung panggil. Untuk production lebih baik di-pinning ke domain frontend.

## 8. Operasi harian

```bash
cd /compe-rams/huawei-inv/backend-measlescare
docker compose ps                     # status
docker compose logs -f backend        # log backend
docker compose restart backend        # restart
docker compose up -d --build          # redeploy setelah ubah kode
docker compose down                   # stop (volume DB tetap ada)
```
Backup DB:
```bash
docker exec huawei-db mysqldump -uroot -p"$(grep DB_ROOT_PW .env | cut -d= -f2)" \
  --single-transaction db_huawei > backup_$(date +%F).sql
```

## 9. Catatan / sisa pekerjaan

- HTTPS publik disajikan Tailscale funnel (sertifikat valid, port 443). URL memakai
  domain `*.tail2d4b04.ts.net` — kalau butuh domain sendiri, perlu Caddy/Nginx di depan
  loopback 8000, bukan sekadar ubah funnel.
- Ganti password `admin123` sekarang juga; backend ini terbuka untuk publik.
- Pin CORS ke domain frontend sebelum dipakai lama.
- `app/routers/gejala.py` tidak punya prefix sendiri, endpoint-nya langsung di root
  (`{BASE}/camera/...` dsb sesuai OpenAPI).
- Funnel punya batas bandwidth Tailscale; untuk trafik produksi tinggi sebaiknya pakai
  VPS/reverse-proxy sendiri.
