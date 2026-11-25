# docs_srv.md — Arsitektur Server MeaslesCare

Dokumen ini menjelaskan arsitektur **backend-measlescare**, **frontend-measlescare**,
cara **Docker** membungkus environment tersebut, dan bagaimana **integrasi MQTT IoT**
(sensor suhu MLX90614 + RFID MFRC522) bekerja. Semua angka dan status di bawah
diambil dari server yang sedang berjalan, bukan dari asumsi file konfigurasi.

| Item | Nilai |
| :--- | :--- |
| Waktu verifikasi | 25 November 2026, 00:28–00:40 UTC |
| Host | `orangepi4pro` — Orange Pi 1.0.8 Jammy, kernel 6.6.98-sun60iw2, aarch64 |
| CPU / RAM | 8 core / 5,7 GiB (tersedia 4,5 GiB) |
| Repo backend | `/home/orangepi/backend-measlescare` (git: `Ramiros-pixel/backend-measlescare`) |
| Repo frontend | `/home/orangepi/frontend-measlescare` (git: `Ramiros-pixel/frontend-measlescare`) |
| Metode | `systemctl`, `ss -ltnp`, `docker ps/info/compose config`, query `information_schema`, `curl`, `mosquitto_pub/sub`, `npm run build` |

> Catatan rahasia: nilai kredensial pada dokumen ini **tidak pernah ditampilkan**.
> Beberapa nilai di repo memang tersimpan sebagai kredensial asli (bukan masker),
> lihat §11.

---

## 1. Ringkasan eksekutif

1. **Docker saat ini membungkus backend, database, dan broker MQTT — tetapi tidak
   frontend.** Frontend tidak punya `Dockerfile` dan tidak punya service di compose;
   ia dibangun Vite lalu disajikan sebagai SPA statis (Vercel/`dist`).
2. **Docker tidak sedang menjalankan apa pun di host ini.** Daemon Docker hidup
   (v29.10.0, Compose v5.8.0) tetapi `docker ps -a`, `docker images`, dan
   `docker compose ls` kosong: 0 container, 0 image, 0 volume. Runtime yang benar-benar
   melayani aplikasi adalah **systemd native** + **MariaDB native** + **Mosquitto native**.
3. **Compose tidak bisa langsung dijalankan di host ini tanpa perbaikan**: `.env` tidak
   ada (password DB kosong), `DATABASE_URL` compose memuat password hardcoded, dan
   service `mosquitto`/`backend` akan bentrok port dengan Mosquitto native (1883) dan
   backend native (8000).
4. **Jalur MQTT sudah terpasang dan broker aktif**, bridge sudah subscribe, tetapi
   **belum ada satu pun pembacaan sensor yang tercatat** (`sensor_readings` = 0).
   Penyebab terukur: publisher tidak berjalan, `/dev/spidev*` tidak ada, dan
   `device_id` publisher (`kiosk-01`) tidak ada di allowlist backend
   (`ESP32_SENSOR_01`).
5. **Data sensor belum mengalir ke alur klinis.** `sensor_readings` adalah tabel
   staging/audit; mesin klinis (`Gejala`, sistem pakar, reconciliation, ONNX) membaca
   `Gejala.Suhu` yang diisi dari UI skrining, bukan dari MQTT. Ini keputusan desain
   Phase 5, bukan bug — tetapi penting dicatat agar tidak salah paham arsitekturnya.

---

## 2. Peta komponen dan tanggung jawab

| Komponen | Lokasi | Tanggung jawab | Status aktual |
| :--- | :--- | :--- | :--- |
| Frontend SPA | `frontend-measlescare/` | UI pasien, kiosk, admin; memanggil REST backend | Build sukses (`dist/`), tidak disajikan host ini |
| Backend FastAPI | `backend-measlescare/app/` | Auth JWT, kiosk session, gejala, wajah, sistem pakar, ONNX, reconciliation, ingest sensor | Aktif, PID 1444, `127.0.0.1:8000` |
| MQTT bridge | `integrasi_sensor/bridge/mqtt_bridge.py` | Normalisasi payload MQTT → `POST /api/kiosk-session/reading` | Aktif, PID 1445, subscribed |
| Sensor publisher | `integrasi_sensor/firmware/sensor_publisher.py` | Baca RFID + suhu, publish QoS 1 | **Tidak berjalan** |
| Broker Mosquitto | native `mosquitto.service` | Transport MQTT | Aktif, `0.0.0.0:1883`, v2.0.11 |
| Database | native MariaDB 10.6.23 | Simpan seluruh data | Aktif, `127.0.0.1:3306`, `db_huawei` |
| Docker | `docker.service` | (disiapkan untuk stack compose) | Aktif, tanpa container |

---

## 3. Runtime aktual (terukur)

### 3.1 Layanan dan port

| Layanan | Manajer | PID | Sejak | Listen | Versi |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `measlescare-backend.service` | systemd (enabled) | 1444 | 20 Nov 13:17 UTC | `127.0.0.1:8000` | FastAPI 0.143.5 / Python 3.10.12 |
| `measlescare-bridge.service` | systemd (enabled) | 1445 | 20 Nov 13:17 UTC | (client keluar) | paho-mqtt |
| `mosquitto.service` | systemd (enabled) | 1089 | 20 Nov 13:17 UTC | `0.0.0.0:1883` | Mosquitto 2.0.11 |
| `mariadb.service` | systemd (enabled) | — | — | `127.0.0.1:3306` | MariaDB 10.6.23 |
| `docker.service` | systemd (enabled) | — | — | socket | Docker 29.10.0 |

