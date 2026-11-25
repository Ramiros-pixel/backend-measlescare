# PHASE 5 IMPLEMENTATION PLAN — MQTT Bridge & FastAPI Backend Integration

**Proyek:** MeaslesCare
**Platform:** Orange Pi 4 Pro (Ubuntu, kernel 6.6.98-sun60iw2)
**Repo:** `/home/orangepi/backend-measlescare` (HEAD `5eaaec7`)
**Tanggal perencanaan:** 20 November 2026
**Mode:** PERENCANAAN & INSPEKSI SAJA — tidak ada file diubah, tidak ada migrasi dijalankan, tidak ada data ditulis, tidak ada service di-restart, tidak ada bridge dijalankan. Satu-satunya artefak yang dibuat adalah dokumen ini.

> Kredensial: seluruh password, secret, token, dan API key tidak ditampilkan di dokumen ini.

---

## 1. Executive Summary

Aliran data sensor **ESP32 → Mosquitto → MQTT Bridge → Backend saat ini belum berfungsi end-to-end**. Penyebab utamanya (terbukti lewat inspeksi source + DB):

1. **Kontrak payload tidak cocok.** ESP32 mengirim `object_temp`/`ambient_temp`; bridge hanya mengenal `suhu`. Akibatnya 100% payload ESP32 ditolak diam-diam (log `WARNING` saja).
2. **Bridge menulis langsung ke tabel `Gejala`** (tabel *examination*) tanpa examination session, dan bahkan **meng-auto-registrasi pasien** dari kartu tak dikenal (NIK hash + password default).
3. **Tidak ada tabel telemetri.** Satu-satunya tempat "sah" saat ini adalah menumpang `Gejala`, yang salah secara arsitektur.
4. **Tidak ada asosiasi ke examination session.** Bridge tidak memakai infrastruktur `kiosksessions`/`kioskdevices` yang sudah ada.
5. **Ambang suhu tidak konsisten** (bridge 25–45 °C vs API/reconciliation 30–45 °C).

**Rencana (ringkas):** ubah bridge menjadi *thin MQTT adapter* yang memvalidasi + menormalisasi payload lalu meneruskannya ke backend melalui satu endpoint internal yang **terikat sesi kiosk aktif**. Tambahkan tabel aditif `sensor_readings` (idempotensi via `event_id` UNIQUE). Hentikan semua auto-registrasi dan penulisan langsung ke `Gejala`. Alur `Gejala` existing (`POST /api/kiosk-session/gejala`) tetap menjadi satu-satunya penulis examination.

**Hasil verifikasi kartu uji (penting):** kartu RFID `B1056B66` **TIDAK terdaftar** di `patient_cards`. Tidak ada pasien yang terhubung. Kartu ini belum bisa dipakai untuk uji integrasi sampai ada keputusan mapping yang eksplisit (lihat §11).

**Tidak ada perubahan yang boleh dieksekusi sebelum dua approval gate dilalui** (§18).

---

## 2. Confirmed User Decisions

| # | Keputusan | Status |
| :-- | :-- | :-- |
| A | Deployment tetap **native Ubuntu** (Mosquitto, MariaDB, FastAPI native; venv existing). **Tidak** migrasi ke Docker, **tidak** menambah dependensi Docker. | Dikonfirmasi user |
| B | Buat **tabel aditif** `sensor_readings`. Tabel existing & record existing **tidak boleh diubah/dihapus/di-rename**. **Tidak** ada migrasi otomatis tanpa approval terpisah. Konsep tabel disetujui; **DDL final & eksekusi belum disetujui**. | Dikonfirmasi user |
| C | Gunakan RFID UID `B1056B66` untuk uji. Wajib verifikasi mapping dulu; **tidak** membuat pasien baru otomatis; **tidak** menimpa mapping existing; bila ambigu → stop & lapor. | Dikonfirmasi user |

Catatan tambahan dari inspeksi yang menyimpang dari asumsi brief (bukan keputusan user, fakta terukur):

- Python environment aktual: `/home/orangepi/backend-measlescare/venv` (bukan `/home/orangepi/venv` yang disebut brief — path itu tidak ada).
- Backend berjalan **manual** (`python main.py`, PID 45181) dari shell, bukan systemd unit.
- Tidak ada container Docker sama sekali (0 image, 0 container).

---

## 3. Existing Architecture (terverifikasi langsung)

### 3.1 Runtime

| Komponen | Mekanisme | Bind / status |
| :-- | :-- | :-- |
| Mosquitto | systemd `mosquitto.service` | `0.0.0.0:1883`, active |
| MariaDB 10.6.23 | systemd | `127.0.0.1:3306`, active, db `db_huawei` |
| FastAPI | `python main.py` (manual, uvicorn) | `127.0.0.1:8000`, active |
| MQTT Bridge | `integrasi_sensor/bridge/mqtt_bridge.py` | **TIDAK berjalan** |
| Publisher Python | `integrasi_sensor/firmware/sensor_publisher.py` | **TIDAK berjalan** |
| Host IP | — | `192.168.20.238` (per `hostname -I`) |

### 3.2 Topik MQTT

| Topik | Arah | Catatan |
| :-- | :-- | :-- |
| `measlescare/sensor/reading` | ESP32 → broker | Dipublikasikan firmware |
| `measlescare/+/reading` | broker → bridge | Wildcard, cocok dengan topik di atas |

