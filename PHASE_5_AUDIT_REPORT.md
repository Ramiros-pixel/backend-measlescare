# PHASE 5 AUDIT REPORT — MQTT Bridge & FastAPI Backend Integration

**Proyek:** MeaslesCare
**Device:** Orange Pi 4 Pro (Ubuntu, kernel 6.6.98-sun60iw2)
**Repo:** `/home/orangepi/backend-measlescare` (HEAD `5eaaec7`)
**Tanggal audit:** 20 November 2026
**Mode:** READ-ONLY — tidak ada file diubah, tidak ada container di-restart, tidak ada data di-insert, tidak ada bridge kedua dijalankan. Satu-satunya file yang dibuat adalah laporan ini.

> Catatan kredensial: seluruh password, secret, token, dan API key disamarkan. Nilai asli tidak ditampilkan di laporan ini.

---

## 1. Executive Summary

**Kesimpulan utama: aliran data ESP32 → Mosquitto → MQTT Bridge saat ini TIDAK BERFUNGSI. Setiap payload dari ESP32 ditolak secara diam-diam oleh bridge.**

Bukti langsung (dijalankan in-process, tanpa I/O database):

| Payload | Hasil `validate_reading()` |
| :--- | :--- |
| Payload ESP32 apa adanya (`ambient_temp` / `object_temp`) | `None` → **ditolak** |
| Payload publisher Python existing (`suhu`) | `('E0040100ABCDEF0001', 36.7)` → diterima |

Bridge hanya mengenal field `suhu`, sedangkan firmware ESP32 mengirim `ambient_temp` + `object_temp` + `event_id` + `uptime_ms`. `rfid_uid` cocok, field suhu tidak. Bridge mencatat `WARNING payload tidak valid` lalu `return` — tidak ada dead-letter, tidak ada alert, tidak ada retry. Dari sisi pengamat, sistem tampak "jalan" karena `mosquitto_sub` menampilkan pesan.

Temuan struktural lain yang sama pentingnya:

1. **Bridge menulis langsung ke tabel `Gejala` tanpa examination session.** Ini melanggar aturan arsitektur Phase 5C poin 4, 5, 6, dan 7: `rfid_uid` diperlakukan sebagai identitas tunggal, dan setiap pembacaan menghasilkan baris `Gejala` baru (satu pembacaan = satu "pemeriksaan").
2. **Bridge melakukan auto-registrasi pasien** (`mqtt_bridge.py` L118–140): kartu tak dikenal langsung membuat `Users` baru dengan NIK hasil hash SHA-256 dari UID, nama `Pasien <HEX>`, password default, dan role `R2`. Siapa pun yang bisa publish ke broker dapat membuat akun pasien.
3. **Broker tanpa autentikasi.** `allow_anonymous true` pada `listener 1883 0.0.0.0` — seluruh LAN dapat publish/read data kesehatan.
4. **Dokumentasi vs realitas infrastruktur berbeda total.** Brief menyebut container `huawei-backend`/`huawei-db` + MySQL port host 3307. Kenyataan: **tidak ada container sama sekali** (0 image, 0 container), database adalah **MariaDB 10.6 native** di `127.0.0.1:3306`, backend berjalan native (uvicorn, `127.0.0.1:8000`), Mosquitto native systemd. Port 3307 tidak ada yang listen.
5. **Bridge menganggap dirinya target Raspberry Pi/Orange Pi Python, bukan ESP32.** `integrasi_sensor/README.md` L19 menyatakan eksplisit "bukan ESP32". Implementasi ESP32 adalah publisher baru yang belum pernah disesuaikan dengan kontrak bridge.
6. **Rentang suhu tidak konsisten.** Bridge menerima 25–45 °C; API (`schemas/main.py` L51, `kiosk_session.py` L31) dan reconciliation (`reconciliation_service.py` L28) menetapkan 30–45 °C. `object_temp` 28.17 akan lolos bridge tetapi ditandai `INVALID` oleh modul hilir.
7. **Database produksi masih bersih.** `Gejala` berisi 4 baris, semuanya data seeder bertanggal 1–10 Nov 2026; `kiosksessions` 0 baris. Tidak ada jejak tulisan bridge. Belum ada kerusakan data yang perlu dibersihkan.

Yang **sudah benar dan layak dipakai ulang** (jangan dibangun ulang):

- Topik: `measlescare/+/reading` **cocok** dengan `measlescare/sensor/reading` (wildcard satu level). Tidak perlu ubah topik.
- Arsitektur sesi kiosk sudah ada dan cukup kuat: token `id_session|NIK|secret`, hash SHA-256 di DB, expiry 20 menit, device binding, `revoked` flag (`app/routers/kiosk_session.py` L45–124).
- Endpoint identifikasi RFID vs face sudah memisahkan peran sesuai keputusan arsitektur (RFID untuk registrasi, face untuk pasien lama).
- `patient_cards` sudah menjadi mapping `rfid_uid → NIK` dengan UNIQUE index.
- Backend berjalan sehat: `GET /` → `{"status":"ok","app":"Huawei ICT Backend"}`, 34 route aktif.

**Rekomendasi inti:** ubah bridge dari "penulis tabel `Gejala`" menjadi **"pengirim pembacaan ke backend melalui satu pintu resmi (session-bound)"**, dan tambahkan tabel staging `sensor_readings` dengan `event_id` UNIQUE untuk idempotensi. Detail di §13–§14.

---

## 2. Existing MQTT Architecture

### 2.1 Kondisi aktual

| Komponen | Kenyataan terukur |
| :--- | :--- |
| Broker | Mosquitto native, `systemd mosquitto.service` **active** |
| Listener | `listener 1883 0.0.0.0` (`/etc/mosquitto/conf.d/measlescare.conf`) |
| Auth | `allow_anonymous true` — **tanpa autentikasi** |
| Persistence | `persistence true`, `persistence_location /var/lib/mosquitto/` |
| Log | `log_dest file /var/log/mosquitto/mosquitto.log` |
| Port listening | `0.0.0.0:1883` (terverifikasi via `ss -lntp`) |
| Publisher | ESP32 (eksternal, tidak ada di repo) |
| Subscriber/bridge | `integrasi_sensor/bridge/mqtt_bridge.py` — **TIDAK berjalan** (tidak ada proses) |
| Publisher Python repo | `integrasi_sensor/firmware/sensor_publisher.py` — **TIDAK berjalan** |

### 2.2 Topik

| Topik | Arah | Status |
| :--- | :--- | :--- |
| `measlescare/sensor/reading` | ESP32 → broker | Dipublikasikan firmware |
| `measlescare/+/reading` | broker → bridge | **Cocok** (wildcard `+` = satu level) |
| `measlescare/<DEVICE_ID>/reading` | publisher Python → broker | Kontrak lama, `<DEVICE_ID>` default `kiosk-01` |

Topik tidak perlu diubah. Wildcard `+` juga berarti bridge menerima **topik apa pun** dengan pola `measlescare/*/reading` — termasuk device yang tidak dikenal.

### 2.3 Temuan

**F-01 — Broker terbuka untuk anonim (Severity: HIGH)**
Lokasi: `/etc/mosquitto/conf.d/measlescare.conf`
Kondisi: `allow_anonymous true` pada listener `0.0.0.0:1883`, port terbuka ke seluruh jaringan `192.168.20.0/24`.
Dampak: siapa pun di LAN dapat (a) membaca seluruh pembacaan suhu + UID kartu pasien, (b) memalsukan pembacaan, (c) memicu auto-registrasi pasien massal (§7), (d) menghabiskan disk via persistence.
Rekomendasi: `allow_anonymous false` + `password_file` per device, ACL per topik (`measlescare/ESP32_SENSOR_01/#`), atau mTLS. Minimal: firewall nftables/ufw membatasi 1883 ke IP ESP32 + localhost. **Jangan lakukan bersamaan dengan perubahan kode** — bridge belum punya kredensial yang teruji.

**F-02 — Tidak ada cara membedakan device sah (Severity: MEDIUM)**
Lokasi: `mqtt_bridge.py` L172–176, L191–207
Kondisi: bridge tidak memvalidasi `device_id`. Nilai `ESP32_SENSOR_01` hanya masuk ke payload, tidak dicocokkan dengan `kioskdevices` (yang sudah ada di DB, 1 baris aktif).
Dampak: reading dari device asing diperlakukan setara; tidak ada audit trail perangkat.
Rekomendasi: whitelist `device_id` lewat env `MQTT_ALLOWED_DEVICES`, atau map `device_id → kioskdevices.id_device` agar sesi bisa di-bind ke perangkat.

---

## 3. MQTT Bridge Source Code Analysis

File tunggal: `integrasi_sensor/bridge/mqtt_bridge.py` (254 baris). Berjalan sebagai proses terpisah dari FastAPI, mengimpor `app.models` dan `app.db.session` langsung (L180).

### 3.1 Peta fungsi

| Bagian | Baris | Fungsi |
| :--- | :--- | :--- |
| `validate_reading()` | L38–61 | Validasi payload → `(rfid_uid, suhu)` atau `None` |
| `RecentSeen` | L64–86 | Dedupe window 60 detik, key `rfid:suhu:ts` |
| `nik_from_rfid()` | L89–97 | NIK 16 digit deterministik (SHA-256 → mod 10^16) |
| `store_reading()` | L100–150 | Auto-register + INSERT `Gejala` |
| `on_connect()` | L184–189 | `subscribe(topic, qos=1)`; cek `reason_code != 0` |
| `on_message()` | L191–230 | Parse → validasi → dedupe → tulis |
| `main()` | L153–250 | Konfigurasi, connect, `loop_forever()` |

### 3.2 Konfigurasi

| Env | Default | Baris |
| :--- | :--- | :--- |
| `MQTT_HOST` | `127.0.0.1` | L172 |
| `MQTT_PORT` | `1883` | L173 |
| `MQTT_USER` / `MQTT_PASSWORD` | kosong → anonim | L174–175 |
| `MQTT_SUBSCRIBE_TOPIC` | `measlescare/+/reading` | L176 |
| `SUHU_MIN` / `SUHU_MAX` | `25.0` / `45.0` | L30–31, L57–58 |
| `RFID_AUTO_REGISTER` | `true` | L119 |
| `RFID_DEFAULT_PASSWORD` | `rfid123` | L135 |