Catatan penting: dokumentasi lama menyebut `MySQL 8.4` di container. Server **aktual**
memakai **MariaDB 10.6.23** native (`SELECT VERSION()`), bukan MySQL 8.4.

Health check yang benar-benar dijalankan:

```
GET /                        -> 200 {"status":"ok","app":"Huawei ICT Backend"}
GET /docs                    -> 200
GET /openapi.json            -> 200
GET /api/docs                -> 404   (Swagger ada di /docs, bukan /api/docs)
GET /api/openapi.json        -> 404
```

`app_name` masih `Huawei ICT Backend` (warisan nama proyek) walau folder sudah
`measlescare`.

### 3.2 Diagram topologi aktual

```
                 ORANGE PI 4 PRO · aarch64 · 8 core · 5,7 GiB

  [ Browser / Kiosk UI ]
        │  HTTPS · SPA statis (Vercel / dist), di luar host ini
        │  fetch {VITE_API_BASE_URL}/api/...
        ▼
  ┌────────────────────────────┐   127.0.0.1:8000   ┌──────────────────────┐
  │ measlescare-backend.svc    │◄───────────────────│ health check lokal   │
  │ uvicorn app.main:app       │                    └──────────────────────┘
  │ PID 1444 · ~148 MB         │
  └──────────────┬─────────────┘
                 │ SQLAlchemy + PyMySQL
                 ▼
  ┌────────────────────────────┐
  │ MariaDB 10.6.23 native     │   db_huawei · 15 tabel
  │ 127.0.0.1:3306 (loopback)  │
  └────────────────────────────┘

  ┌────────────────────────────┐  1883/TCP  ┌────────────────────────┐
  │ Mosquitto 2.0.11 native    │◄───────────│ sensor_publisher (OFF) │
  │ 0.0.0.0:1883 (anonim)      │            │ hardware I2C/SPI absen │
  └──────────────┬─────────────┘            └────────────────────────┘
                 │ measlescare/+/reading (QoS 1)
                 ▼
  ┌────────────────────────────┐
  │ measlescare-bridge.svc     │  POST /api/kiosk-session/reading
  │ PID 1445 (adapter tipis)   │  header X-Kiosk-Key
  └────────────────────────────┘

  ┌────────────────────────────┐
  │ docker.service v29.10.0    │  0 container · 0 image · 0 volume
  │ tidak memuat compose       │  runtime aplikasi = systemd native
  └────────────────────────────┘
```

---

## 4. Arsitektur backend

### 4.1 Lapisan aplikasi

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Entry & lifecycle                                                           │
│   main.py  (systemd)  ->  uvicorn.run("app.main:app", 127.0.0.1:8000,       │
│                                        reload dari UVICORN_RELOAD)          │
│   Docker CMD      ->  uvicorn app.main:app --host 0.0.0.0 --port 8000       │
│   startup: Base.metadata.create_all -> migrate_database() -> seed Role,     │
│            admin default (admin/admin123), master gejala, aturan pakar      │
├─────────────────────────────────────────────────────────────────────────────┤
│ Router / HTTP (prefix global = settings.API_PREFIX, native "/api")          │
│   /auth  /users  /gejala(+camera)  /face  /kiosk  /kiosk-session            │
│   /pakar  /v1/measles  /reconciliation                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│ Service domain                                                              │
│   face_engine (OpenCV LBPH)   measles_engine (ONNX Runtime)                 │
│   expert_system (decision tree + inference)                                 │
│   reconciliation_service (safety gate)   sensor_service (ingest MQTT)       │
│   core/security (JWT, bcrypt)  core/rate_limit (sliding window in-memory)   │
├─────────────────────────────────────────────────────────────────────────────┤
│ Model & persistence                                                         │
│   SQLAlchemy 2.0 ORM + PyMySQL  ->  MariaDB db_huawei (15 tabel)            │
│   process-recognation/ (dataset wajah + face_model.yml + labels.json)       │
│   app/models/weights/mobilenetv3_measleswatch.onnx (5.9 MB)                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Inventaris router (OpenAPI aktual: 36 path, 37 operasi)

| Prefix | File | Fungsi |
| :--- | :--- | :--- |
| `/api/auth` | `auth.py` | register, login, me (JWT) |
| `/api/users` | `users.py` | list/detail user, aturan role R1/R2 |
| `/api/gejala`, `/api/camera` | `gejala.py` | pencatatan gejala + hasil kamera (tanpa prefix lokal) |
| `/api/face` | `face.py` | enroll/train/recognize/reset model LBPH |
| `/api/kiosk` | `kiosk.py` | identifikasi RFID/wajah, email, capture |
| `/api/kiosk-session` | `kiosk_session.py` | sesi kiosk + ingest sensor (`/reading`) |
| `/api/pakar` | `pakar.py` | evaluasi sistem pakar, master gejala |
| `/api/v1/measles` | `measles.py` | inferensi ONNX MeaslesWatch |
| `/api/reconciliation` | `reconciliation.py` | rekonsiliasi bukti klinis |