### 3.3 Payload ESP32 (aktual)

```json
{"event_id":"4bfed264-11648","device_id":"ESP32_SENSOR_01","rfid_uid":"B1056B66","ambient_temp":27.67,"object_temp":28.17,"uptime_ms":11649}
```

### 3.4 Skema database (terverifikasi via SQLAlchemy inspector)

14 tabel: `Camera, Gejala, Role, Status, Users, aturan_pakar, aturan_pakar_detail, evidence_reconciliations, hasil_pakar, jawaban_gejala, kioskdevices, kiosksessions, master_gejala, patient_cards`. **Tidak ada `sensor_readings`.**

Struktur kunci:

| Tabel | Kolom penting | FK |
| :-- | :-- | :-- |
| `Users` | `NIK` varchar(16) **PK**; `Name`, `password`, `id_Role` | `id_Role → Role.id_Role` |
| `patient_cards` | `id` int PK AI; `rfid_uid` varchar(64) **UNIQUE**; `NIK`; `created_at` | `NIK → Users.NIK` |
| `Gejala` | `id_gejala` varchar(20) PK; `NIK`; `Batuk`; `Suhu` float; `Tanggal` | `NIK → Users.NIK` |
| `kioskdevices` | `id_device` varchar(36) PK; `nama_device`; `secret_hash`; `aktif`; `created_at` | — |
| `kiosksessions` | `id_session` varchar(36) PK; `id_device`; `token_hash` **UNIQUE**; `expires_at`; `revoked`; `created_at` | `id_device → kioskdevices.id_device` |

Jumlah baris (live): `Users`=4 (1 admin + 3 pasien seeder), `patient_cards`=3, `Gejala`=4, `kiosksessions`=0, `kioskdevices`=1, `Camera`=3, `Status`=2.

### 3.5 Bridge saat ini (`integrasi_sensor/bridge/mqtt_bridge.py`, 254 baris)

| Bagian | Baris | Perilaku |
| :-- | :-- | :-- |
| `validate_reading()` | 38–61 | Wajib `rfid_uid` + `suhu` (25–45 °C) → `(rfid_uid, suhu)` |
| `RecentSeen` | 64–86 | Dedupe in-memory 60 dtk, key `rfid:suhu:ts` |
| `nik_from_rfid()` | 89–97 | NIK 16 digit deterministik dari SHA-256 UID (untuk auto-register) |
| `store_reading()` | 100–150 | **Auto-register pasien + INSERT `Gejala` langsung** |
| `on_message()` | 191–230 | Parse → validasi → dedupe → tulis; exception ditelan |
| `main()` | 153–250 | `connect()` sekali (gagal = mati), `loop_forever()` |

Dependensi bridge: `paho-mqtt` + `sqlalchemy` + `pymysql` + `python-dotenv`. **Fakta penting:** `paho-mqtt`, `httpx`, dan `requests` **belum terpasang** di venv repo (bridge saat ini tidak bisa dijalankan sama sekali sebelum `pip install paho-mqtt`).

### 3.6 Backend (FastAPI)

- Entry: `app/main.py` — 9 router, startup menjalankan `Base.metadata.create_all()` + `migrate_database()` + seeding (role/admin/master-gejala/aturan).
- `app/core/config.py` — `Settings` (`DATABASE_URL`, `SECRET_KEY`, `KIOSK_API_KEY`, rate-limit). Baca dari env/`.env` (`.env` root **tidak ada**; memakai default di source).
- `app/routers/kiosk_session.py` — infrastruktur sesi:
  - `_device_from_key()` (L35–42): autentikasi perangkat via `X-Kiosk-Key` (bcrypt vs `secret_hash`).
  - `_session_from_token()` (L45–83): parse `id_session|NIK|secret`, hash SHA-256 vs `token_hash` (constant-time), cek `revoked`, `expires_at` (20 mnt), device binding.
  - `create_gejala_from_kiosk()` (L189–212): **satu-satunya jalur sah** menulis `Gejala` dari kiosk.
- `app/routers/kiosk.py` — `/kiosk/identify-rfid` (kartu → pasien, **tidak** membuat pasien baru), `/kiosk/identify-face`, dll.
- Frontend (`/home/orangepi/frontend-measlescare/src/api/endpoints.ts`) sudah memakai `POST /api/kiosk-session/gejala` untuk menulis pemeriksaan.

---

## 4. Root Cause Analysis

| # | Root cause | Efek |
| :-- | :-- | :-- |
| 1 | Kontrak payload bridge (`suhu` 25–45) ≠ payload ESP32 (`object_temp`/`ambient_temp`) | 100% pembacaan ditolak senyap |
| 2 | Bridge menulis langsung ke `Gejala` (tabel examination), `Batuk=NULL`, tanpa sesi | Satu pembacaan = satu "pemeriksaan" yatim; menyeleweng dari alur examination |
| 3 | Auto-registrasi pasien dari UID tak dikenal (NIK hash + password default) | Identitas palsu; abuse lewat broker anonim |
| 4 | Tidak ada asosiasi ke `kiosksessions`/`kioskdevices` | Aturan "reading → session aktif" tidak terpenuhi |
| 5 | Ambang suhu beda (25–45 vs 30–45) + bridge melewati validasi Pydantic | Nilai 28.17 "lolos bridge" tapi INVALID di hilir |
| 6 | Idempotensi in-memory + `event_id` tak dipakai | Duplikat setelah restart / redelivery QoS 1 |
| 7 | Broker `allow_anonymous true` + bind `0.0.0.0:1883` | Seluruh LAN bisa baca/palsukan data kesehatan |
| 8 | Bridge tanpa systemd unit + `connect()` sekali | Mati saat boot / broker belum siap |
| 9 | `paho-mqtt` belum terpasang | Bridge belum bisa dijalankan |