Urutan pemuatan konfigurasi (L164–165): `integrasi_sensor/config.env` → `.env` root, keduanya `override=False`.

**F-03 — `.env` root tidak ada (Severity: MEDIUM)**
Lokasi: root repo (hanya `.env.example`), `integrasi_sensor/config.env` (hanya `config.example.env`)
Kondisi: kedua file konfigurasi tidak ada. Bridge akan memakai default `mqtt 127.0.0.1:1883` dan `DATABASE_URL` default dari `app/core/config.py` L14–17.
Dampak: konfigurasi produksi bergantung pada nilai default yang tertanam di source (termasuk kredensial DB default). Tidak ada jejak konfigurasi eksplisit yang bisa di-audit; perbedaan environment tidak terlihat.
Rekomendasi: buat `.env` (di luar scope read-only ini) dari `.env.example`, dan hapus kredensial default dari `config.py` (gagal keras bila `DATABASE_URL` tidak diset).

### 3.3 Payload parsing & validasi

**F-04 — Kontrak payload tidak cocok dengan ESP32 (Severity: CRITICAL)**
Lokasi: `mqtt_bridge.py` L47–61
Kondisi: validator membutuhkan `rfid_uid` (string 2–64 char) **dan** `suhu` (numerik, 25–45). Payload ESP32 tidak punya `suhu`.
Dampak: **100% pembacaan ESP32 dibuang.** Terbukti: `validate_reading(esp32_payload) → None`. Tidak ada data masuk DB selamanya, sementara log hanya `WARNING`. Ini kegagalan senyap — alasan utama Phase 5 belum berhasil.
Rekomendasi: tambahkan adapter payload di sisi bridge (bukan mengubah firmware): `suhu = object_temp` bila field `suhu` absen, teruskan `ambient_temp`, `event_id`, `uptime_ms`. Pertahankan dukungan format lama agar publisher Python tetap kompatibel (§7 untuk detail kontrak).

**F-05 — `ambient_temp` diabaikan total (Severity: LOW)**
Lokasi: `mqtt_bridge.py` L38–61
Kondisi: hanya `object_temp` (via `suhu`) yang dipakai. `ambient_temp` tidak disimpan, tidak dipakai untuk koreksi.
Dampak: hilangnya konteks kalibrasi; sulit mendiagnosis pembacaan bias (mis. sensor belum stabil, ambient 27.67 vs objek 28.17 → selisih hanya 0.5 °C, indikasi sensor belum mencapai ekuilibrium termal atau jarak salah).
Rekomendasi: simpan `ambient_temp` di staging untuk analitik & QA; pakai untuk aturan validasi "objek harus > ambient + 0.5 °C" bila pemeriksaan suhu tubuh.

**F-06 — Rentang suhu bridge ≠ rentang domain aplikasi (Severity: HIGH)**
Lokasi: `mqtt_bridge.py` L30–31 (25–45) vs `app/schemas/main.py` L51 dan `app/routers/kiosk_session.py` L31 (30–45) vs `app/services/reconciliation_service.py` L28 (30–45)
Kondisi: tiga ambang berbeda di tiga tempat. Bridge = satu-satunya jalur yang menulis tanpa melewati validasi Pydantic.
Dampak: nilai 25–30 °C tersimpan di `Gejala.Suhu` lalu ditandai `INVALID` oleh reconciliation ("Pengukuran suhu tubuh berada di luar rentang yang dapat diperiksa") — data masuk tetapi tidak dapat dipakai menyimpulkan apa pun, dan UI menerima angka yang mustahil untuk suhu tubuh manusia. Dengan `object_temp` 28.17 contoh di brief, skenario ini **pasti terjadi**.
Rekomendasi: satu sumber ambang (konstanta bersama, mis. `app/core/constants.py`), bridge menolak < 30 °C sebagai "bukan pembacaan tubuh" dan menandainya `rejected_out_of_range` di staging, bukan insert ke `Gejala`.

**F-07 — `null` handling longgar (Severity: LOW)**
Lokasi: L45–56
Kondisi: `rfid_uid` non-string/null → reject (baik); `suhu` null → reject (baik); `suhu` string numerik diterima via `float()` (mis. `"36.7"` lolos).
Dampak: toleransi tipe membuat kontrak tidak tegas; `NaN`/`Infinity` dari JSON Python (`float('nan')`) akan gagal pada perbandingan rentang sehingga aman, tetapi `"36,7"` (koma desimal) → `None` tanpa alasan jelas di log.
Rekomendasi: tolak non-numerik secara eksplisit; log alasan penolakan terstruktur (`reason=` field) agar bisa dihitung.

**F-08 — `event_id` tidak dipakai untuk idempotensi (Severity: HIGH)**
Lokasi: L204
Kondisi: kunci dedupe `f"{rfid_uid}:{suhu}:{ts}"`. ESP32 tidak mengirim `ts`, jadi kunci efektif `"<UID>:<suhu>:"`.
Dampak: (a) dua pemeriksaan sah pada kartu yang sama dengan suhu identik dalam 60 detik → pembacaan kedua **hilang**; (b) dedupe hanya in-memory, hilang saat proses restart → redelivery QoS 1 setelah restart menghasilkan duplikat; (c) `event_id` — satu-satunya field yang dirancang untuk idempotensi — tidak digunakan sama sekali.
Rekomendasi: gunakan `event_id` sebagai kunci idempotensi persisten (`UNIQUE` constraint di tabel staging). Fallback bila `event_id` absen: hash payload.

**F-09 — Dedupe in-memory, tidak tahan restart (Severity: MEDIUM)**
Lokasi: L64–86, L182
Kondisi: `RecentSeen` hidup di RAM proses.
Dampak: QoS 1 pada `clean_session=True` (default) → broker mengirim ulang bila PUBACK hilang; setelah restart bridge, jendela dedupe kosong dan duplikat masuk.
Rekomendasi: pindahkan idempotensi ke DB (§13), sisakan `RecentSeen` sebagai optimasi lapis pertama.

**F-10 — `max_items` diabaikan (Severity: LOW / bug)**
Lokasi: L71 (`max_items` disimpan tidak dipakai) vs L83 (hardcode `500`)
Kondisi: parameter konstruktor `max_items` mati; eviction selalu 500.
Dampak: parameter menyesatkan; tidak berbahaya saat ini.
Rekomendasi: gunakan `self.max_items`.

**F-11 — Parameter `payload` tidak dipakai (Severity: LOW)**
Lokasi: L100 `store_reading(db, rfid_uid, suhu, payload)`
Kondisi: `payload` tidak dibaca di body fungsi.
Dampak: dead parameter; menyiratkan fitur yang belum jadi (mis. menyimpan `event_id`).
Rekomendasi: jadikan input kontrak eksplisit saat refactor.

### 3.4 Reconnection & error handling

**F-12 — Kegagalan connect awal mematikan bridge permanen (Severity: HIGH)**
Lokasi: L241 `client.connect(...)` sebelum `loop_forever()`
Kondisi: `connect()` dipanggil sekali. Bila broker belum siap (mis. saat boot, Mosquitto belum active), `ConnectionRefusedError` naik dan proses keluar. `reconnect_delay_set` (L240) hanya berlaku untuk koneksi yang pernah sukses.
Dampak: pada urutan boot yang salah, bridge mati diam-diam dan tidak ada pembacaan yang tersimpan sampai dijalankan manual. Tidak ada systemd unit untuk bridge (tidak ditemukan di `systemctl`).
Rekomendasi: `client.connect_async()` + `loop_start()`, atau bungkus dalam retry loop dengan backoff; jadikan systemd service `Restart=always` setelah disetujui.

**F-13 — Tidak ada `on_disconnect` / observabilitas (Severity: MEDIUM)**
Lokasi: L184–189 (hanya `on_connect`), L243–249
Kondisi: tidak ada handler `on_disconnect`, tidak ada metrik (jumlah diterima/ditolak/disimpan), tidak ada dead-letter untuk payload invalid.
Dampak: kegagalan F-04 tidak terdeteksi otomatis; tidak ada cara menjawab "berapa reading masuk hari ini".
Rekomendasi: tambah `on_disconnect`, counter periodik di log, dan tabel/queue `rejected` dengan alasan.

**F-14 — `on_message` menelan semua exception (Severity: MEDIUM)**
Lokasi: L210–215
Kondisi: `except Exception: db.rollback(); log.exception(...); return` — pesan hilang tanpa retry/queue.
Dampak: gangguan DB sesaat (lock, restart) = kehilangan data permanen meski QoS 1 (PUBACK sudah dikirim ke broker sebelum commit, karena `on_message` sinkron dan tidak memanggil `message.ack` manual).
Rekomendasi: commit sebelum ack (QoS 2 semantics atau manual ack), atau tulis ke staging lokal dulu.

### 3.5 Database & insert mechanism

**F-15 — INSERT langsung ke `Gejala` per pembacaan (Severity: CRITICAL)**
Lokasi: L142–150
Kondisi: setiap pembacaan valid → `Gejala(id_gejala=uuid4[:20], NIK=card.NIK, Suhu=suhu, Batuk=None)`.
Dampak: (a) satu pembacaan sensor diperlakukan sebagai satu pemeriksaan lengkap — `Gejala` adalah tabel *examination* di ERD (`dokumen_database_erd.md`), bukan tabel telemetri; (b) `Batuk` selalu NULL sehingga rekam medis setengah jadi; (c) `hasil_pakar`/`jawaban_gejala`/`evidence_reconciliations` akan kosong untuk baris-baris ini; (d) membanjiri riwayat pasien dengan puluhan baris "pemeriksaan" dari satu sesi ukur; (e) melanggar Phase 5C poin 4, 6, 7.
Rekomendasi: **bridge berhenti menulis `Gejala`.** Lihat §13.