### 4.3 Model data (hitungan `COUNT(*)` aktual)

| Tabel | Baris | Peran |
| :--- | ---: | :--- |
| `Users` | 4 | pasien + admin (`NIK` varchar(16) PK) |
| `Role` | 2 | R1 Admin, R2 User |
| `Gejala` | 4 | pemeriksaan: `Suhu`, `Batuk`, `Tanggal` |
| `Camera` | 3 | hasil deteksi kamera |
| `Status` | 2 | master status |
| `patient_cards` | 3 | `rfid_uid` UNIQUE → `Users.NIK` |
| `kioskdevices` | 1 | perangkat kiosk (`secret_hash` bcrypt, `aktif`) |
| `kiosksessions` | 0 | sesi aktif/kadaluarsa (`token_hash` sha256, `expires_at`, `revoked`) |
| `master_gejala` | 12 | basis pengetahuan gejala |
| `aturan_pakar` | 7 | aturan pakar |
| `aturan_pakar_detail` | 15 | detail aturan |
| `hasil_pakar` | 3 | hasil evaluasi pakar |
| `jawaban_gejala` | 7 | jawaban gejala per pemeriksaan |
| `sensor_readings` | **0** | staging/audit telemetri MQTT (belum ada data) |
| `evidence_reconciliations` | 0 | hasil rekonsiliasi |

Skema dibuat otomatis saat startup (`create_all` + migrasi aditif). Tidak ada tabel
sensor yang menulis langsung ke `Gejala`.

### 4.4 Keamanan dan identitas

- **JWT** HS256, expiry 120 menit (`ACCESS_TOKEN_EXPIRE_MINUTES`), `SECRET_KEY`
  default masih `change-me` bila env tidak diisi.
- **Perangkat kiosk**: header `X-Kiosk-Key`, diverifikasi bcrypt terhadap
  `kioskdevices.secret_hash`; hanya device `aktif=1`.
- **Sesi kiosk**: token `id_session|NIK|secret`, disimpan sebagai SHA-256 di
  `kiosksessions.token_hash`, umur 20 menit, wajib perangkat yang sama
  (session-device binding → 403 bila beda device).
- **Rate limit**: sliding window in-memory per IP (`X-Forwarded-For` dipakai bila ada),
  60 req/menit untuk RFID, 30 req/menit untuk create session, 120 req/menit untuk
  ingest `/kiosk-session/reading`; 429 + `Retry-After`.
- **CORS**: `allow_origins=["*"]` — longgar, cocok untuk demo, perlu dipersempit untuk
  produksi.
- **Identitas pasien**: selalu dari sesi aktif / NIK pada token, **tidak pernah** dari
  `rfid_uid`. RFID hanya cross-check.

### 4.5 Model ML

| Model | Path | Catatan |
| :--- | :--- | :--- |
| Wajah LBPH | `process-recognation/trainer/face_model.yml` + `labels.json` | dataset per-NIK `process-recognation/dataset/<NIK>/*.jpg`; total folder 17 MB; di-bind-mount di compose |
| MeaslesWatch ONNX | `app/models/weights/mobilenetv3_measleswatch.onnx` | 5,9 MB, ikut ke dalam image karena `COPY . .` |

---

## 5. Arsitektur frontend

### 5.1 Stack dan hasil build (terukur)

| Item | Nilai |
| :--- | :--- |
| Framework | React 19 + TypeScript 6 + Vite 8.3.4 |
| Styling | Tailwind CSS 4 (plugin Vite) |
| Routing | React Router 7 (`BrowserRouter` + `Routes`) |
| Data | TanStack Query 5 |
| 3D | three.js + `@react-three/fiber` + `drei` (`KioskScene`, GLB `screening-kiosk.glb`) |
| Build | `npm run build` sukses: 679 modul, **2,44 s** |
| Output | `dist/index.html` 0,96 kB · CSS 83,93 kB (gzip 15,85 kB) · JS **1.739,26 kB** (gzip 459,18 kB) |
| Peringatan | chunk > 500 kB (belum code-splitting) |
| Container | **tidak ada Dockerfile / service compose** |
| Deploy | `vercel.json`: framework vite, output `dist`, rewrite SPA `/(.*) → /index.html` |

### 5.2 Rute UI

```
/                         -> redirect /user
/login  /register
/user                     -> UserPublicLayout
  /fungsi-alat  /cara-penggunaan
  /user/skrining/identifikasi   (kiosk: RFID / wajah / NIK)
  /user/skrining/pemeriksaan    (SkriningPage: foto -> suhu -> gejala -> hasil)
/user (terproteksi)       -> beranda / periksa / hasil/:id / riwayat / profil
/admin (R1)               -> dashboard / pasien / skrining / laporan / pengguna
                             / pengguna/:nik / pemeriksaan / pemeriksaan/:id
*                         -> NotFoundPage
```

### 5.3 Cara frontend menemukan backend (penting untuk Docker)