---

## 5. Database Schema Proposal

### 5.1 Prinsip

- **Aditif murni**: 1 tabel baru, 0 kolom diubah, 0 constraint existing disentuh, 0 tabel di-rename/drop.
- `sensor_readings` = **staging/telemetri + audit trail**, bukan examination. Data final tetap di `Gejala`.
- Idempotensi persisten via `event_id` UNIQUE.
- Setiap pembacaan disimpan beserta status proses & status validasi + alasan penolakan + payload mentah (agar tidak ada pembacaan yang hilang tanpa jejak).

### 5.2 Kolom & tipe data

| Kolom | Tipe | Null | Keterangan |
| :-- | :-- | :-- | :-- |
| `id_reading` | BIGINT UNSIGNED AI | NO | PK |
| `event_id` | VARCHAR(64) | NO | Kunci idempotensi (dari payload; fallback hash) |
| `device_id` | VARCHAR(64) | NO | `device_id` MQTT yang dipublikasikan (mis. `ESP32_SENSOR_01`) |
| `rfid_uid` | VARCHAR(64) | YES | UID kartu (uppercase), **bukan** sumber identitas |
| `id_session` | VARCHAR(36) | YES | FK → `kiosksessions.id_session` (sesi aktif, nullable saat ditolak) |
| `NIK` | VARCHAR(16) | YES | FK → `Users.NIK`, diambil **dari sesi**, bukan dari kartu |
| `object_temp` | FLOAT | YES | Suhu tubuh kanonik (normalisasi dari `object_temp`/`suhu`), nilai asli |
| `ambient_temp` | FLOAT | YES | Suhu ambien (dipertahankan terpisah) |
| `uptime_ms` | BIGINT UNSIGNED | YES | Uptime ESP32 (deteksi reboot) |
| `source_format` | VARCHAR(20) | NO | `esp32` \| `python_publisher` |
| `status` | VARCHAR(24) | NO | Status proses (lihat §5.3) |
| `validation_status` | VARCHAR(20) | YES | Status validasi suhu: `VALID`/`INVALID`/`MISSING` |
| `reason` | VARCHAR(255) | YES | Alasan penolakan terstruktur |
| `raw_payload` | TEXT | YES | Payload JSON mentah (audit) |
| `received_at` | DATETIME | NO | Waktu diterima backend (default now) |

### 5.3 Nilai `status` (proses)

`ACCEPTED`, `REJECTED_PAYLOAD`, `REJECTED_UID`, `REJECTED_DEVICE`, `REJECTED_NO_SESSION`, `REJECTED_MULTI_SESSION`, `REJECTED_RANGE`.

(Duplikat `event_id` **tidak** disimpan sebagai baris baru — UNIQUE constraint menolak insert, bridge/backend mengakui sebagai "sudah diproses".)

### 5.4 Index & alasan

| Index | Tipe | Alasan |
| :-- | :-- | :-- |
| `PRIMARY (id_reading)` | PK | Identitas baris |
| `uq_sensor_readings_event_id (event_id)` | UNIQUE | Idempotensi tahan restart |
| `idx_sensor_readings_session (id_session)` | — | Query "semua reading milik sesi" |
| `idx_sensor_readings_patient_time (NIK, received_at)` | — | Riwayat telemetri per pasien, terurut waktu |
| `idx_sensor_readings_device_time (device_id, received_at)` | — | Audit per perangkat |

### 5.5 Foreign key & nullability

- `id_session → kiosksessions.id_session`, `ON DELETE SET NULL` — reading ditolak (tanpa sesi) tetap bisa disimpan dengan `id_session=NULL`.
- `NIK → Users.NIK`, `ON DELETE SET NULL` — identitas pasien tidak pernah memblokir retensi audit.
- Kedua kolom nullable karena pembacaan yang **ditolak** (mis. `REJECTED_NO_SESSION`) tidak punya sesi/pasien, tetapi tetap direkam untuk audit.

### 5.6 Retensi

Tidak ada kebijakan hapus otomatis di fase ini. Tabel tumbuh ~1 baris per pembacaan (beberapa per menit per kiosk saat aktif). Retention pruning (mis. arsip bulanan) diusulkan sebagai pekerjaan terpisah di fase berikutnya; tidak didefinisikan sekarang untuk menghindari keputusan destruktif.

---

## 6. SQL DDL (proposal — BELUM dieksekusi)