**F-16 — Auto-registrasi pasien dari kartu tak dikenal (Severity: CRITICAL)**
Lokasi: L118–140; didokumentasikan di `integrasi_sensor/README.md` L42–47
Kondisi: kartu tidak ada di `patient_cards` + `RFID_AUTO_REGISTER=true` (default) → buat `Users` (NIK hash, `Name="Pasien <HEX>"`, password default, `R2`) + `PatientCard`, lalu simpan.
Dampak: (a) identitas pasien dibangkitkan dari UID kartu, bukan dari registrasi nyata — melanggar Phase 5C poin 1 & 5; (b) akun dengan password default seragam dapat login; (c) vektor abuse: siapa pun yang publish banyak UID acak (broker anonim, F-01) membuat ratusan pasien sampah; (d) NIK hasil hash **bukan NIK valid** (bukan format NIK Indonesia, tidak terkait identitas sipil) sehingga merusak integritas data medis.
Rekomendasi: `RFID_AUTO_REGISTER=false` segera (satu baris env, tanpa ubah kode), dan hapus jalur auto-registrasi dari bridge pada refactor. Registrasi pasien hanya lewat alur kiosk/frontend yang sudah ada.

**F-17 — Tidak ada transaction boundary yang jelas (Severity: MEDIUM)**
Lokasi: L127–149
Kondisi: `db.add(User)` → `db.add(PatientCard)` → `db.add(Gejala)` → satu `db.commit()`.
Dampak: positif — atomik (gagal semua atau sukses semua). Negatif — `PatientCard.rfid_uid` UNIQUE dapat memicu `IntegrityError` saat race dengan request `/api/kiosk/identify-rfid`; ditangkap sebagai `Exception` generik sehingga pembacaan hilang, bukan di-retry.
Rekomendasi: UPSERT eksplisit / `SELECT ... FOR UPDATE` per UID, dan tangani `IntegrityError` sebagai "sudah terdaftar, lanjutkan".

**F-18 — Session DB per pesan tanpa pool tuning (Severity: LOW)**
Lokasi: L209–217 (`SessionLocal()` / `close()` per pesan); `app/db/session.py` L6
Kondisi: engine default pool; `pool_pre_ping=True`, `pool_recycle=3600`.
Dampak: pada laju 1 pesan/beberapa detik tidak masalah; pada burst bisa menghabiskan koneksi.
Rekomendasi: tetap satu sesi per pesan (aman), tetapi tambahkan `pool_size`/`max_overflow` eksplisit bila laju naik.

---

## 4. FastAPI Backend Architecture

### 4.1 Struktur

```
app/
  main.py                  # entry point, include 9 router, startup: create_all + migrate + seed
  core/config.py           # Settings (DATABASE_URL, API_PREFIX, SECRET_KEY, KIOSK_API_KEY, rate limit)
  core/security.py         # hash/verify password, JWT, DbSession, CurrentUser, AdminUser
  core/rate_limit.py       # rate_limit_rfid, rate_limit_session_create
  db/session.py            # engine + SessionLocal + Base
  db/migrations.py         # ALTER TABLE Users (idempotent, additive only)
  models/gejala.py         # Role, User, Gejala, Camera, KioskDevice, KioskSession, Status, PatientCard
  models/pakar.py          # MasterGejala, JawabanGejala, AturanPakar, AturanPakarDetail, HasilPakar
  models/reconciliation.py # EvidenceReconciliation
  routers/                 # auth, users, gejala, face, pakar, kiosk, kiosk_session, measles, reconciliation
  schemas/                 # main, face, pakar, measles, reconciliation
  services/                # face_engine, measles_engine, reconciliation_service
  seeders/                 # pakar_seeder, seed_all
  expert_system/           # decision_tree, inference_engine, knowledge_base
```

### 4.2 Kondisi runtime (terverifikasi)

| Item | Nilai |
| :--- | :--- |
| Proses | `venv/bin/python` (uvicorn multi-worker, PID 45181/45183), cwd = repo |
| Bind | `127.0.0.1:8000` (loopback saja) |
| Health | `GET /` → `200 {"status":"ok","app":"Huawei ICT Backend"}` |
| DB | MariaDB 10.6.23, `db_huawei`, `127.0.0.1:3306` |
| `API_PREFIX` | `/api` (default; live routes mengonfirmasi) |
| Env `DATABASE_URL` | tidak diset eksplisit di proses → memakai default `config.py` |

**F-19 — Startup melakukan DDL dan seeding otomatis (Severity: MEDIUM)**
Lokasi: `app/main.py` L97–164 (`Base.metadata.create_all`, `migrate_database()`, seed role/admin/master gejala/aturan)
Kondisi: setiap start backend menjalankan DDL + seeding, termasuk membuat admin default `admin`/`admin123` bila belum ada (L132–151, password dicetak ke stdout saat dibuat).
Dampak: tidak ada migrasi berversi; perubahan model tanpa persetujuan bisa langsung mengubah DB produksi. Password admin default adalah risiko bila DB di-reset.
Rekomendasi: di luar scope Phase 5, tetapi catat sebagai utang teknis. Untuk Phase 5, **jangan** menambah kolom via model tanpa persetujuan (karena `create_all` + aturan read-only).

**F-20 — Tidak ada service MQTT di layer backend (Severity: HIGH, gap arsitektur)**
Lokasi: seluruh `app/` (grep `mqtt` → 0 hasil)
Kondisi: backend sama sekali tidak tahu MQTT. Satu-satunya jalur data sensor adalah bridge yang menulis langsung ke DB, melewati seluruh aturan bisnis FastAPI (auth, session, rate limit, validasi Pydantic, audit).
Dampak: aturan aplikasi hanya berlaku untuk jalur HTTP; data sensor adalah warga kelas dua tanpa validasi domain. Ini akar penyebab F-06, F-15, F-16.
Rekomendasi: pindahkan penulisan ke backend (endpoint internal atau service in-process). Bridge menjadi adapter tipis.

### 4.3 SSE / WebSocket

**F-21 — Tidak ada SSE maupun WebSocket (Severity: LOW)**
Lokasi: `app/` (tidak ada `EventSourceResponse`, `websocket`, `StreamingResponse`)
Kondisi: realtime tidak tersedia. Frontend melakukan polling/request-response biasa.
Dampak: setelah integrasi sensor, UI tidak akan otomatis menampilkan suhu baru; perlu refresh manual. Bukan blocker Phase 5, tetapi memengaruhi UX "tempel kartu → suhu muncul".
Rekomendasi: pertimbangkan `GET /api/kiosk-session/{id}/events` (SSE) pada fase berikutnya; jangan dikerjakan di Phase 5.

---

## 5. Docker Networking Analysis

### 5.1 Kondisi aktual

```
docker ps -a   → kosong (0 container)
docker images  → kosong (0 image)
docker network → bridge, host, none (default saja)
```

Tidak ada container `huawei-backend`, `huawei-db`, maupun `huawei-mosquitto`. Stack yang berjalan **native**:

| Service | Mekanisme | Bind |
| :--- | :--- | :--- |
| Mosquitto | systemd | `0.0.0.0:1883` |
| MariaDB 10.6 | systemd | `127.0.0.1:3306` |
| FastAPI | uvicorn (venv) | `127.0.0.1:8000` |

**F-22 — Brief tidak sesuai realitas infrastruktur (Severity: HIGH, blocking untuk perencanaan)**
Lokasi: `docker-compose.yml` vs host
Kondisi: brief menyebut `huawei-backend` + `huawei-db` + MySQL host port `3307`. Kenyataan: 0 container, MariaDB native pada `3306`, tidak ada listener di `3307`.
Dampak: setiap rencana yang mengasumsikan container (mis. `docker compose exec`, `host.docker.internal`, DNS `db:3306`) akan gagal. Perintah di `integrasi_sensor/README.md` L158–162 (`docker compose exec mosquitto ...`) **tidak dapat dijalankan** di host ini.
Rekomendasi: tetapkan satu target deployment sebelum implementasi: **(A) tetap native** (paling murah, cocok dengan kondisi sekarang dan RAM 2 GB) atau **(B) kembali ke Docker**. Untuk Phase 5 saya rekomendasikan **(A)**, karena seluruh komponen sudah berjalan native dan terbukti sehat.

### 5.2 Analisis `docker-compose.yml` (bila opsi B dipilih)

| Baris | Isi | Masalah untuk integrasi |
| :--- | :--- | :--- |
| L3–21 | `db:` tanpa `ports:` | MySQL **tidak dipublikasikan ke host**. Bridge yang berjalan di host tidak bisa mencapai `127.0.0.1:3306`/`3307`. |
| L31 | `DATABASE_URL: ...@db:3306/db_huawei` | Hanya valid di dalam network compose; nilai host `3307` di brief tidak pernah ada di file. |
| L36–37 | `127.0.0.1:8000:8000` | Backend hanya loopback; konsisten dengan kondisi native. |
| L45–60 | `mosquitto` publish `1883:1883` | Akan **bentrok** dengan Mosquitto native yang sudah memakai `1883`. |
| — | tidak ada `extra_hosts` | `host.docker.internal` **tidak dikonfigurasi**. Di Linux, nama itu tidak otomatis ada (hanya Docker Desktop). Tanpa `extra_hosts: ["host.docker.internal:host-gateway"]`, container tidak bisa menjangkau broker native di host. |

**F-23 — `host.docker.internal` tidak dikonfigurasi (Severity: HIGH bila container)**
Lokasi: `docker-compose.yml` (tidak ada `extra_hosts`)
Kondisi: belum pernah disiapkan.
Dampak: bila backend dijadikan container dan broker tetap native, `MQTT_HOST=host.docker.internal` akan gagal resolve → `Name or service not known`.
Rekomendasi: bila container dipakai, tambahkan `extra_hosts: ["host.docker.internal:host-gateway"]` dan set `MQTT_HOST=host.docker.internal`; atau lebih aman: jalankan bridge **di host** (bukan di container), sehingga `127.0.0.1` tetap benar untuk broker *dan* DB.