| Mode | `VITE_API_BASE_URL` | `API_BASE` efektif | Jalur |
| :--- | :--- | :--- | :--- |
| Dev (`npm run dev`) | kosong | `/be-api` | Vite proxy `/be-api/*` → `http://127.0.0.1:8000`, rewrite ke `/api/*` |
| Build produksi | `https://host` | `https://host/api` (auto ditambah) | langsung ke backend |
| Build produksi | `https://host/api` | tetap | langsung ke backend |
| Build produksi | kosong | `/be-api` | **butuh reverse proxy same-origin**; di Vercel tanpa rewrite akan 404 |

File `.env` frontend saat ini berisi `VITE_API_BASE_URL=` (kosong) dan
`VITE_KIOSK_API_KEY` (21 karakter). Artinya build produksi dari repo ini akan
memanggil `/be-api` pada origin sendiri — perlu diisi sebelum deploy, atau
disediakan reverse proxy.

### 5.4 Alur kiosk di UI

```
IdentifikasiPage
  RFID        -> POST /kiosk/identify-rfid
  Wajah       -> POST /kiosk-session/identify-face
  NIK + foto  -> POST /kiosk-session/create   (X-Kiosk-Key)
                        |
                        v  access_token sesi (20 menit)
SkriningPage
  foto + suhu (input UI) + gejala
     -> POST /kiosk-session/gejala            (X-Kiosk-Key + X-Kiosk-Session)
     -> POST /v1/measles/predict              (inferensi ONNX)
     -> POST /pakar/evaluasi                  (sistem pakar)
     -> POST /reconciliation/evaluate         (safety gate)
                        |
                        v
ResultPage  (tampilan hasil + disclaimer medis)
```

Suhu pada alur ini **diketik/diukur manual di UI**. Belum ada komponen frontend yang
membaca `sensor_readings` atau berlangganan MQTT langsung.

---

## 6. Bagaimana Docker membungkus environment

### 6.1 Cakupan pembungkusan

| Environment | Dibungkus Docker? | Bukti |
| :--- | :--- | :--- |
| Backend FastAPI | **Ya** | `Dockerfile` + service `backend` (build `.`) |
| Database | **Ya** | service `db`, image `mysql:8.4`, volume `db_data` |
| Broker MQTT | **Ya** | service `mosquitto`, image `eclipse-mosquitto:2` |
| Frontend SPA | **Tidak** | tidak ada `Dockerfile`/compose service; deploy statis (Vercel/`dist`) |
| Publisher sensor | **Tidak** | butuh akses GPIO/I2C/SPI host, dijalankan native |
| Bridge MQTT | **Tidak** | dijalankan native (systemd), bukan service compose |

### 6.2 Dockerfile (backend)

| Baris | Isi | Konsekuensi |
| :--- | :--- | :--- |
| `FROM python:3.11-slim` | base | **berbeda** dari venv native (Python 3.10.12); perlu diuji ulang sebelum produksi |
| `ENV PYTHONDONTWRITEBYTECODE, PYTHONUNBUFFERED, PIP_NO_CACHE_DIR` | runtime | log langsung ke stdout container |
| `apt-get install libgl1 libglib2.0-0` | dependency OpenCV headless | wajib untuk decode JPEG/PNG |
| `COPY requirements.txt` → `pip install` | layer cache | rebuild cepat bila kode berubah |
| `COPY . .` | seluruh repo | **termasuk** `app/models/weights/*.onnx`, `process-recognation/`, `mosquitto/`, `deploy/` |
| `EXPOSE 8000` + `CMD uvicorn app.main:app --host 0.0.0.0 --port 8000` | entry | berbeda dari native (`python main.py`, bind 127.0.0.1) |

`.dockerignore` mengecualikan `.venv/`, `__pycache__`, `.env*` (kecuali
`.env.example`), `.git/`, `*.md`, `postman_collection.json`. Jadi image **tidak**
membawa `.env` maupun dokumen; konfigurasi wajib lewat environment compose.

### 6.3 docker-compose.yml (3 service)

| Service | Image / build | Port host | Volume | Mem limit | Healthcheck | Depends on |
| :--- | :--- | :--- | :--- | ---: | :--- | :--- |
| `db` (`huawei-db`) | `mysql:8.4` | **tidak dipublish** | `db_data:/var/lib/mysql` | 512 MB | `mysqladmin ping` 5s ×20 | — |
| `backend` (`huawei-backend`) | build `.` | `127.0.0.1:8000` | bind `./process-recognation:/app/process-recognation` | 512 MB | — | `db: service_healthy` |
| `mosquitto` (`huawei-mosquitto`) | `eclipse-mosquitto:2` | `1883:1883` | `./mosquitto/config:ro`, `mosquitto_data`, `mosquitto_log` | 128 MB | `mosquitto_sub $SYS/broker/uptime` | — |

Environment yang di-inject ke `backend`:

| Variabel | Nilai di compose | Catatan |
| :--- | :--- | :--- |
| `DATABASE_URL` | `mysql+pymysql://root:<password>@db:3306/db_huawei` | password **hardcoded** di file (13 karakter, tidak ditampilkan); host `db` = nama service |
| `SECRET_KEY` | `${SECRET_KEY}` | dari `.env` (tidak ada di repo) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `${ACCESS_TOKEN_EXPIRE_MINUTES}` | dari `.env` |
| `API_PREFIX` | `""` | **khusus Docker**: route tidak ber-prefix karena Tailscale funnel me-mount `/api` lalu melepas prefix |