```sql
-- MariaDB 10.6 / InnoDB. Aditif; tidak menyentuh tabel existing.
CREATE TABLE IF NOT EXISTS sensor_readings (
  id_reading        BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  event_id          VARCHAR(64)     NOT NULL,
  device_id         VARCHAR(64)     NOT NULL,
  rfid_uid          VARCHAR(64)     NULL,
  id_session        VARCHAR(36)     NULL,
  NIK               VARCHAR(16)     NULL,
  object_temp       FLOAT           NULL,
  ambient_temp      FLOAT           NULL,
  uptime_ms         BIGINT UNSIGNED NULL,
  source_format     VARCHAR(20)     NOT NULL DEFAULT 'esp32',
  status            VARCHAR(24)     NOT NULL,
  validation_status VARCHAR(20)     NULL,
  reason            VARCHAR(255)    NULL,
  raw_payload       TEXT            NULL,
  received_at       DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id_reading),
  UNIQUE KEY uq_sensor_readings_event_id (event_id),
  KEY idx_sensor_readings_session (id_session),
  KEY idx_sensor_readings_patient_time (NIK, received_at),
  KEY idx_sensor_readings_device_time (device_id, received_at),
  CONSTRAINT fk_sensor_readings_session
    FOREIGN KEY (id_session) REFERENCES kiosksessions (id_session)
    ON DELETE SET NULL,
  CONSTRAINT fk_sensor_readings_patient
    FOREIGN KEY (NIK) REFERENCES Users (NIK)
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

Model SQLAlchemy padanan: `app/models/sensor.py` (class `SensorReading`, `__tablename__ = "sensor_readings"`).

---

## 7. ERD

Hubungan tabel baru terhadap schema existing (hanya hubungan yang relevan ditampilkan):

```
┌──────────────┐                ┌───────────────────┐
│    Users     │ 1           N  │   patient_cards   │
│  NIK (PK)    │◄───────────────│ id (PK)           │
│  Name        │                │ rfid_uid (UQ)     │
│  id_Role     │                │ NIK (FK)          │
└──────┬───────┘                └───────────────────┘
       │ 1
       │ (NIK)
       │ N
┌──────▼───────┐
│    Gejala    │  (tabel examination — TIDAK diubah, TIDAK disentuh bridge)
│ id_gejala(PK)│
│  NIK (FK)    │
│  Suhu        │
└──────────────┘

┌────────────────┐           ┌────────────────────┐
│  kioskdevices  │ 1       N │   kiosksessions    │
│ id_device (PK) │◄──────────│ id_session (PK)    │
│  secret_hash   │           │ id_device (FK)     │
│  aktif         │           │ token_hash (UQ)    │
└────────────────┘           │ expires_at, revoked│
                             └──────────┬─────────┘
                                        │ 1
                                        │ (id_session, SET NULL)
                                        │ 0..N
                             ┌──────────▼──────────────────────┐
                             │      sensor_readings  (NEW)     │
                             │ id_reading (PK, AI)             │
                             │ event_id (UQ)                   │
                             │ device_id                       │
                             │ rfid_uid                        │
                             │ id_session (FK → kiosksessions) │
                             │ NIK (FK → Users)                │
                             │ object_temp / ambient_temp      │
                             │ uptime_ms / source_format       │
                             │ status / validation_status      │
                             │ reason / raw_payload            │
                             │ received_at                     │
                             └─────────────────────────────────┘
```

Ringkasan relasi:

- `sensor_readings.id_session` → `kiosksessions.id_session` (0..N dari satu sesi; nullable, SET NULL).
- `sensor_readings.NIK` → `Users.NIK` (pasien dari sesi, bukan dari kartu; nullable, SET NULL).
- `sensor_readings` **tidak** ber-FK ke `patient_cards`/`Gejala` (agar tidak menciptakan dependensi pemeriksaan yang menyesatkan). `rfid_uid` disimpan sebagai string audit, bukan FK.

---

## 8. MQTT Bridge Refactoring Design

Arsitektur target:

```
ESP32 ──MQTT QoS1──► Mosquitto ──► Bridge (adapter tipis, systemd)
                                     1. parse JSON (invalid → log + counter, drop)
                                     2. normalize: object_temp→suhu kanonik; preserve ambient
                                     3. validate: UID regex, temp 30–45, device allowlist
                                     4. idempotency: event_id (fallback hash)
                                     5. POST /api/kiosk-session/reading (X-Kiosk-Key, retry+backoff)
                                              │
                                              ▼
                                    FastAPI (existing)
                                     • auth device (X-Kiosk-Key)
                                     • resolve active session (device binding)
                                     • INSERT sensor_readings (event_id UNIQUE)