**F-24 — MariaDB ≠ MySQL 8.4, dan DB hanya listen loopback (Severity: MEDIUM)**
Lokasi: host `ss -lntp` → `127.0.0.1:3306`; DB engine `10.6.23-MariaDB`
Kondisi: `compose` menargetkan `mysql:8.4`. Realitas MariaDB 10.6 dengan bind loopback.
Dampak: SQL yang kompatibel MySQL 8 (mis. `JSON_TABLE`, window function tertentu, `CHECK` enforcement) bisa berbeda perilaku di MariaDB. Bind loopback berarti **hanya proses di host** yang bisa terhubung — container tidak bisa, kecuali via `network_mode: host` atau bind diubah.
Rekomendasi: bridge wajib berjalan di host (bukan container) pada kondisi sekarang; perbarui dokumentasi agar menyebut MariaDB 10.6, bukan MySQL 8.4.

**F-25 — Bridge tidak punya unit systemd (Severity: MEDIUM)**
Lokasi: `systemctl list-units` → tidak ada unit bridge/publisher; `scripts/` hanya berisi `register_kiosk_device.py`
Kondisi: bridge dijalankan manual dari terminal.
Dampak: tidak ada auto-start saat boot, tidak ada auto-restart, tidak ada log terpusat. Bertabrakan dengan F-12.
Rekomendasi: buat `measlescare-bridge.service` (`Restart=always`, `After=mosquitto.service mariadb.service`, user non-root, `EnvironmentFile`) — setelah persetujuan.

---

## 6. Database Schema Analysis

Engine: **MariaDB 10.6.23**, database `db_huawei`. Tidak ada perubahan schema dilakukan.

### 6.1 Tabel relevan & jumlah baris

| Tabel | Baris | Peran |
| :--- | ---: | :--- |
| `Users` | 4 | Pasien + admin (`NIK` PK varchar(16)) |
| `patient_cards` | 3 | Mapping `rfid_uid` → `NIK` |
| `Gejala` | 4 | **Tabel pemeriksaan** (examination) |
| `kiosksessions` | 0 | Sesi kiosk aktif/kedaluwarsa |
| `kioskdevices` | 1 | Perangkat kiosk + secret hash |
| `Camera` | 3 | Hasil deteksi kamera per pemeriksaan |
| `Status` | 2 | Laporan per camera |
| `master_gejala` | 12 | Master gejala sistem pakar |
| `aturan_pakar` / `aturan_pakar_detail` | 7 / 15 | Rule base |
| `jawaban_gejala` | 8 | Jawaban kuesioner per pemeriksaan |
| `hasil_pakar` | 3 | Hasil inferensi per pemeriksaan |
| `evidence_reconciliations` | 0 | Rekonsiliasi bukti klinis |

### 6.2 Struktur kunci

**`Gejala`** (tabel examination — perhatikan: tidak ada kolom sesi, device, event, atau timestamp pengukuran terpisah)

| Kolom | Tipe | Null | Key |
| :--- | :--- | :--- | :--- |
| `id_gejala` | varchar(20) | NO | **PK** |
| `NIK` | varchar(16) | NO | MUL → `Users.NIK` |
| `Batuk` | varchar(20) | YES | — |
| `Suhu` | float | YES | — |
| `Tanggal` | datetime | NO | default `CURRENT_TIMESTAMP` |

**`patient_cards`**: `id` int PK AI, `rfid_uid` varchar(64) **UNIQUE**, `NIK` varchar(16) FK → `Users.NIK`, `created_at` datetime.

**`kiosksessions`**: `id_session` varchar(36) PK, `id_device` varchar(36) FK → `kioskdevices`, `token_hash` varchar(64) **UNIQUE**, `expires_at` datetime, `revoked` tinyint(1), `created_at`.

**`Users`**: `NIK` varchar(16) PK, `Name`, `Tempat_Tgl_Lahir`, `Golongan_darah` varchar(2), `Email` varchar(255) UNIQUE, `Alamat` text, `password` varchar(255), `id_Role` FK → `Role`.

### 6.3 Foreign key

```
Gejala.NIK                → Users.NIK
patient_cards.NIK         → Users.NIK
kiosksessions.id_device   → kioskdevices.id_device
Camera.id_gejala          → Gejala.id_gejala
Status.id_cam             → Camera.id_cam
jawaban_gejala.id_gejala  → Gejala.id_gejala
hasil_pakar.id_gejala     → Gejala.id_gejala   (UNIQUE)
evidence_reconciliations.id_gejala → Gejala.id_gejala (UNIQUE)
aturan_pakar_detail.kode_gejala → master_gejala.kode_gejala
Users.id_Role             → Role.id_Role
```

### 6.4 Temuan

**F-26 — Tidak ada tempat sah untuk telemetri sensor (Severity: CRITICAL)**
Lokasi: schema `db_huawei` (13 tabel, tidak ada `sensor_readings`/`measurements`)
Kondisi: satu-satunya jalan adalah menumpang `Gejala`. Tidak ada kolom `id_session`, `device_id`, `event_id`, `ambient_temp`, `uptime_ms`, atau `source`.
Dampak: tidak mungkin memenuhi Phase 5C poin 4 ("pembacaan sensor harus terhubung ke examination session aktif") dengan schema sekarang tanpa menyalahgunakan `Gejala`.
Rekomendasi: **tabel baru** (aditif, tidak destruktif) `sensor_readings` — usulan di §13.3. Perlu persetujuan eksplisit karena menyentuh schema.

**F-27 — `Gejala.Suhu` float tanpa constraint (Severity: MEDIUM)**
Lokasi: kolom `Suhu float NULL`
Kondisi: DB menerima nilai apa pun; validasi hanya di Pydantic (dan bridge melewatinya).
Dampak: data invalid bisa masuk permanen. Sudah terbukti berisiko lewat F-06.
Rekomendasi: jangan ubah schema di Phase 5; tegakkan di aplikasi/bridge. `CHECK` constraint bisa diusulkan terpisah (MariaDB 10.6 mendukung, tetapi berisiko pada data lama).

**F-28 — `Tanggal` tanpa index, `created_at` tidak ada di `Gejala` (Severity: LOW)**
Lokasi: `Gejala` (index hanya PK + `NIK`)
Kondisi: `GET /api/gejala/history` mengurutkan `Tanggal DESC` (L42) tanpa index.
Dampak: tidak terasa pada 4 baris; akan melambat setelah puluhan ribu baris (yang justru akan terjadi bila bridge tetap insert per pembacaan — lihat F-15).
Rekomendasi: evaluasi index setelah arsitektur persistence final.

**F-29 — Data saat ini bersih (Severity: INFO / baik)**
Lokasi: `Gejala` 4 baris (`G0000000000000000001..0004`, tanggal 2026-11-01..11-10), `kiosksessions` 0, `patient_cards` 3 (`E0040100ABCDEF000x`), `Users` 4 (`admin` + 3 seeder)
Kondisi: seluruh data adalah seeder (`app/seeders/seed_all.py` L88–94). Tidak ada baris hasil bridge.
Dampak: **tidak ada pembersihan data yang dibutuhkan** sebelum implementasi. Titik rollback bersih.
Rekomendasi: ambil snapshot `mysqldump` sebelum implementasi Phase 5 (§16).

---

## 7. Payload Contract Validation

### 7.1 Kontrak yang ada (tiga versi, tidak sinkron)

**A. ESP32 (aktual, dari brief)**

```json
{"event_id":"4bfed264-11648","device_id":"ESP32_SENSOR_01","rfid_uid":"B1056B66",
 "ambient_temp":27.67,"object_temp":28.17,"uptime_ms":11649}
```

**B. Bridge (`mqtt_bridge.py` L38–61) — yang diharapkan**

```json
{"rfid_uid":"<2-64 char>","suhu":<25..45>}
```

**C. Publisher Python repo (`sensor_publisher.py` L128–134) — yang dikirim**

```json
{"device_id":"kiosk-01","rfid_uid":"E0040100ABCDEF0001","suhu":36.7,
 "sensor":"mlx90614","ts":"2026-11-20T09:00:00+00:00"}
```

### 7.2 Matriks validasi field

| Field | Tipe ESP32 | Diperlukan bridge | Status | Catatan |
| :--- | :--- | :--- | :--- | :--- |
| `event_id` | string | tidak | **Tidak dipakai** | Kandidat utama idempotensi (F-08) |
| `device_id` | string | tidak | **Tidak dipakai** | Tidak divalidasi vs `kioskdevices` (F-02) |
| `rfid_uid` | string `B1056B66` | ya | **Cocok** | Normalisasi `.strip().upper()` baik |
| `ambient_temp` | float 27.67 | tidak | **Diabaikan** | Tidak tersimpan (F-05) |
| `object_temp` | float 28.17 | **ya (sebagai `suhu`)** | **MISMATCH** | Penyebab kegagalan utama (F-04) |
| `uptime_ms` | int 11649 | tidak | Tidak dipakai | Berguna untuk deteksi reboot ESP32 |

### 7.3 Uji perilaku (dijalankan, tanpa I/O DB)

```
ESP32 payload apa adanya     -> None                         (ditolak)
Payload publisher Python     -> ('E0040100ABCDEF0001', 36.7)  (diterima)
ESP32 + suhu=object_temp     -> ('B1056B66', 28.17)           (diterima, tapi 28.17 < 30 -> INVALID di hilir)
```

### 7.4 Skenario tepi