Tuning hemat RAM di `db`: `--innodb-buffer-pool-size=128MB`,
`--performance-schema=OFF`.

### 6.4 Graf dependensi compose

```
docker compose up -d
├── db          image mysql:8.4        :3306 internal · volume db_data
├── backend     build Dockerfile       :8000 → 127.0.0.1 · bind process-recognation
└── mosquitto   image eclipse-mosquitto:2   :1883 → host · volume data/log

backend  depends_on  db (condition: service_healthy)
ketiganya berbagi network  backend-measlescare_default
publish ke host: 127.0.0.1:8000 (backend) dan 1883 (mosquitto)
opsional: tailscale funnel --bg --set-path=/api http://127.0.0.1:8000
```

### 6.5 Status Docker aktual (terukur)

```
docker ps -a            -> kosong (0 container)
docker images           -> kosong (0 image)
docker compose ls       -> kosong (tidak ada project)
docker volume ls        -> hanya volume bawaan (tidak ada db_data/mosquitto_*)
docker network ls       -> bridge/host/none saja (tidak ada backend-measlescare_default)
docker info             -> 29.10.0, overlayfs, cgroup v2/systemd, 8 CPU, 5.716 GiB
```

`docker compose config` berhasil mem-parse file tetapi menghasilkan peringatan:

```
WARN "DB_ROOT_PW" variable is not set. Defaulting to a blank string.
WARN "SECRET_KEY" variable is not set. Defaulting to a blank string.
WARN "ACCESS_TOKEN_EXPIRE_MINUTES" variable is not set. Defaulting to a blank string.
```

### 6.6 Blocker bila compose dijalankan di host ini

| # | Blocker | Bukti | Dampak |
| ---: | :--- | :--- | :--- |
| 1 | `.env` tidak ada | `ls .env` → tidak ditemukan | `MYSQL_ROOT_PASSWORD` kosong → container `mysql:8.4` gagal inisialisasi |
| 2 | Password DB di `DATABASE_URL` hardcoded | 13 karakter, berbeda dari `${DB_ROOT_PW}` yang tidak diketahui | backend container berisiko gagal auth ke `db` |
| 3 | Port 1883 sudah dipakai Mosquitto native | `ss`: `0.0.0.0:1883` | service `mosquitto` gagal bind |
| 4 | Port 8000 sudah dipakai backend native | `ss`: `127.0.0.1:8000` | service `backend` gagal bind |
| 5 | Data DB terpisah | volume `db_data` baru vs MariaDB native berisi 15 tabel | aplikasi Docker akan tampak "kosong" |
| 6 | Image belum ada | `docker images` kosong | `up` butuh pull `mysql:8.4` + `eclipse-mosquitto:2` + build |
| 7 | Frontend tidak termasuk | tidak ada Dockerfile | UI tetap harus di-deploy terpisah |

Jadi, secara desain **Docker membungkus backend + DB + broker**, tetapi secara
operasional **Docker belum menjadi runtime aplikasi ini**.

---

## 7. Arsitektur integrasi MQTT IoT

### 7.1 Perangkat dan wiring

Target hardware: Orange Pi 4 Pro (bukan ESP32), dua sensor di header 40-pin.

| Sensor | Bus | Pin (BOARD) | Alamat / sinyal |
| :--- | :--- | :--- | :--- |
| MLX90614 (GY-906/HW-691) | I2C | VIN 3.3V (1/17), GND (6/9), SCL 5, SDA 3 | `0x5A`, PEC verified |
| MFRC522 Mini | SPI | SDA/SS 24 (CE0), SCK 23, MOSI 19, MISO 21, RST 22, 3.3V, GND | 13,56 MHz |
| RST GPIO | gpiod | pin 22 = PD23 = line 119 `gpiochip0` | reset via `/dev/gpiochip0` |

### 7.2 Rantai perangkat lunak

```
 ┌──────────────────────────── integrasi_sensor/ ────────────────────────────┐
 │                                                                           │
 │  firmware/mlx90614.py   (I2C, median N sampel, verifikasi PEC)            │
 │  firmware/mfrc522.py    (SPI + gpiod reset, UID -> hex uppercase)         │
 │  firmware/sensor_publisher.py                                             │
 │        loop: tunggu kartu -> baca suhu -> publish QoS 1                   │
 │        topik: measlescare/<DEVICE_ID>/reading                             │
 │        payload: device_id, rfid_uid, suhu, sensor, ts                     │
 │                     │                                                     │
 │                     ▼  MQTT 1883                                          │
 │  Mosquitto (native 2.0.11, allow_anonymous true)                          │
 │                     │                                                     │
 │                     ▼  subscribe measlescare/+/reading (QoS 1)            │
 │  bridge/mqtt_bridge.py                                                    │
 │        normalize_payload(): object_temp (fallback suhu), event_id         │
 │        (sha256 payload bila kosong), ambient_temp, uptime_ms,             │
 │        source_format = python_publisher | esp32, raw_payload              │
 │        worker thread + retry backoff 1s→2s→4s (maks 4 percobaan)          │
 │                     │                                                     │
 │                     ▼  HTTP POST (loopback)                               │
 │  backend  /api/kiosk-session/reading   header X-Kiosk-Key                 │
 │        _device_from_key -> bcrypt compare kioskdevices.secret_hash        │
 │        ingest_sensor_reading (validator otoritatif)                       │
 │                     │                                                     │
 │                     ▼                                                     │
 │  MariaDB  sensor_readings (event_id UNIQUE = idempotency key)             │
 └───────────────────────────────────────────────────────────────────────────┘
```

