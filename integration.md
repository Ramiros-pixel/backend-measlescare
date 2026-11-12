# INTEGRATION — backend-measlescare

Panduan kredensial & akses database untuk tim integrasi.

Sumber data: `docker-compose.yml`, `.env`, `app/core/config.py` di repo ini.
Semua nilai di bawah **diverifikasi langsung** terhadap container yang sedang berjalan
(`docker compose ps`, `SHOW DATABASES`, `SHOW TABLES`, login uji) — bukan asumsi dari file saja.

---

## 1. Ringkasan koneksi database

| Item | Nilai |
|---|---|
| Engine | MySQL **8.4.11** (image `mysql:8.4`) |
| Container | `huawei-db` |
| **Nama database** | **`db_huawei`** |
| **User** | **`root`** |
| **Password** | **`b8294f27e063b5662d94567a3a42be66`** |
| Port di dalam network Docker | `3306` |
| Port di host (laptop/server) | **tidak dipublikasikan** — `docker port huawei-db` kosong |
| Network Docker | `backend-measlescare_default` |
| IP container saat ini | `172.19.0.2` |
| Volume data | `backend-measlescare_db_data` -> `/var/lib/mysql` |
| Compose project | `backend-measlescare` |

Password di atas = nilai `DB_ROOT_PW` di file `.env` repo ini (dibaca oleh
`docker-compose.yml` sebagai `MYSQL_ROOT_PASSWORD`). `.env` sudah masuk `.gitignore`.

### Connection string siap pakai

```text
# dari dalam network Docker (dipakai container backend) — gunakan hostname service "db"
mysql+pymysql://root:b8294f27e063b5662d94567a3a42be66@db:3306/db_huawei

# dari container lain di network yang sama
mysql -h db -P 3306 -uroot -pb8294f27e063b5662d94567a3a42be66 db_huawei

# URL versi SQLAlchemy (JDBC-style, untuk tool GUI): host 127.0.0.1 hanya setelah port dibuka (lihat §5)
mysql://root:b8294f27e063b5662d94567a3a42be66@127.0.0.1:3306/db_huawei
```

Catatan: `docker-compose.yml` baris `DATABASE_URL` memakai interpolasi
`mysql+pymysql://root:${DB_ROOT_PW}@db:3306/db_huawei`, jadi container backend mengambil
password dari `.env` yang sama.

---

## 2. Syntax masuk ke database Docker (paling sering dipakai)

Semua perintah dijalankan dari host, di folder repo:

```bash
cd /compe-rams/huawei-inv/backend-measlescare
```

### 2a. Shell MySQL interaktif (baca password dari .env otomatis)

```bash
docker exec -it huawei-db mysql -uroot -p"$(grep '^DB_ROOT_PW=' .env | cut -d= -f2)" db_huawei
```

### 2b. Shell MySQL interaktif (lewat service name compose — lebih ringkas)

```bash
docker compose exec db mysql -uroot -p"$(grep '^DB_ROOT_PW=' .env | cut -d= -f2)" db_huawei
```

### 2c. Manual — password diketik saat diminta (tidak muncul di history shell)

```bash
docker exec -it huawei-db mysql -uroot -p
# lalu saat diminta Enter password: ketik b8294f27e063b5662d94567a3a42be66
# setelah prompt mysql> muncul:
#   USE db_huawei;
```

### 2d. Query langsung tanpa masuk shell (one-liner)

```bash
docker exec huawei-db mysql -uroot -p"$(grep '^DB_ROOT_PW=' .env | cut -d= -f2)" db_huawei -e "SHOW TABLES;"
```

### 2e. Bash shell di dalam container DB (untuk cek file/my.cnf)

```bash
docker exec -it huawei-db bash
# di dalam: mysql -uroot -p db_huawei
```

> Peringatan `mysql: [Warning] Using a password on the command line interface can be insecure`
> itu normal/harmless. Untuk menekan warning, tambahkan `2>/dev/null` di akhir perintah.

---

## 3. Isi database (hasil verifikasi langsung)

```sql
mysql> SHOW DATABASES;
+--------------------+
| Database           |
+--------------------+
| db_huawei          |
| information_schema |
| mysql              |
| performance_schema |
| sys                |
+--------------------+
```

Tabel di `db_huawei` (dibuat otomatis oleh `Base.metadata.create_all()` saat backend start):

| Tabel | Jumlah baris (saat dicek) |
|---|---|
| `Users` | 9 |
| `Gejala` | 17 |
| `Camera` | 17 |
| `Role` | 2 |
| `Status` | 0 |

Struktur `Users`:

| Field | Type | Null | Key |
|---|---|---|---|
| `NIK` | varchar(16) | NO | PRI |
| `Name` | varchar(100) | NO | — |
| `Tgl_lahir` | date | NO | — |
| `Alamat` | text | YES | — |
| `password` | varchar(255) | NO | — (hash argon2) |
| `id_Role` | varchar(10) | NO | MUL -> `Role.id_Role` |

Isi `Role`:

| id_Role | Name |
|---|---|
| R1 | Admin |
| R2 | User |

Akun default aplikasi (seed saat startup): **NIK `admin` / password `admin123`** (role R1).
Ganti segera setelah login pertama. Penambahan user dilakukan lewat API
`POST {BASE}/auth/register`, bukan INSERT manual (password harus di-hash argon2 oleh
`app/core/security.py`).

---

## 4. Koneksi dari aplikasi / tool lain

### Dari container di compose network yang sama (paling aman)

```python
# Python (PyMySQL / SQLAlchemy)
DATABASE_URL = "mysql+pymysql://root:b8294f27e063b5662d94567a3a42be66@db:3306/db_huawei"
```

Hostname = **`db`** (nama service di `docker-compose.yml`), bukan `localhost`.

### Dari container backend yang sedang jalan (tanpa menambah dependency)

```bash
docker compose exec backend python -c "
import os, pymysql
u = os.environ['DATABASE_URL']
print(u)
"
```

### Dari host tanpa SQL client

```bash
docker run --rm -it --network backend-measlescare_default mysql:8.4 \
  mysql -h db -P 3306 -uroot -pb8294f27e063b5662d94567a3a42be66 db_huawei
```

---

## 5. Kalau butuh akses MySQL dari host (DBeaver / TablePlus / MySQL Workbench)

Port 3306 **sengaja tidak dipublish** ke host (lihat `docker-compose.yml`: baris `ports`
pada service `db` sudah dihapus) agar DB tidak terbuka ke internet. Dua pilihan:

Opsi A — SSH/Docker tunnel, DB tetap tidak terekspos:

```bash
# terminal 1: buka listener lokal 3307 -> container huawei-db:3306
docker run --rm -it --network backend-measlescare_default -p 127.0.0.1:3307:3306 \
  alpine/socat tcp-listen:3306,fork,reuseaddr tcp-connect:db:3306
# koneksikan GUI ke 127.0.0.1:3307, user root, password di §1
```

Opsi B — publish sementara via override (JANGAN pakai binding 0.0.0.0 di server publik):

```bash
docker compose -f docker-compose.yml -f - up -d db <<'YML'
services:
  db:
    ports:
      - "127.0.0.1:3306:3306"
YML
```

Hapus lagi setelah selesai: `docker compose up -d db` (tanpa override) lalu
`docker compose rm -sf db` bila perlu.

---

## 6. Backup & restore

```bash
# backup
docker exec huawei-db mysqldump -uroot -p"$(grep '^DB_ROOT_PW=' .env | cut -d= -f2)" \
  --single-transaction --routines --triggers db_huawei > backup_$(date +%F).sql

# restore ke container yang sama
docker exec -i huawei-db mysql -uroot -p"$(grep '^DB_ROOT_PW=' .env | cut -d= -f2)" \
  db_huawei < backup_2026-11-11.sql
```

---

## 7. Troubleshooting cepat

| Gejala | Penyebab / solusi |
|---|---|
| `ERROR 1045 (28000): Access denied for user 'root'@'localhost'` | password salah / ada spasi atau newline ikut terbaca. Pakai pola `$(grep '^DB_ROOT_PW=' .env \| cut -d= -f2)` atau ketik manual (§2c) |
| `ERROR 2002 (HY000): Can't connect to local MySQL server` | container DB belum siap. Cek `docker compose ps` -> harus `Up (healthy)`; `docker compose logs db` |
| `mysql: command not found` (di host) | client MySQL tidak ada di host — pakai `docker exec` (§2) atau `docker run mysql:8.4` (§4) |
| `Can't connect to MySQL server on '127.0.0.1' (111)` | port 3306 memang tidak dipublish ke host — itu by design, lihat §5 |
| `ERROR 1049 (42000): Unknown database 'db_huawei'` | nama DB salah ketik, atau volume DB baru/kosong; tabel dibuat saat backend start |
| Lupa password root | lihat `.env` -> `DB_ROOT_PW`. Kalau `.env` hilang, password tersimpan di volume dan perlu reset manual (`--skip-grant-tables`) |

---

## 8. Catatan keamanan (penting)

- **Password root ada di plaintext di dokumen ini.** Jangan commit/push `integration.md`
  ke repo publik — `.gitignore` saat ini hanya menutup `.env`.
  Kalau dokumen ini akan dibagikan ke tim lewat Git, hapus dulu nilai password di §1
  dan ganti menjadi referensi variabel `.env`.
- Kredensial ini adalah root MySQL. Untuk aplikasi jangka panjang, buat user DB
  terpisah (mis. `measles_app`) dengan grant terbatas ke `db_huawei`, lalu ubah
  `DATABASE_URL` di `.env`/compose agar backend tidak jalan sebagai root.
- Backend publik di `https://ramirosservers.tail2d4b04.ts.net/api` (Tailscale funnel) —
  lihat `hasil_env.md` untuk detail deploy, port, dan routing.
- Segera ganti password akun aplikasi `admin/admin123`.