| Skenario | Perilaku sekarang | Penilaian |
| :--- | :--- | :--- |
| Field wajib hilang (`suhu`) | reject + warning | **Penyebab kegagalan produksi** |
| JSON invalid | reject + warning (L194–196) | OK |
| `rfid_uid` null/kosong | reject (L48) | OK |
| `rfid_uid` < 2 char | reject | OK, tetapi UID RFID nyata 8–14 hex; batas bawah 2 terlalu longgar |
| `object_temp` null | (field tak dikenal) reject | OK secara kebetulan |
| Suhu di luar 25–45 | reject | Ambang salah (F-06) |
| Suhu 25–30 (mis. 28.17) | **diterima** → `Gejala.Suhu=28.17` | **Salah** — ditandai INVALID oleh reconciliation |
| `event_id` duplikat | **tidak terdeteksi** | Duplikat masuk DB bila `suhu`/`ts` berbeda |
| Urutan pesan (QoS 1, 2 worker) | tidak ada ordering guarantee | Tidak relevan untuk telemetri, relevan bila dipakai untuk "nilai terakhir" |
| `rfid_uid` format aneh (`"a"`, `"../../"`, unicode) | diterima (2–64 char) | Perlu validasi `^[0-9A-F]{4,32}$` |
| `device_id` tak dikenal | diproses setara | Perlu whitelist (F-02) |
| `object_temp` = 0 / negatif | reject (< 25) | OK |
| Payload > ukuran wajar | tanpa batas eksplisit | Tambah `max payload` 1 KB |

### 7.5 Rekomendasi kontrak (tanpa mengubah firmware)

Adapter dua arah di bridge, prioritas: `suhu` → `object_temp` → reject.

```
Kontrak kanonik internal (hasil normalisasi bridge):
  event_id      string  (dari payload; fallback: sha256(payload)[:32])
  device_id     string  (wajib, harus terdaftar)
  rfid_uid      string  uppercase ^[0-9A-F]{4,32}$
  object_temp   float   30.0..45.0   <- WAJIB untuk "suhu tubuh"
  ambient_temp  float   opsional, -10..60
  uptime_ms     int     opsional
  received_at   datetime UTC (waktu broker terima)
```

Firmware ESP32 **tidak perlu diubah**. Cukup bridge yang menerjemahkan `object_temp → suhu`. Perubahan firmware hanya disarankan pada fase lanjutan (tambah `ts` + kirim `device_id` yang benar), dan itu opsional.

---

## 8. Patient Identity & Examination Session Analysis

### 8.1 Keputusan arsitektur vs implementasi

| # | Aturan Phase 5C | Kondisi aktual | Status |
| :--- | :--- | :--- | :--- |
| 1 | RFID untuk registrasi pasien baru | `/api/kiosk/identify-rfid` (L72–84) memetakan kartu → pasien, tapi **tidak membuat pasien baru**; pembuatan pasien baru justru dilakukan bridge secara otomatis (L118–140) dengan data palsu | **Menyimpang** |
| 2 | Pasien lama via Face Recognition | `/api/kiosk-session/identify-face` (L127–186) + `/api/kiosk/identify-face` (L87–101) sudah benar, server-side, tidak menerima klaim NIK | **Sesuai** |
| 3 | Backend membuat session setelah identitas terverifikasi | `POST /api/kiosk-session/create` (L86–124) mewajibkan face re-check; `identify-face` menerbitkan token | **Sesuai** |
| 4 | Pembacaan sensor terhubung ke session aktif | **Tidak ada kaitan apa pun** antara bridge dan `kiosksessions`. Bridge menulis atas `NIK` dari kartu | **Tidak terpenuhi** |
| 5 | `rfid_uid` bukan dasar identifikasi tunggal untuk pasien lama | Bridge memperlakukan `rfid_uid` sebagai **satu-satunya** dasar (L118) | **Dilanggar** |
| 6 | Jangan hubungkan sensor ke pasien tanpa session aktif | Bridge menulis ke pasien mana pun yang kartunya terbaca, tanpa cek session (malah membuat pasien baru bila belum ada) | **Dilanggar** |
| 7 | Jangan otomatis menyelesaikan pemeriksaan karena ada pembacaan | Bridge membuat baris `Gejala` baru = "pemeriksaan" baru; tidak ada konsep "menyelesaikan", tetapi efeknya sama: setiap pembacaan menjadi pemeriksaan | **Dilanggar** |

### 8.2 Mekanisme sesi yang sudah ada (layak dipakai)

`app/routers/kiosk_session.py`:

| Fungsi | Baris | Isi |
| :--- | :--- | :--- |
| `_device_from_key()` | L35–42 | Autentikasi perangkat via `X-Kiosk-Key` + bcrypt verify terhadap `kioskdevices.secret_hash` |
| `_session_from_token()` | L45–83 | Parse `id_session\|NIK\|secret`, bandingkan SHA-256 dengan `token_hash` (constant-time), cek `revoked`, cek `expires_at` (20 menit), cek device aktif, **device binding** (L76–81) |
| `create_kiosk_session()` | L86–124 | Wajib `X-Kiosk-Key`; verifikasi wajah server-side terhadap NIK yang diklaim (L99–102); terbitkan token |
| `identify_face_and_create_session()` | L127–186 | Identifikasi tanpa klaim NIK (anti-spoofing), langsung terbitkan sesi |
| `create_gejala_from_kiosk()` | L189–212 | **Satu-satunya jalur sah** menulis `Gejala` non-UI: wajib `X-Kiosk-Session` + `X-Kiosk-Key`, NIK diambil dari token, bukan parameter |
| `revoke_kiosk_session()` | L215–226 | Set `revoked=True` |

Ini adalah fondasi yang benar. Masalahnya: bridge tidak memakainya.

**F-30 — `kiosksessions` tidak menyimpan `id_gejala` (Severity: HIGH)**
Lokasi: `kiosksessions` (kolom: `id_session`, `id_device`, `token_hash`, `expires_at`, `revoked`, `created_at`)
Kondisi: sesi hanya mengikat (perangkat, pasien, masa berlaku). Tidak ada pointer ke pemeriksaan yang sedang berjalan.
Dampak: bridge tidak dapat menjawab "examination mana yang aktif untuk sesi ini". Tanpa ini, aturan Phase 5C poin 4 tidak bisa ditegakkan hanya dengan data yang ada.
Rekomendasi: dua opsi (pilih satu, keduanya perlu persetujuan schema):
- **(i) Aditif minimal:** tambah `id_gejala` nullable + `finalized_at` nullable ke `kiosksessions`.
- **(ii) Tabel staging baru** `sensor_readings` dengan `id_session` FK (rekomendasi saya, §13.3) — tidak menyentuh tabel existing sama sekali.

**F-31 — Frontend sudah memakai `POST /api/kiosk-session/gejala` (Severity: INFO / penting)**
Lokasi: `/home/orangepi/frontend-measlescare/src/api/endpoints.ts` L228
Kondisi: alur UI saat ini mengirim `Suhu` + `Batuk` dari kiosk setelah sesi dibuat. Artinya **sudah ada jalur resmi** untuk menulis pemeriksaan.
Dampak: menggabungkan sensor ke jalur ini = 0 endpoint baru, 0 duplikasi, sesuai aturan "jangan buat endpoint duplikat".
Rekomendasi: jadikan `kiosk-session/gejala` (atau turunannya) sebagai satu-satunya penulis `Gejala` dari dunia sensor.

---

## 9. Data Persistence Analysis

### 9.1 Jawaban langsung atas pertanyaan audit

| Pertanyaan | Jawaban |
| :--- | :--- |
| Apakah bridge menyimpan langsung ke `Gejala`? | **Ya.** `mqtt_bridge.py` L142–150. |
| Apakah setiap pembacaan → record baru? | **Ya.** `id_gejala = uuid4().hex[:20]`, selalu INSERT, tanpa UPSERT. |
| Apakah data sementara dan hasil final tercampur? | **Ya.** `Gejala` adalah tabel examination (punya `hasil_pakar`, `jawaban_gejala`, `evidence_reconciliations` sebagai anak). Bridge menulis baris tanpa anak → sampah semi-final. |
| Potensi duplikat? | **Ya, tiga sumber:** (a) dedupe in-memory hilang saat restart (F-09); (b) `event_id` tidak dipakai (F-08); (c) redelivery QoS 1 setelah crash tanpa ack manual (F-14). |
| Hubungan reading ↔ patient ↔ examination? | Hanya `reading.NIK → Users.NIK`. **Tidak ada** hubungan ke sesi, perangkat, atau event. |

### 9.2 Dampak terukur pada data sekarang

- `Gejala`: 4 baris, semua seeder. Belum ada polusi. **Ini kesempatan emas** untuk memperbaiki arsitektur sebelum data nyata masuk.
- Bila bridge dijalankan apa adanya dengan firmware yang diperbaiki (`suhu` dikirim): 1 kartu ditempel 1× = 1 baris `Gejala`; satu sesi pemeriksaan realistis (identifikasi → ukur → jawab kuesioner → foto → evaluasi) dapat menghasilkan 3–10 baris, dan hanya satu yang akan punya `hasil_pakar`. Sisanya baris yatim.
- Auto-registrasi (F-16) akan membuat `Users` dengan NIK hash — tidak dapat direkonsiliasi dengan NIK sipil bila pasien datang lagi.

### 9.3 Rekomendasi mekanisme persistence (kompatibel dengan existing)

Prinsip: **`Gejala` tetap milik backend. Bridge tidak menulis tabel domain.**

Alur target:

```
ESP32 ──MQTT──> Mosquitto ──> Bridge (adapter tipis)
                                  │  1. parse + normalisasi (object_temp -> suhu)
                                  │  2. validasi domain (30..45, UID regex, device whitelist)
                                  │  3. idempotensi via event_id
                                  ▼
                    POST /api/kiosk-session/reading   (internal, X-Kiosk-Key)
                                  │  backend: cek sesi aktif (token/device) -> NIK dari sesi
                                  │  tulis ke sensor_readings (staging, id_session FK)
                                  ▼
                    UI kiosk / endpoint existing  ->  Gejala (examination final)
                                  ▼
                    /api/reconciliation/evaluate + /api/pakar/evaluasi
```

Konsekuensi:
- 0 endpoint duplikat: `kiosk-session/gejala` tetap penulis `Gejala`; yang baru hanya penerima telemetri.
- `rfid_uid` **tidak** menjadi dasar identifikasi untuk pasien lama — identitas datang dari sesi (face-verified) atau dari kartu **terdaftar** pada alur registrasi.
- Tidak ada pemeriksaan yang "selesai" karena sensor; pembacaan hanya mengisi `Suhu` pada examination yang sedang berjalan.
- Idempotensi tahan restart (UNIQUE `event_id`).
- Data sementara (banyak pembacaan) terpisah dari data final (1 examination).