### 7.3 Sequence diagram

```
Publisher                (1) kartu RFID terbaca + suhu objek (median 5 sampel)
    |
    |  MQTT publish QoS 1   topik: measlescare/<DEVICE_ID>/reading
    v
Mosquitto (broker)       (2) terima pesan, teruskan ke subscriber
    |
    |  deliver QoS 1       topik cocok: measlescare/+/reading
    v
Bridge (adapter tipis)   (3) parse JSON + normalisasi payload kanonik
    |                        (object_temp, event_id, raw_payload)
    |  HTTP POST /api/kiosk-session/reading   header X-Kiosk-Key
    v
Backend (validator)      (4) auth device -> allowlist -> rentang suhu
    |                        -> sesi aktif -> cross-check RFID -> INSERT
    |  respons: ACCEPTED | REJECTED_* | duplicate
    v
MariaDB                  (5) tabel sensor_readings (audit + staging)
```

### 7.4 Kontrak topik dan payload

| Topik | Arah | QoS | Payload |
| :--- | :--- | ---: | :--- |
| `measlescare/<DEVICE_ID>/reading` | publisher → broker | 1 | JSON pembacaan |
| `measlescare/+/reading` | bridge subscribe | 1 | pola wildcard |

Payload publisher aktual (belum kanonik):

```json
{
  "device_id": "kiosk-01",
  "rfid_uid": "E0040100ABCDEF0001",
  "suhu": 36.7,
  "sensor": "mlx90614",
  "ts": "2026-11-18T15:04:05+00:00"
}
```

Payload kanonik yang dikirim bridge ke backend:

```json
{
  "event_id": "<uuid atau sha256(payload) 64 hex>",
  "device_id": "kiosk-01",
  "rfid_uid": "E0040100ABCDEF0001",
  "object_temp": 36.7,
  "ambient_temp": null,
  "uptime_ms": null,
  "source_format": "python_publisher",
  "raw_payload": "{\"device_id\":...}"
}
```

### 7.5 Tangga validasi backend (urutan pasti)

```
POST /api/kiosk-session/reading
   │
   ├─ 1. X-Kiosk-Key cocok dengan kioskdevices.secret_hash?  ─ tidak → 401
   ├─ 2. event_id sudah ada?                                ─ ya    → duplicate
   ├─ 3. device_id ∈ ALLOWED_DEVICES?                       ─ tidak → REJECTED_DEVICE
   ├─ 4. object_temp ada?                                   ─ tidak → REJECTED_PAYLOAD/MISSING
   ├─ 5. 30 ≤ object_temp ≤ 45?                             ─ tidak → REJECTED_RANGE
   ├─ 6. sesi aktif per id_device (revoked=0, belum expired)
   │        >1 sesi                                          ─ ya    → REJECTED_MULTI_SESSION
   ├─ 7. rfid_uid valid & terdaftar & cocok dengan NIK sesi  ─ tidak → REJECTED_UID
   ├─ 8. ada sesi aktif?                                    ─ tidak → REJECTED_NO_SESSION
   └─ 9. ACCEPTED (id_session + NIK diisi dari sesi)
```

Semua keputusan — termasuk penolakan — **tetap disimpan** sebagai baris
`sensor_readings` beserta `status`, `validation_status`, `reason`, dan
`raw_payload`. Nilai suhu di luar rentang disimpan apa adanya, tidak di-clamp.

### 7.6 Konfigurasi dan drift yang terukur

| Variabel | Nilai efektif sekarang | Dipakai | Catatan |
| :--- | :--- | :--- | :--- |
| `MQTT_HOST` / `MQTT_PORT` | `127.0.0.1` / `1883` | publisher + bridge | dari `integrasi_sensor/config.env` |
| `MQTT_SUBSCRIBE_TOPIC` | `measlescare/+/reading` | bridge | — |
| `BACKEND_URL` | `http://127.0.0.1:8000` | bridge | loopback |
| `KIOSK_API_KEY` | terisi (tidak ditampilkan) | bridge | harus sama dengan secret device demo |
| `DEVICE_ID` | **default `kiosk-01`** | publisher | tidak di-set di `config.env` |
| `MQTT_ALLOWED_DEVICES` | **default `ESP32_SENSOR_01`** | backend | **tidak cocok** dengan `kiosk-01` |
| `SUHU_MIN` / `SUHU_MAX` | 30 / 45 | backend | `config.example.env` masih menulis 25/45 |
| `I2C_BUS` | default `1` | publisher | host tidak punya `/dev/i2c-1` |
| `SPI_BUS/DEVICE` | default `0`/`0` | publisher | host tidak punya `/dev/spidev*` |

Drift dokumentasi: `integrasi_sensor/README.md` dan `Documentation.md` masih
menggambarkan bridge versi lama (menulis langsung ke `Gejala`, auto-registrasi kartu,
`RFID_AUTO_REGISTER`, validasi 25–45). Kode Phase 5 **tidak** melakukan itu: bridge
adapter tipis, tanpa tulis DB, tanpa auto-registrasi, validasi 30–45 di backend.