```

Tanggung jawab bridge (fungsi yang diubah/ditambah di `mqtt_bridge.py`):

| Fungsi | Perubahan |
| :-- | :-- |
| `normalize_payload(data)` | **BARU**. Map `suhu` \| `object_temp` → `object_temp` kanonik; pertahankan `ambient_temp`, `event_id`, `device_id`, `uptime_ms`; deteksi `source_format`. |
| `validate_reading()` | Ganti: UID regex `^[0-9A-F]{4,32}$`, temp 30–45 (konstanta bersama), `device_id` wajib + allowlist, `event_id` wajib/fallback. Return objek hasil + `reason` terstruktur (bukan `None` saja). |
| `store_reading()` | **HAPUS** (auto-register + INSERT `Gejala` dibuang). |
| `post_reading()` | **BARU**. HTTP POST ke backend via stdlib `urllib` (tanpa dependensi baru), header `X-Kiosk-Key`, retry eksponensial, ack setelah sukses. |
| `on_connect/on_message/on_disconnect` | Tambah `on_disconnect` + counter; `connect_async()` + `loop_start()` (fix mati saat broker belum siap); log alasan penolakan terstruktur. |
| `RecentSeen` | Dipertahankan sebagai optimasi lapis pertama; idempotensi sesungguhnya di DB (`event_id`). |

Kontrak kanonik internal (hasil normalisasi):

```
event_id      string  (dari payload; fallback sha256(payload))
device_id     string  (wajib, allowlist)
rfid_uid      string  uppercase ^[0-9A-F]{4,32}$
object_temp   float   30.0..45.0  (WAJIB untuk suhu tubuh)
ambient_temp  float   opsional, -10..60
uptime_ms     int     opsional
received_at   datetime UTC (diisi backend)
```

Backward compatibility: payload publisher Python lama (`suhu`) tetap diterima (`source_format=python_publisher`). Firmware ESP32 **tidak diubah**.

---

## 9. Backend Integration Design

Endpoint internal **baru** (tidak ada endpoint existing yang cocok untuk telemetri):

```
POST /api/kiosk-session/reading
Headers:
  X-Kiosk-Key: <kunci perangkat kiosk>   (bcrypt vs kioskdevices.secret_hash)
Body:
  {
    "event_id": "4bfed264-11648",
    "device_id": "ESP32_SENSOR_01",
    "rfid_uid": "B1056B66",
    "object_temp": 36.7,
    "ambient_temp": 27.6,
    "uptime_ms": 11649,
    "source_format": "esp32"
  }
```

Perilaku (backend = validator otoritatif):

1. `_device_from_key()` — autentikasi perangkat (reuse existing).
2. Validasi payload (Pydantic) — field wajib, rentang suhu 30–45.
3. `_resolve_active_session(db, device)` — **BARU** (lihat §10): cari sesi aktif (`revoked=0`, `expires_at > now`) untuk `device.id_device`.
4. Insert `sensor_readings`:
   - Ada sesi aktif → `id_session`, `NIK` (dari sesi), `status=ACCEPTED` (atau `REJECTED_RANGE` bila suhu di luar 30–45, dengan `validation_status=INVALID`, `reason=temperature_out_of_range`, nilai asli tetap disimpan).
   - Tidak ada sesi → `id_session=NULL`, `NIK=NULL`, `status=REJECTED_NO_SESSION`.
   - Kartu tak dikenal → **tetap dicatat** `status=REJECTED_UID` (tanpa membuat pasien), `id_session` tetap diisi bila sesi aktif (untuk audit).
5. Idempotensi: `event_id` UNIQUE. `IntegrityError` duplikat → kembalikan 200 `{status:"duplicate"}` (idempotent, tidak crash).
6. Response terstruktur: `{status, id_reading, reason}`. Log audit per request (tanpa payload sensitif).

Keamanan:

- Endpoint memerlukan `X-Kiosk-Key` (bukan publik). Backend bind `127.0.0.1:8000` (loopback) sehingga tidak terekspos ke LAN.
- `rfid_uid` **tidak pernah** dipakai sebagai autentikasi/identitas pasien. Identitas pasien murni dari sesi.
- Rate limit (reuse `InMemoryRateLimiter`, mis. 120/mnt) untuk mencegah flood.
- Device binding mencegah reading dari satu kiosk diatribusikan ke sesi pasien kiosk lain.

**Tidak** membuat endpoint publik baru; **tidak** menyentuh `/api/kiosk-session/gejala` (tetap satu-satunya penulis `Gejala`).

---

## 10. Session Association Design

Masalah: bridge tidak punya session token (ESP32 adalah sensor buta). Solusi: resolusi sesi **dari perangkat**, bukan dari token.

Fungsi baru `_resolve_active_session(db, device)` di `app/services/sensor_service.py`:

```
1. query kiosksessions WHERE id_device = device.id_device
     AND revoked = 0 AND expires_at > now
2. 0 hasil  → None (→ REJECTED_NO_SESSION)
3. 1 hasil  → kembalikan sesi itu
4. >1 hasil → None (→ REJECTED_MULTI_SESSION; ambigu, tolak demi mencegah
              kontaminasi antar-pasien — default konservatif)