---

## 10. Existing API Inventory

Terverifikasi dari `GET /openapi.json` pada instance yang berjalan (34 route).

| Method | Path | Auth | Fungsi | Dipakai frontend |
| :--- | :--- | :--- | :--- | :--- |
| GET | `/` | — | Health check | — |
| POST | `/api/auth/register` | — | Registrasi akun | ✅ |
| POST | `/api/auth/login` | — | JWT login | ✅ |
| GET | `/api/auth/me` | JWT | Profil token | ✅ |
| GET | `/api/users` | JWT/Admin | Daftar user | ✅ |
| GET | `/api/users/me` | JWT | Profil sendiri | ✅ |
| GET | `/api/users/{nik}` | JWT/Admin | Detail user | — |
| POST | `/api/gejala` | JWT | Catat gejala (NIK dari token) | ✅ |
| GET | `/api/gejala/history` | JWT | Riwayat (admin: semua) | — |
| GET | `/api/gejala/{id_gejala}` | JWT | Detail pemeriksaan | — |
| POST | `/api/camera` | JWT | Rekam deteksi kamera | ✅ |
| GET | `/api/camera` | JWT | Daftar deteksi | — |
| POST | `/api/face/capture` | JWT | Simpan sampel wajah | — |
| POST | `/api/face/login` | — | Login via wajah | — |
| POST | `/api/face/recognize` | JWT | Kenali wajah | ✅ |
| POST | `/api/face/train` / `/retrain` | JWT | Latih model | — |
| GET | `/api/face/model` / `/status` | JWT | Status model | — |
| DELETE | `/api/face/reset/{nik}` | JWT | Hapus sampel | — |
| POST | `/api/pakar/evaluasi` | JWT | Inferensi sistem pakar | ✅ |
| GET | `/api/pakar/hasil/{id_gejala}` | JWT | Hasil pakar | — |
| GET | `/api/pakar/master-gejala` | JWT | Master gejala | ✅ |
| POST | `/api/reconciliation/evaluate` | JWT | Rekonsiliasi bukti klinis | ✅ |
| GET | `/api/reconciliation/{id_gejala}` | JWT | Hasil rekonsiliasi | — |
| POST | `/api/kiosk/identify-rfid` | X-Kiosk-Key | Kartu → pasien | ✅ |
| POST | `/api/kiosk/identify-face` | X-Kiosk-Key | Wajah → pasien | ✅ |
| POST | `/api/kiosk/email` | X-Kiosk-Key | Simpan email pasien | ✅ |
| POST | `/api/kiosk/face/recognize` | X-Kiosk-Key | Verifikasi 1:1 | ✅ |
| POST | `/api/kiosk/face/capture` | X-Kiosk-Key | Ambil sampel | ✅ |
| POST | `/api/kiosk/face/train` | X-Kiosk-Key | Latih model | ✅ |
| POST | `/api/kiosk-session/create` | X-Kiosk-Key | Buat sesi (re-verify wajah) | ✅ |
| POST | `/api/kiosk-session/identify-face` | X-Kiosk-Key | Sesi langsung dari wajah | ✅ |
| POST | `/api/kiosk-session/gejala` | X-Kiosk-Session + Key | **Tulis pemeriksaan** | ✅ |
| POST | `/api/kiosk-session/revoke` | X-Kiosk-Session + Key | Tutup sesi | ✅ |
| POST | `/api/v1/measles/predict` | — | Klasifikasi CV 6 kelas | ✅ |

**Tidak ada** endpoint MQTT/sensor/telemetri: tidak ada duplikasi yang perlu dihindari, tetapi juga belum ada pintu masuk untuk sensor.

**F-32 — `POST /api/gejala` duplikat fungsional dengan `/api/kiosk-session/gejala` (Severity: LOW)**
Lokasi: `app/routers/gejala.py` L14–26 vs `app/routers/kiosk_session.py` L189–212
Kondisi: dua jalur menulis `Gejala` dengan trust model berbeda (JWT user vs sesi kiosk). Tidak ada validasi bahwa satu examination tidak ditulis dua kali.
Dampak: tidak berbahaya sekarang, tetapi menambah jalur yang harus dijaga saat integrasi sensor. **Jangan menambah jalur ketiga** (mis. `POST /api/sensor/reading` yang langsung ke `Gejala`).
Rekomendasi: sensor → `kiosk-session` (telemetri) → satu penulisan `Gejala`.

---

## 11. Identified Issues

Diurutkan berdasarkan severity. ID merujuk bagian detail di atas.

| ID | Severity | Isu | Lokasi |
| :--- | :--- | :--- | :--- |
| F-04 | **CRITICAL** | Payload ESP32 (`object_temp`) tidak dikenali bridge (`suhu`) → 100% ditolak senyap | `mqtt_bridge.py` L47–61 |
| F-15 | **CRITICAL** | Bridge INSERT langsung ke `Gejala` per pembacaan (tanpa sesi, `Batuk=NULL`) | `mqtt_bridge.py` L142–150 |
| F-16 | **CRITICAL** | Auto-registrasi pasien dari kartu tak dikenal (NIK hash, password default) | `mqtt_bridge.py` L118–140 |
| F-26 | **CRITICAL** | Tidak ada tabel/kolom sah untuk telemetri sensor | schema `db_huawei` |
| F-01 | HIGH | Broker `allow_anonymous true` pada `0.0.0.0:1883` | `/etc/mosquitto/conf.d/measlescare.conf` |
| F-06 | HIGH | Ambang suhu 25–45 (bridge) vs 30–45 (API & reconciliation) | L30–31 vs `schemas/main.py` L51 |
| F-08 | HIGH | `event_id` tidak dipakai untuk idempotensi | `mqtt_bridge.py` L204 |
| F-12 | HIGH | Connect awal gagal → proses mati, tanpa retry | `mqtt_bridge.py` L241 |
| F-20 | HIGH | Backend tidak punya layer MQTT; semua aturan bisnis dilewati | `app/` (0 referensi) |
| F-22 | HIGH | Brief (Docker, 3307, MySQL 8.4) ≠ realitas (native, 3306, MariaDB 10.6) | host vs `docker-compose.yml` |
| F-23 | HIGH* | `host.docker.internal` tidak dikonfigurasi (*relevan bila container) | `docker-compose.yml` |
| F-30 | HIGH | `kiosksessions` tidak menunjuk examination | schema `kiosksessions` |
| F-02 | MEDIUM | `device_id` tidak divalidasi | L172–207 |
| F-03 | MEDIUM | `.env` root & `config.env` sensor tidak ada; mengandalkan default source | root repo |
| F-09 | MEDIUM | Dedupe in-memory hilang saat restart | L64–86 |
| F-13 | MEDIUM | Tidak ada `on_disconnect`, metrik, dead-letter | L184–249 |
| F-14 | MEDIUM | Exception menelan pesan tanpa retry (PUBACK dikirim sebelum commit) | L210–215 |
| F-17 | MEDIUM | Race `PatientCard` UNIQUE → `IntegrityError` generik, reading hilang | L127–149 |
| F-19 | MEDIUM | Startup menjalankan DDL + seeding + admin default | `app/main.py` L97–164 |
| F-24 | MEDIUM | MariaDB (bukan MySQL 8.4), DB bind loopback | host |
| F-25 | MEDIUM | Bridge tanpa systemd unit | host |
| F-27 | MEDIUM | `Gejala.Suhu` float tanpa constraint DB | schema |
| F-05 | LOW | `ambient_temp` diabaikan | L38–61 |
| F-07 | LOW | Toleransi tipe longgar, log tanpa alasan terstruktur | L45–56 |
| F-10 | LOW | `max_items` diabaikan (hardcode 500) | L71 vs L83 |
| F-11 | LOW | Parameter `payload` tidak dipakai | L100 |
| F-18 | LOW | Pool DB tanpa tuning eksplisit | `db/session.py` L6 |
| F-21 | LOW | Tidak ada SSE/WebSocket | `app/` |
| F-28 | LOW | `Gejala.Tanggal` tanpa index | schema |
| F-32 | LOW | Dua jalur tulis `Gejala` | `gejala.py` L14 vs `kiosk_session.py` L189 |
| F-29 | INFO | Data produksi bersih (tidak perlu pembersihan) | DB |

---

## 12. Risk Assessment

### 12.1 Risiko tanpa perubahan (status quo)

| Risiko | Probabilitas | Dampak | Catatan |
| :--- | :--- | :--- | :--- |
| Phase 5 dianggap "berhasil" padahal 0 data tersimpan | **Tinggi** | Tinggi | `mosquitto_sub` menampilkan payload; bridge diam. Sudah terjadi. |
| Payload diformat ulang di sisi ESP32 "asal jalan" | Sedang | Sedang | Solusi cepat yang mengunci utang teknis di firmware |
| Injeksi data via broker anonim | Sedang | **Tinggi** | Data kesehatan pasien; auto-registrasi memperparah |
| Duplikat tak terkendali saat retry | Sedang | Sedang | Belum terasa karena 0 data |
| Bridge mati saat reboot, tidak ada yang sadar | **Tinggi** | Sedang | Tanpa systemd unit + tanpa alert |

### 12.2 Risiko per perubahan yang diusulkan