### 7.7 Status integrasi MQTT aktual

| Pemeriksaan | Hasil |
| :--- | :--- |
| `mosquitto.service` | aktif, `0.0.0.0:1883`, v2.0.11, config `/etc/mosquitto/conf.d/measlescare.conf` (`allow_anonymous true`) |
| Uji publish/subscribe loopback | **berhasil** (`measlescare/healthcheck/ping`, retained lalu dibersihkan) |
| Bridge | aktif PID 1445, log `subscribed: measlescare/+/reading` |
| Publisher | **tidak berjalan** (tidak ada proses `sensor_publisher`) |
| Device node | `/dev/spidev*` **tidak ada**; tidak ada `/dev/i2c-1`; `/dev/gpiochip0-1` ada |
| `sensor_readings` | **0 baris** — belum pernah ada pembacaan yang diterima |
| `kiosksessions` | **0 baris** — tidak ada sesi aktif, sehingga ingest akan `REJECTED_NO_SESSION` |
| `kioskdevices` | 1 perangkat aktif (`c0ffee00-...-000000000001`) |

Kesimpulan: rantai **transport** sehat (broker + bridge), tetapi rantai **data**
belum pernah tuntas. Untuk pembacaan pertama yang `ACCEPTED` diperlukan tiga hal:
publisher berjalan dengan device node yang benar, `device_id` masuk allowlist, dan
ada sesi kiosk aktif.

---

## 8. Diagram alur ringkas

### 8.1 Alur request frontend → backend (dev)

```
Browser (5173)
   │ GET /be-api/gejala/history
   ▼
Vite dev server  ──rewrite /be-api -> /api──►  FastAPI 127.0.0.1:8000
                                                   │
                                                   ├─ JWT bearer verify
                                                   ├─ role check (R1/R2)
                                                   └─ SQLAlchemy → MariaDB
```

### 8.2 Alur request produksi (Docker + funnel)

```
Browser  ──https://host/api/...──►  Tailscale funnel (strip /api)
                                          │
                                          ▼
                              backend container :8000 (API_PREFIX="")
                                          │
                                          ▼
                              db container mysql:8.4 (network internal)
```

### 8.3 Alur Docker vs native (fork runtime)

```
              SATU HOST — DUA RUNTIME YANG SALING BEREBUT PORT
┌───────────────────────────────┬───────────────────────────────┐
│ AKTUAL (systemd native)       │ COMPOSE (belum dijalankan)    │
├───────────────────────────────┼───────────────────────────────┤
│ backend   127.0.0.1:8000      │ backend   127.0.0.1:8000      │
│ bridge    systemd (PID 1445)  │ db        internal :3306      │
│ mosquitto 0.0.0.0:1883        │ mosquitto 0.0.0.0:1883        │
│ MariaDB   127.0.0.1:3306      │ data      volume db_data baru │
│ data      15 tabel nyata      │ frontend  tidak termasuk      │
└───────────────────────────────┴───────────────────────────────┘
  konflik: port 8000 (backend) dan 1883 (broker) diperebutkan keduanya
```

---

## 9. Operasional

### 9.1 Perintah runtime aktual (native)

```bash
# status
systemctl status measlescare-backend measlescare-bridge mosquitto mariadb
ss -ltnp | grep -E ':(8000|1883|3306)'

# log
journalctl -u measlescare-backend -f
journalctl -u measlescare-bridge -f

# health
curl -s http://127.0.0.1:8000/
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8000/docs

# publisher (butuh hardware siap)
cd /home/orangepi/backend-measlescare
./venv/bin/python -m integrasi_sensor.firmware.sensor_publisher --verbose

# uji broker tanpa hardware (topik di luar pola bridge, tidak menulis DB)
mosquitto_pub -h 127.0.0.1 -t 'measlescare/healthcheck/ping' -m '{"ok":true}'
mosquitto_sub -h 127.0.0.1 -t 'measlescare/#' -v
```

### 9.2 Perintah bila memakai Docker

```bash
cd /home/orangepi/backend-measlescare
cp .env.example .env          # isi DB_ROOT_PW, SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES
docker compose config         # validasi tanpa menjalankan
docker compose build backend
docker compose up -d db mosquitto
docker compose ps             # db harus Up (healthy)
docker compose up -d backend
docker compose logs -f backend
docker compose down           # volume tetap
```

Sebelum itu, hentikan dulu stack native yang memakai port sama (backend 8000,
mosquitto 1883) dan pastikan `DATABASE_URL` memakai `${DB_ROOT_PW}` yang sama
dengan `MYSQL_ROOT_PASSWORD`.

### 9.3 Backup

```bash
# native
mysqldump --single-transaction db_huawei > backup_$(date +%F).sql
# docker
docker exec huawei-db sh -c 'mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" --single-transaction db_huawei' > backup_$(date +%F).sql
```

---

## 10. Temuan dan rekomendasi