```

Aturan yang dipertahankan (konsisten dengan `_session_from_token`):

- `revoked` harus 0 (jangan terima konteks sesi basi).
- `expires_at > now` (20 menit, jangan terima sesi kedaluwarsa).
- Device binding: sesi yang dipakai harus `id_device == device.id_device` (mencegah reading kiosk A diatribusikan ke sesi pasien kiosk B).

Catatan arsitektur (dokumentasikan, tidak dieksekusi): `kiosksessions` tidak menyimpan pointer ke `Gejala` (id_gejala). Karena `sensor_readings` terpisah dan `Gejala` tetap ditulis lewat `/api/kiosk-session/gejala`, gap ini tidak menghalangi Phase 5. Menambah `id_gejala` nullable ke `kiosksessions` adalah opsi aditif yang **tidak diambil** di fase ini (agar tabel existing tetap utuh).

---

## 11. RFID Mapping Verification (kartu uji `B1056B66`)

Hasil query `patient_cards` (live, read-only):

| # | rfid_uid | NIK | Pasien |
| :-- | :-- | :-- | :-- |
| 1 | `E0040100ABCDEF0001` | 3201234567890002 | Bagas Pratama |
| 2 | `E0040100ABCDEF0002` | 3201234567890003 | Siti Rahayu |
| 3 | `E0040100ABCDEF0003` | 3201234567890004 | Dewi Lestari |

**Verifikasi `B1056B66`:**

- UID: `B1056B66`
- Terdaftar di `patient_cards`? **TIDAK** (`SELECT ... WHERE UPPER(rfid_uid)='B1056B66'` → kosong).
- Pasien terhubung: **TIDAK ADA**.
- NIK terhubung: **TIDAK ADA**.
- Status mapping: **belum terpetakan** (unmapped/unknown).
- Aman dipakai untuk uji integrasi? **BELUM** — kartu tidak dikenal.

Konsekuensi & rekomendasi (per Decision C):

1. Dengan `RFID_AUTO_REGISTER=false`, reading dari `B1056B66` akan menghasilkan `REJECTED_UID` (ditolak tanpa membuat pasien) — ini perilaku yang diinginkan.
2. Untuk uji end-to-end "sesi aktif + suhu valid", ada dua pilihan yang **membutuhkan keputusan eksplisit user** (keduanya adalah data-write, di luar scope inspeksi ini):
   - **(a)** Petakan `B1056B66` ke salah satu pasien seeder existing (mis. `3201234567890002`) lewat alur registrasi resmi (`POST /api/kiosk/identify-rfid` tidak menulis; perlu jalur/script pendaftaran kartu yang sudah ada di `scripts/` atau lewat SQL/script yang **disetujui**), atau
   - **(b)** Gunakan kartu seeder existing (`E0040100ABCDEF0001`) untuk kasus "sesi aktif", dan biarkan `B1056B66` untuk kasus "kartu tak dikenal" (`REJECTED_UID`).
3. **Tidak** membuat pasien baru otomatis, **tidak** menimpa mapping existing.

Rekomendasi saya: **(b)** untuk fase uji — tanpa mengubah data apa pun, sambil menunggu keputusan user soal mapping `B1056B66`.

---

## 12. Temperature Validation Policy

Lokasi validasi suhu yang diaudit:

| Lokasi | Ambang saat ini |
| :-- | :-- |
| `integrasi_sensor/bridge/mqtt_bridge.py` L30–31 | 25–45 °C |
| `app/schemas/main.py` L51 (`GejalaCreate.Suhu`) | 30–45 °C |
| `app/routers/kiosk_session.py` L31 (`CreateGejalaIn.Suhu`) | 30–45 °C |
| `app/services/reconciliation_service.py` L28 | 30–45 °C |

**Kebijakan final (satu sumber):** `SUHU_MIN=30.0`, `SUHU_MAX=45.0` untuk **suhu tubuh**; rentang ambien `-10..60` terpisah. Didefinisikan sekali di `app/core/constants.py` (baru) dan dibaca oleh bridge + schema + reconciliation (configurable via env).

Prinsip:

- Nilai asli **tidak pernah di-clamp/diubah**. `object_temp` disimpan apa adanya.
- Di luar 30–45 → `validation_status=INVALID`, `reason=temperature_out_of_range`, tetap disimpan (bukan dibuang) dengan nilai asli.
- Pembacaan di luar rentang **tidak pernah** ditafsirkan sebagai diagnosis; tidak pernah mengisi `Gejala.Suhu` otomatis.
- Catatan penting: payload uji 28.17 °C adalah **pembacaan uji rekayasa**, bukan suhu tubuh manusia valid (selisih ambient–objek 0.5 °C mengindikasikan sensor belum ekuilibrium termal / jarak salah). Dengan kebijakan 30–45, 28.17 akan ditolak sebagai `REJECTED_RANGE` — sesuai domain.

---

## 13. Configuration Changes

File konfigurasi baru: `integrasi_sensor/config.env` (dibuat dari `config.example.env`). Nilai yang diusulkan (audit Stage 5.1):

| Variabel | Nilai saat ini | Nilai usulan | Alasan |
| :-- | :-- | :-- | :-- |
| `RFID_AUTO_REGISTER` | `true` | **`false`** | Matikan auto-registrasi pasien palsu |
| `SUHU_MIN` | `25.0` | **`30.0`** | Samakan dengan kebijakan domain |
| `SUHU_MAX` | `45.0` | `45.0` | — |
| `MQTT_SUBSCRIBE_TOPIC` | `measlescare/+/reading` | `measlescare/+/reading` (tetap) | Wildcard cocok; boleh dispesifikkan |
| `MQTT_HOST` / `MQTT_PORT` | `127.0.0.1` / `1883` | tetap | — |
| `MQTT_ALLOWED_DEVICES` | (baru) | `ESP32_SENSOR_01` | Whitelist device_id |
| `BACKEND_URL` | (baru) | `http://127.0.0.1:8000` | Target endpoint bridge |
| `KIOSK_API_KEY` | (baru) | `<kunci perangkat kiosk>` | Auth bridge → backend (nilai dari `kioskdevices`) |
| `MQTT_USER` / `MQTT_PASSWORD` | kosong | (diisi bila broker auth diaktifkan, tahap terpisah) | — |