| Perubahan | Risiko | Mitigasi |
| :--- | :--- | :--- |
| Adapter payload `object_temp → suhu` | Rendah — fungsi murni, teruji unit | Pertahankan dukungan `suhu`; unit test untuk kedua format |
| `RFID_AUTO_REGISTER=false` | Rendah, tetapi kartu uji `B1056B66` belum terdaftar → reading akan ditolak | Daftarkan kartu uji lebih dulu (via script/API), baru matikan auto-register |
| Stop INSERT ke `Gejala` dari bridge | **Sedang** — perilaku berubah; UI tidak lagi melihat baris otomatis | Jalankan paralel (staging) sebelum mematikan jalur lama; snapshot DB |
| Tabel baru `sensor_readings` | Rendah (aditif), tetapi `create_all` di startup akan membuatnya otomatis | Perlu persetujuan schema; dokumentasikan di `dokumentasi_database_erd.md` |
| Endpoint internal `kiosk-session/reading` | Sedang — menambah surface API | Wajib `X-Kiosk-Key` + rate limit, tidak diekspos ke publik (bind loopback) |
| Ambang suhu 30–45 di bridge | Rendah | Nilai 28.17 tidak lagi diterima sebagai suhu tubuh — sesuai domain |
| Autentikasi broker | **Sedang–Tinggi** — bila salah, ESP32 berhenti publish | Uji dengan `mosquitto_pub` ber-kredensial dulu; rollback = satu baris config |
| systemd unit bridge | Rendah | `Restart=always`; rollback = `systemctl disable --now` |
| Menjalankan Docker lagi | **Tinggi** di host 2 GB: bentrok port 1883, DB double, RAM | Rekomendasi: tetap native (opsi A) |

### 12.3 Klasifikasi data

Data yang mengalir: UID kartu RFID + suhu tubuh + identitas pasien (NIK, nama, email). Ini **data kesehatan pribadi**. Konsekuensi: broker anonim (F-01) dan password default (F-16) bukan sekadar bug kualitas — keduanya adalah masalah kepatuhan. Perbaikan keduanya tidak boleh ditunda ke fase berikutnya setelah data nyata mulai mengalir.

---

## 13. Recommended Integration Architecture

### 13.1 Prinsip

1. **`Gejala` tetap milik backend.** Bridge tidak pernah menulis tabel domain.
2. **Identitas dari sesi, bukan dari kartu** (kecuali alur registrasi eksplisit).
3. **Idempotensi di DB**, bukan di RAM.
4. **Satu kontrak kanonik** di bridge; firmware tidak diubah.
5. **Reuse maksimal:** `kiosksessions`, `kioskdevices`, `patient_cards`, `_session_from_token`, `_device_from_key`, `/api/kiosk-session/gejala`.

### 13.2 Arsitektur target

```
┌──────────┐   MQTT QoS1    ┌────────────┐    TCP 127.0.0.1:1883
│  ESP32   │ ─────────────► │ Mosquitto  │ ◄──────────────┐
│ SENSOR_01│  measlescare/  │  (native)  │                │
└──────────┘  sensor/reading└────────────┘                │
                                                          │
                    ┌─────────────────────────────────────┴──────┐
                    │  Bridge (native, systemd)                  │
                    │  1. parse JSON                             │
                    │  2. normalize: object_temp → suhu          │
                    │  3. validate: UID regex, 30–45 °C, device  │
                    │  4. idempotency key = event_id             │
                    │  5. POST /api/kiosk-session/reading        │
                    │     (X-Kiosk-Key, retry + backoff)         │
                    └───────────────────┬────────────────────────┘
                                        │ HTTP 127.0.0.1:8000
                    ┌───────────────────▼────────────────────────┐
                    │  FastAPI (existing)                        │
                    │  • resolve device → kioskdevices           │
                    │  • resolve active session (device binding, │
                    │    not revoked, not expired)               │
                    │  • INSERT sensor_readings (id_session FK,  │
                    │    event_id UNIQUE)                        │
                    └───────────────────┬────────────────────────┘
                                        │
                    ┌───────────────────▼────────────────────────┐
                    │  UI/flow existing                          │
                    │  POST /api/kiosk-session/gejala → Gejala   │
                    │  POST /api/pakar/evaluasi                  │
                    │  POST /api/reconciliation/evaluate         │
                    └────────────────────────────────────────────┘
```

### 13.3 Usulan schema (aditif, perlu persetujuan)

```sql
CREATE TABLE sensor_readings (
  id_reading   BIGINT AUTO_INCREMENT PRIMARY KEY,
  event_id     VARCHAR(64)  NOT NULL,
  device_id    VARCHAR(36)  NOT NULL,
  rfid_uid     VARCHAR(64)  NULL,
  id_session   VARCHAR(36)  NULL,
  NIK          VARCHAR(16)  NULL,
  object_temp  FLOAT        NULL,
  ambient_temp FLOAT        NULL,
  uptime_ms    BIGINT       NULL,
  status       VARCHAR(20)  NOT NULL,   -- ACCEPTED | REJECTED_RANGE | REJECTED_NO_SESSION | REJECTED_UID | REJECTED_PAYLOAD
  reason       VARCHAR(255) NULL,
  raw_payload  TEXT         NULL,
  received_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_sensor_event (event_id),
  KEY idx_sensor_session (id_session),
  KEY idx_sensor_patient_time (NIK, received_at),
  CONSTRAINT fk_sensor_session FOREIGN KEY (id_session) REFERENCES kiosksessions(id_session),
  CONSTRAINT fk_sensor_patient FOREIGN KEY (NIK) REFERENCES Users(NIK)
);
```

Keuntungan: tidak menyentuh tabel existing, idempotensi persisten, audit lengkap (termasuk payload ditolak), `status` memisahkan data sah dari sampah, dan examination final tetap di `Gejala`.

Catatan: `Base.metadata.create_all()` di `app/main.py` L108 akan membuat tabel ini otomatis setelah model ditambahkan — jadi implementasi harus disertai persetujuan dan dokumentasi ERD.

### 13.4 Alternatif yang dipertimbangkan (dan ditolak)

| Alternatif | Alasan ditolak |
| :--- | :--- |
| Ubah firmware: kirim `suhu` | Bekerja, tetapi mengunci kontrak di perangkat yang sulit di-update; melanggar "jangan ubah payload firmware tanpa alasan teknis jelas"; tidak menyelesaikan F-15/F-16 |
| Bridge insert langsung ke `Gejala` tapi dengan cek sesi di DB | Masih melewati backend (no audit, no rate limit, no validasi Pydantic); tetap melanggar aturan "logika bisnis di service" (AGENTS.md §3) |
| Bridge memanggil `POST /api/kiosk-session/gejala` langsung | Membuat 1 `Gejala` per pembacaan — masalah F-15 tetap ada |
| Backend subscribe MQTT in-process (paho di FastAPI) | Menambah dependensi & lifecycle ke app web; restart backend = kehilangan pesan; bridge terpisah lebih tahan banting |

---

## 14. Implementation Plan

Semua langkah di bawah **BELUM dijalankan**. Menunggu persetujuan (§9 prompt / gate di akhir laporan).

### Tahap 0 — Persiapan (tanpa ubah kode)

| # | Aksi | File | Risiko | Rollback |
| :--- | :--- | :--- | :--- | :--- |
| 0.1 | Snapshot DB: `mysqldump db_huawei` ke `backups/` | — | None | restore dump |
| 0.2 | Snapshot repo: `git tag phase5-baseline` | — | None | `git reset --hard` |
| 0.3 | Daftarkan kartu uji `B1056B66` ke pasien nyata via `POST /api/kiosk/identify-rfid`-flow / script | DB (data) | Rendah | hapus baris `patient_cards` |
| 0.4 | Putuskan target deployment (rekomendasi: tetap native) | — | None | — |

### Tahap 1 — Hentikan pendarahan (config only, ≤5 menit)

| # | Aksi | File | Risiko |
| :--- | :--- | :--- | :--- |
| 1.1 | Set `RFID_AUTO_REGISTER=false` | `integrasi_sensor/config.env` (baru) | Rendah — kartu tak terdaftar ditolak (sesuai aturan 5C.6) |
| 1.2 | Set `SUHU_MIN=30.0` | idem | Rendah — 28.17 tidak lagi diterima sebagai suhu tubuh |
| 1.3 | Set `MQTT_SUBSCRIBE_TOPIC=measlescare/sensor/reading` (eksplisit) | idem | Rendah — memperjelas kontrak |
| 1.4 | Pastikan bridge **tidak** dijalankan sampai Tahap 3 selesai | — | None |

### Tahap 2 — Adapter payload + validasi (kode, teruji unit)

| # | Aksi | File | Risiko |
| :--- | :--- | :--- | :--- |
| 2.1 | `normalize_payload()`: `suhu` \|\| `object_temp` \|\| reject; validasi `^[0-9A-F]{4,32}$`; whitelist `device_id` | `mqtt_bridge.py` L38–61 | Rendah (fungsi murni) |
| 2.2 | Alasan penolakan terstruktur (`reason=`) + counter log | idem L191–207 | Rendah |
| 2.3 | `event_id` → kunci idempotensi (fallback hash payload) | idem L204 | Rendah |
| 2.4 | Unit test 2 format payload + 8 kasus tepi (§7.4) | `tests/test_mqtt_bridge.py` (baru) | None |

### Tahap 3 — Layer persistence backend (butuh persetujuan schema)

| # | Aksi | File | Risiko |
| :--- | :--- | :--- | :--- |
| 3.1 | Model `SensorReading` + tabel `sensor_readings` | `app/models/gejala.py` atau `app/models/sensor.py` (baru) | Sedang — `create_all` otomatis |
| 3.2 | Service `ingest_sensor_reading()`: validasi domain, resolve sesi aktif via `_session_from_token`/device binding, UPSERT by `event_id` | `app/services/sensor_service.py` (baru) | Sedang |
| 3.3 | Endpoint `POST /api/kiosk-session/reading` (auth `X-Kiosk-Key`, rate limit) | `app/routers/kiosk_session.py` | Sedang — surface API baru |
| 3.4 | Update `Documentation.md` + `dokumentasi_database_erd.md` | docs | None |

### Tahap 4 — Bridge jadi adapter HTTP