| Prioritas | Temuan | Rekomendasi |
| :--- | :--- | :--- |
| P0 | Docker tidak memuat stack apa pun, padahal dokumen lama menyatakan "berhasil deploy" | Tegaskan satu runtime sebagai sumber kebenaran; perbarui `hasil_env.md`/`integration.md` agar tidak menyesatkan |
| P0 | Kredensial DB asli tersimpan di `docker-compose.yml` dan `app/core/config.py` (repo publik) | Rotasi password, pindahkan ke `.env`/secret, hapus dari git history |
| P0 | `mqtt_bridge.py` menerima `KIOSK_API_KEY` dari file yang tidak di-commit; kalau hilang, bridge gagal start | Dokumentasikan provisioning key; tambahkan pengecekan saat deploy |
| P1 | `DEVICE_ID=kiosk-01` vs `ALLOWED_DEVICES=ESP32_SENSOR_01` | Set `MQTT_ALLOWED_DEVICES` eksplisit atau samakan default |
| P1 | Publisher belum berjalan; `/dev/spidev*` dan `/dev/i2c-1` tidak ada | Aktifkan SPI/I2C di Armbian, verifikasi `i2cdetect` 0x5A, buat unit systemd publisher |
| P1 | `sensor_readings` tidak pernah terisi; tidak ada sesi aktif | Uji E2E setelah publisher + sesi siap; pastikan status `ACCEPTED` tercatat |
| P1 | Frontend build produksi dengan `VITE_API_BASE_URL` kosong | Isi env di Vercel (atau sediakan rewrite `/be-api`) |
| P2 | `README`/`Documentation.md` MQTT masih menjelaskan perilaku lama (tulis `Gejala`, auto-register, 25–45 °C) | Sinkronkan dengan kode Phase 5 |
| P2 | Bundle JS 1,74 MB | Code-splitting (dynamic import halaman admin/3D) |
| P2 | Broker `allow_anonymous true` di `0.0.0.0` untuk data kesehatan | Aktifkan `password_file` + TLS, batasi listener |
| P2 | `SECRET_KEY=change-me`, CORS `*`, admin default `admin123` | Ganti sebelum produksi |

---

## 11. Lampiran: bukti dan berkas kunci

### 11.1 Perintah verifikasi yang dijalankan

| Perintah | Ringkasan hasil |
| :--- | :--- |
| `systemctl is-active docker measlescare-backend measlescare-bridge mosquitto mariadb` | semuanya `active` |
| `ss -ltnp` | `127.0.0.1:8000`, `127.0.0.1:3306`, `0.0.0.0:1883` |
| `docker ps -a` / `docker images` / `docker compose ls` | kosong |
| `docker compose config` | parse sukses, 3 service, 4 warning (3 variabel env kosong) |
| `SELECT VERSION()` | `10.6.23-MariaDB-0ubuntu0.22.04.1` |
| `COUNT(*)` 15 tabel | lihat §4.3 (`sensor_readings` = 0, `kiosksessions` = 0) |
| `curl /`, `/docs`, `/openapi.json` | 200; 37 operasi / 36 path |
| `mosquitto_pub` + `mosquitto_sub` retained | pesan diterima, broker sehat |
| `npm run build` | sukses, 2,44 s, `dist/` terbentuk |
| `ls /dev/spidev*`, `ls /dev/i2c-*` | tidak ada SPI; tidak ada bus 1 |

### 11.2 Berkas kunci

```
backend-measlescare/
├── main.py                     # launcher systemd (bind 127.0.0.1, reload via env)
├── Dockerfile                  # image backend (python:3.11-slim, uvicorn 0.0.0.0:8000)
├── docker-compose.yml          # db (mysql:8.4) + backend + mosquitto
├── .dockerignore               # mengecualikan .env, venv, md
├── app/
│   ├── main.py                 # FastAPI + startup create_all/migrate/seed
│   ├── core/{config,security,rate_limit,constants}.py
│   ├── routers/{auth,users,gejala,face,kiosk,kiosk_session,pakar,measles,reconciliation}.py
│   ├── services/{face_engine,measles_engine,reconciliation_service,sensor_service}.py
│   ├── models/{gejala,kiosk_session,pakar,reconciliation,sensor}.py
│   └── models/weights/mobilenetv3_measleswatch.onnx
├── integrasi_sensor/
│   ├── firmware/{mlx90614,mfrc522,sensor_publisher}.py
│   ├── bridge/mqtt_bridge.py
│   └── config.env              # kredensial bridge (tidak di-commit)
├── mosquitto/config/mosquitto.conf
├── deploy/{measlescare-backend.service,measlescare-bridge.service}
└── docs_srv.md                 # dokumen ini

frontend-measlescare/
├── vite.config.ts              # proxy /be-api -> 127.0.0.1:8000 (/api)
├── vercel.json                 # SPA rewrite, output dist
├── src/api/{client,endpoints,types}.ts
├── src/pages/...               # user, admin, skrining, identifikasi
└── .env                        # VITE_API_BASE_URL (kosong), VITE_KIOSK_API_KEY
```

### 11.3 Catatan tentang kredensial di repo

`docker-compose.yml` memuat password DB asli (13 karakter) dan
`app/core/config.py` memuat password default (8 karakter) yang benar-benar dipakai
koneksi native. Nilainya tidak dicetak di dokumen ini. Keduanya harus dianggap
bocor karena repo di-push ke GitHub publik, dan sebaiknya dirotasi sebelum
deployment berikutnya.