Catatan: `.env` root dan `integrasi_sensor/config.env` **belum ada** di disk (hanya `.example`). Membuat `config.env` adalah bagian dari implementasi, **bukan** sekarang.

---

## 14. File-Level Change Plan

Semua perubahan di bawah **dieksekusi hanya setelah Approval Gate B**.

### 14.1 File baru

| File | Isi |
| :-- | :-- |
| `integrasi_sensor/config.env` | Konfigurasi bridge (lihat §13) |
| `app/models/sensor.py` | Model `SensorReading` (tabel `sensor_readings`) |
| `app/services/sensor_service.py` | `ingest_sensor_reading()`, `_resolve_active_session()` |
| `app/core/constants.py` | Konstanta suhu tunggal (`SUHU_MIN/MAX`, rentang ambien) |
| `tests/test_mqtt_bridge.py` | Unit test normalize/validate |
| `tests/test_sensor_service.py` | Unit test service + endpoint |
| `/etc/systemd/system/measlescare-bridge.service` | Unit systemd (`Restart=always`, `After=mosquitto.service mariadb.service`) |

### 14.2 File yang diubah

| File | Perubahan | Risiko |
| :-- | :-- | :-- |
| `integrasi_sensor/bridge/mqtt_bridge.py` | Refactor ke adapter HTTP (§8); hapus auto-register & INSERT `Gejala`; `connect_async`/`loop_start`; `on_disconnect`; log terstruktur | **Sedang** (perilaku berubah total) |
| `app/routers/kiosk_session.py` | Tambah `POST /kiosk-session/reading` | Sedang (surface API +1) |
| `app/main.py` | Tambah `from app.models import sensor` agar `create_all` mengenali tabel | Rendah |
| `app/schemas/main.py` (atau file schema baru) | Schema `SensorReadingIn/Out` | Rendah |
| `Documentation.md`, `dokumentasi_database_erd.md`, `integrasi_sensor/README.md` | Dokumentasi tabel + arsitektur | None |

### 14.3 File yang **TIDAK** diubah

`Gejala`/alur examination, `app/routers/gejala.py`, `app/services/reconciliation_service.py` (kebijakan suhu diseragamkan via konstanta, logika tak diubah), frontend, `docker-compose.yml`, firmware ESP32, tabel existing, data existing.

---

## 15. Integration Test Matrix

Semua uji memakai `mosquitto_pub` (simulasi), **bukan** menyalakan ESP32 berulang. Uji DB di `db_huawei` setelah snapshot (§16); idealnya `db_huawei_test`.

| # | Kasus | Input | Hasil yang diharapkan |
| :-- | :-- | :-- | :-- |
| 1 | Payload ESP32 valid | `object_temp=36.7`, sesi aktif | `sensor_readings` 1 baris `ACCEPTED`, `id_session`+`NIK` terisi; `Gejala` tidak bertambah |
| 2 | `object_temp` hilang & `suhu` hilang | tanpa suhu | `REJECTED_PAYLOAD` / ditolak bridge, `reason=missing_temperature` |
| 3 | `event_id` hilang | tanpa event_id | `event_id` fallback hash; tetap tersimpan (1 baris) |
| 4 | JSON invalid | `{not json` | Bridge log warning, **tidak** ada baris DB, proses tetap hidup |
| 5 | Duplikat `event_id` (kirim 5×) | event_id sama | 1 baris total; kiriman ke-2..5 diakui sebagai duplikat (idempotent) |
| 6 | RFID tak dikenal | `rfid_uid=B1056B66` | `REJECTED_UID`, **tidak** ada `Users`/`patient_cards` baru |
| 7 | RFID dikenal, tanpa sesi aktif | `rfid_uid=E0040100ABCDEF0001`, kiosksessions kosong | `REJECTED_NO_SESSION`, `id_session=NULL` |
| 8 | Sesi aktif valid | sesi dibuat via `identify-face`, lalu reading | `ACCEPTED`, `NIK` = NIK sesi (bukan dari kartu) |
| 9 | Suhu invalid | `object_temp=28.17` | `REJECTED_RANGE`, `validation_status=INVALID`, nilai 28.17 tetap tersimpan di `object_temp`, `Gejala` tidak bertambah |
| 10 | MQTT disconnect/reconnect | restart broker saat bridge jalan | Bridge reconnect otomatis, tidak crash |
| 11 | Backend down 30 dtk | stop backend, kirim reading | Bridge retry + backoff, tidak crash; reading masuk setelah backend hidup |
| 12 | DB down | stop MariaDB | Bridge/backend log error; tidak crash loop; recovery setelah DB hidup |
| 13 | Cross-patient isolation | 2 sesi aktif beda perangkat | Reading perangkat A tidak pernah ke sesi perangkat B (`REJECTED_MULTI_SESSION`/device binding) |
| 14 | Pesan berulang (QoS 1 redelivery) | payload identik 2× | 1 baris (event_id UNIQUE) |
| 15 | `device_id` asing | `device_id=ESP32_EVIL` | `REJECTED_DEVICE` |

Verifikasi tanpa mengganggu produksi: `SELECT COUNT(*) FROM Gejala` tetap 4 di semua kasus (kecuali kasus yang sengaja lewat `/api/kiosk-session/gejala`).