| # | Aksi | File | Risiko |
| :--- | :--- | :--- | :--- |
| 4.1 | Ganti `store_reading()` → `post_reading()` (HTTP ke `127.0.0.1:8000`) | `mqtt_bridge.py` L100–150 | **Sedang** — perilaku berubah total |
| 4.2 | Hapus jalur auto-registrasi & insert `Gejala` | idem L118–150 | Sedang |
| 4.3 | Retry + backoff saat backend down; manual `ack` setelah sukses | idem L191–241 | Rendah |
| 4.4 | `connect_async` + `loop_start` (fix F-12) | idem L241 | Rendah |

### Tahap 5 — Operasional

| # | Aksi | File | Risiko |
| :--- | :--- | :--- | :--- |
| 5.1 | systemd unit `measlescare-bridge.service` (`Restart=always`) | `/etc/systemd/system/` | Rendah |
| 5.2 | Autentikasi broker + ACL per device | `mosquitto.conf`, `passwd` | Sedang |
| 5.3 | Firewall 1883 → hanya ESP32 + localhost | nftables/ufw | Rendah |

**Urutan wajib:** 0 → 1 → 2 → 3 → 4 → 5. Tahap 1 aman dijalankan sendirian (efek: reading ditolak dengan alasan jelas, bukan senyap). Tahap 3 & 4 harus berpasangan; jangan aktifkan 4 sebelum 3 teruji.

---

## 15. Testing Plan

Semua pengujian di bawah **belum dijalankan** (mode read-only). Perintah menggunakan Mosquitto native (bukan `docker compose exec`, karena F-22).

### 15.1 Unit (tanpa hardware, tanpa DB)

```bash
cd /home/orangepi/backend-measlescare
./venv/bin/python -m pytest tests/test_mqtt_bridge.py -v
```

Kasus wajib:
1. Payload ESP32 (`object_temp`) → diterima, `suhu == object_temp`.
2. Payload publisher Python (`suhu`) → tetap diterima (backward compat).
3. `suhu` absen & `object_temp` absen → reject `reason=missing_temp`.
4. `object_temp = 28.17` → reject `reason=out_of_range` (bukan diterima).
5. `rfid_uid = "a"` / `"../../etc"` / unicode → reject `reason=bad_uid`.
6. `device_id = "ESP32_EVIL"` → reject `reason=device_not_allowed`.
7. `event_id` sama dikirim 3× → 1 baris `sensor_readings`.
8. JSON rusak → reject, proses tetap hidup.
9. `ambient_temp` absen → tetap diterima (`ambient` opsional).
10. `uptime_ms` turun (indikasi reboot ESP32) → tercatat, tidak menolak.

### 15.2 Kontrak & topik (dengan broker, tanpa DB)

```bash
# terminal 1: lihat semua pesan
mosquitto_sub -h 127.0.0.1 -p 1883 -t 'measlescare/#' -v

# terminal 2: simulasi ESP32 (payload asli dari brief)
mosquitto_pub -h 127.0.0.1 -p 1883 -q 1 -t 'measlescare/sensor/reading' \
  -m '{"event_id":"4bfed264-11648","device_id":"ESP32_SENSOR_01","rfid_uid":"B1056B66","ambient_temp":27.67,"object_temp":28.17,"uptime_ms":11649}'
```

Harapan setelah Tahap 2–4: `sensor_readings` menerima 1 baris `status=REJECTED_RANGE` (karena 28.17 < 30), **tidak ada** baris `Gejala` baru.

Verifikasi idempotensi: kirim perintah yang sama 5×; `SELECT COUNT(*) FROM sensor_readings WHERE event_id='4bfed264-11648'` = **1**.

### 15.3 Integrasi end-to-end (butuh sesi kiosk aktif)

```bash
# 1) buat sesi (face-verified) -> dapat access_token
curl -s -X POST http://127.0.0.1:8000/api/kiosk-session/identify-face \
  -H "X-Kiosk-Key: <kiosk-key>" -H 'Content-Type: application/json' \
  -d '{"image":"<base64-jpeg>"}'

# 2) kirim reading dengan sesi aktif (bridge melakukannya otomatis)
#    -> sensor_readings.id_session terisi, status=ACCEPTED

# 3) cek tidak ada Gejala otomatis
#    SELECT COUNT(*) FROM Gejala;  -- harus tetap 4

# 4) tutup pemeriksaan lewat jalur existing
curl -s -X POST http://127.0.0.1:8000/api/kiosk-session/gejala \
  -H "X-Kiosk-Session: <token>" -H "X-Kiosk-Key: <kiosk-key>" \
  -H 'Content-Type: application/json' -d '{"Suhu":36.7,"Batuk":"kering"}'
#    -> 1 baris Gejala baru (5 total)

# 5) evaluasi
curl -s -X POST http://127.0.0.1:8000/api/reconciliation/evaluate ...
```

### 15.4 Matriks skenario (acceptance)

| # | Skenario | Ekspektasi |
| :--- | :--- | :--- |
| T1 | ESP32 publish, tidak ada sesi aktif | `sensor_readings` status `REJECTED_NO_SESSION`; `Gejala` tidak bertambah |
| T2 | ESP32 publish, sesi aktif | `ACCEPTED`, `id_session` terisi |
| T3 | Kartu tidak terdaftar | `REJECTED_UID`; **tidak ada** `Users`/`patient_cards` baru |
| T4 | `object_temp` 28.17 | `REJECTED_RANGE` |
| T5 | `object_temp` 36.7 | `ACCEPTED`, `NIK` dari sesi (bukan dari kartu) |
| T6 | Replay payload sama 5× | 1 baris (idempotent) |
| T7 | Broker restart saat bridge jalan | Bridge reconnect otomatis, tidak ada pesan hilang (persistent session) |
| T8 | Backend down 30 detik | Bridge retry, tidak crash, reading masuk setelah backend hidup |
| T9 | Bridge restart | Tidak ada duplikat (event_id di DB) |
| T10 | `device_id` asing | `REJECTED_DEVICE` |
| T11 | Reboot host | Bridge & backend auto-start, tidak ada kehilangan data |

### 15.5 Verifikasi tanpa mengganggu produksi

- Semua uji manual pakai `mosquitto_pub` (simulasi), **bukan** menyalakan ESP32 fisik berulang.
- Uji DB di database terpisah (`db_huawei_test`) bila memungkinkan; jika tidak, snapshot dulu (Tahap 0.1).
- `GET /api/gejala/history` dipakai untuk memverifikasi tidak ada penambahan baris tak terduga.

---

## 16. Rollback Strategy

### 16.1 Titik rollback

| Lapis | Aksi | Waktu |
| :--- | :--- | :--- |
| Kode | `git tag phase5-baseline` (sebelum Tahap 2); `git reset --hard phase5-baseline` | < 1 menit |
| Config | Kembalikan `integrasi_sensor/config.env` ke nilai awal (`RFID_AUTO_REGISTER=true`, `SUHU_MIN=25.0`) atau hapus file (default lama berlaku) | < 1 menit |
| DB schema | `DROP TABLE sensor_readings` (aditif → drop aman, 0 dampak ke tabel existing) | < 1 menit |
| DB data | `mysql db_huawei < backups/phase5_baseline.sql` | 1–2 menit |
| Proses | `systemctl disable --now measlescare-bridge` → kembali ke mode manual | < 1 menit |
| Broker | Kembalikan `allow_anonymous true` di `measlescare.conf` + `systemctl restart mosquitto` | < 1 menit |
| Firmware | **Tidak ada perubahan** → tidak perlu rollback | — |

### 16.2 Kriteria pembatalan (abort trigger)

Hentikan dan rollback bila salah satu terjadi:
1. Bridge crash-loop > 3× dalam 5 menit.
2. `Gejala` bertambah tanpa aksi eksplisit pengguna (regresi F-15).
3. `Users` atau `patient_cards` bertambah otomatis (regresi F-16).
4. ESP32 berhenti publish setelah perubahan autentikasi broker.
5. Latensi `POST /api/kiosk-session/reading` > 500 ms p95 (host 2 GB).
6. RAM tersisa < 150 MB (host hanya 2 GB; jangan tambahkan container).

### 16.3 Sifat perubahan (mengapa rollback murah)

- Semua perubahan bridge bersifat **penggantian satu fungsi** (`store_reading` → `post_reading`) dalam satu file.
- Schema hanya **aditif** (1 tabel baru, 0 kolom diubah, 0 constraint existing disentuh).
- Firmware **tidak diubah**.
- Jalur `Gejala` existing (`/api/kiosk-session/gejala`) **tidak diubah** — tetap berfungsi selama transisi.
- Auto-registrasi dimatikan lewat env, bukan penghapusan kode → bisa dinyalakan lagi dalam 1 baris bila ada kebutuhan demo.

---

## 17. Ringkasan untuk Approval Gate

1. **Kondisi sistem:** backend FastAPI sehat (34 route, DB MariaDB 10.6 native, 4/3/4/0/1 baris di Users/patient_cards/Gejala/kiosksessions/kioskdevices). Broker native aktif. **Tidak ada Docker.** Bridge & publisher **tidak berjalan**.
2. **Masalah utama:** payload ESP32 ditolak 100% (terbukti), bridge menulis langsung ke `Gejala` tanpa sesi, auto-registrasi pasien, broker anonim, ambang suhu tidak konsisten, tidak ada tabel telemetri.
3. **Rencana:** 6 tahap (§14), mulai dari config aman → adapter payload → layer persistence backend → bridge sebagai adapter HTTP → operasional.
4. **File yang perlu diubah:** `integrasi_sensor/bridge/mqtt_bridge.py`, `integrasi_sensor/config.env` (baru), `app/models/*` (baru: sensor), `app/services/sensor_service.py` (baru), `app/routers/kiosk_session.py`, `tests/test_mqtt_bridge.py` (baru), `Documentation.md`, `dokumentasi_database_erd.md`, systemd unit (baru).
5. **Risiko:** sedang untuk perubahan perilaku bridge & endpoint baru; semua rollback ≤ 2 menit; firmware tidak disentuh.
6. **Rollback:** git tag + dump SQL + drop 1 tabel aditif + disable 1 service (§16).

**Menunggu persetujuan eksplisit sebelum implementasi. Tidak ada perubahan yang dilakukan pada audit ini.**