---

## 16. Backup and Rollback Plan

### 16.1 Backup (sebelum implementasi apa pun)

1. `git status` bersih → `git tag phase5-baseline` (HEAD `5eaaec7`).
2. `mysqldump --single-transaction --routines --triggers db_huawei > backups/phase5_pre_$(date +%s).sql` (schema + data).
3. Salin file yang akan diubah ke `backups/` (mqtt_bridge.py, kiosk_session.py, main.py, schemas, docs).
4. Catat konfigurasi saat ini (mosquitto.conf, isi env, daftar systemd unit).
5. Verifikasi integritas: `grep -c "CREATE TABLE" backups/phase5_pre_*.sql`, `git rev-parse phase5-baseline`.

### 16.2 Rollback (per lapis)

| Lapis | Aksi | Waktu |
| :-- | :-- | :-- |
| Kode | `git reset --hard phase5-baseline` (atau restore file individu) + restart backend | <1 mnt |
| Konfigurasi | Hapus/kembalikan `integrasi_sensor/config.env` | <1 mnt |
| DB schema | `DROP TABLE IF EXISTS sensor_readings;` (aditif → drop aman, 0 dampak ke tabel lain) | <1 mnt |
| DB data | `mysql db_huawei < backups/phase5_pre_*.sql` | 1–2 mnt |
| Proses | `systemctl disable --now measlescare-bridge` → kembali manual | <1 mnt |
| Broker | (bila auth diaktifkan) kembalikan `allow_anonymous true` + `systemctl restart mosquitto` | <1 mnt |

### 16.3 Kriteria abort

Hentikan + rollback bila: (1) bridge crash-loop >3×/5 mnt; (2) `Gejala` bertambah tanpa aksi user; (3) `Users`/`patient_cards` bertambah otomatis; (4) ESP32 berhenti publish setelah perubahan auth broker; (5) latensi endpoint reading >500 ms p95; (6) RAM <150 MB.

### 16.4 Downtime

- Backend: restart singkat (<1 mnt) saat deploy model + route baru. Mosquitto & MariaDB tetap jalan.
- Bridge: belum ada bridge yang berjalan → tidak ada downtime bridge existing.
- Firmware: tidak diubah → 0 downtime.

---

## 17. Risks and Mitigations

| Risiko | Prob. | Dampak | Mitigasi |
| :-- | :-- | :-- | :-- |
| Kartu `B1056B66` tidak terdaftar → uji "sesi aktif" gagal | **Tinggi** | Sedang | Gunakan kartu seeder untuk kasus sesi; keputusan mapping eksplisit (§11) |
| `paho-mqtt` belum terpasang → bridge tak bisa jalan | **Tinggi** | Sedang | `pip install paho-mqtt` di venv (bagian implementasi) |
| Broker anonim = injeksi data kesehatan | Sedang | **Tinggi** | `RFID_AUTO_REGISTER=false` segera; auth broker tahap terpisah |
| Perubahan perilaku bridge (stop tulis `Gejala`) mengejutkan UI | Sedang | Sedang | Jalur `Gejala` existing tak diubah; paralel/staging dulu |
| `>1` sesi aktif per device → ambigu | Rendah | Sedang | Tolak `REJECTED_MULTI_SESSION` (default konservatif) |
| Backend tanpa systemd unit → restart manual rawan salah | Sedang | Sedang | Dokumentasikan; unit backend diusulkan terpisah (bukan scope) |
| `create_all` di startup membuat tabel otomatis | Rendah | Rendah | Jalankan DDL eksplisit lebih dulu (setelah Gate A), lalu model jadi no-op |

---

## 18. Approval Checklist

**APPROVAL GATE A — DATABASE SCHEMA** (diperlukan sebelum CREATE TABLE/DDL):

- [ ] Menyetujui DDL `sensor_readings` (§6) — kolom, tipe, index, constraint, FK.
- [ ] Menyetujui kebijakan suhu tunggal 30–45 °C (§12).
- [ ] Menyetujui strategi migrasi: DDL eksplisit (aditif) + model no-op via `create_all`.
- [ ] Menyetujui rollback `DROP TABLE sensor_readings` (§16).

**APPROVAL GATE B — IMPLEMENTATION** (diperlukan sebelum ubah kode/config):

- [ ] Menyetujui rencana perubahan file (§14).
- [ ] Menyetujui endpoint internal `POST /api/kiosk-session/reading` (§9).
- [ ] Menyetujui desain asosiasi sesi `_resolve_active_session` (§10).
- [ ] Menyetujui konfigurasi `RFID_AUTO_REGISTER=false`, `SUHU_MIN=30` (§13).
- [ ] **Keputusan mapping kartu `B1056B66`** (§11) — opsi (a) petakan, atau (b) pakai kartu seeder untuk uji.
- [ ] Menyetujui prosedur backup/rollback (§16).

**Status saat ini: BELUM ada yang dieksekusi. Menunggu persetujuan Gate A (schema) dan Gate B (implementasi) secara eksplisit.**

---

*Dokumen ini dihasilkan dari inspeksi read-only terhadap repo, database, dan service yang berjalan. Tidak ada perubahan yang dilakukan.*
