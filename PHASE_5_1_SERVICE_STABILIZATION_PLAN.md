# PHASE 5.1 SERVICE STABILIZATION PLAN — Production Service Stabilization & Operational Readiness

**Proyek:** MeaslesCare
**Platform:** Orange Pi 4 Pro (Ubuntu, kernel 6.6.98-sun60iw2)
**Repo:** `/home/orangepi/backend-measlescare`
**Mode:** READ-ONLY AUDIT & PLANNING — tidak ada proses dihentikan, tidak ada unit systemd diubah/dibuat, tidak ada service di-start/stop, tidak ada kode/config diubah, tidak ada reboot. Artefak satu-satunya adalah dokumen ini.

> Kredensial: seluruh password, secret, token, dan API key tidak ditampilkan di dokumen ini.

---

## 1. Executive Summary

Phase 5 (MQTT Bridge & FastAPI) sudah terverifikasi end-to-end. Saat ini backend FastAPI dan MQTT Bridge berjalan sebagai **background process milik sesi agent sebelumnya**, bukan systemd service. Akibatnya: (a) tidak auto-start saat reboot, (b) tidak auto-restart saat crash, (c) bisa ikut mati saat sesi berakhir.

**Tujuan Phase 5.1:** jadikan backend + bridge sebagai systemd service yang persisten, tanpa mengubah logika bisnis Phase 5 yang sudah terverifikasi, tanpa Docker, tanpa mengubah schema/kode aplikasi.

**Temuan kunci audit:**
1. **Lokasi venv di brief salah.** Brief menyebut `/home/orangepi/venv`, kenyataannya venv berada di `/home/orangepi/backend-measlescare/venv` (`/home/orangepi/venv` tidak ada). Unit file harus memakai path yang benar.
2. Backend berjalan via `python main.py` (bukan `uvicorn` CLI langsung) dari root repo, bind `127.0.0.1:8000`, tanpa `--reload`, tanpa `--workers`.
3. Bridge berjalan via `python -m integrasi_sensor.bridge.mqtt_bridge` (saat ini dengan `--verbose`; unit produksi akan tanpa `--verbose`).
4. MariaDB & Mosquitto sudah `active` + `enabled` (native systemd).
5. **Tidak ada** unit systemd apa pun untuk backend/bridge; tidak ada supervisor/pm2/forever.
6. Template `deploy/measlescare-bridge.service` sudah ada dan mendekati benar, tetapi (a) masih menyertakan dependensi `mariadb.service` yang tidak lagi dibutuhkan bridge (bridge adalah adapter HTTP, tidak menulis DB), (b) belum punya `Group=`, (c) belum punya `TimeoutStopSec`.

**Rencana:** buat 2 unit systemd (`measlescare-backend.service` baru + `measlescare-bridge.service` disempurnakan), hentikan proses background lama, lalu enable+start kedua service. Seluruh langkah `sudo` dijalankan oleh user (sudo membutuhkan password).

---

## 2. Current Process Inventory (audit live)

| Proses | PID | Parent | Cmdline | cwd | User | Port |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| FastAPI backend (parent) | 69553 | 41084 (sesi agent) | `./venv/bin/python main.py` | `/home/orangepi/backend-measlescare` | orangepi (1000) | 127.0.0.1:8000 |
| FastAPI (child multiprocessing) | 69578 | 69553 | `.../python -c from multiprocessing.spawn ...` | — | orangepi | (berbagi 8000) |
| MQTT Bridge | 72105 | 41084 (sesi agent) | `./venv/bin/python -m integrasi_sensor.bridge.mqtt_bridge --verbose` | `/home/orangepi/backend-measlescare` | orangepi | — |
| Mosquitto | (systemd) | 1 | `/usr/sbin/mosquitto -c /etc/mosquitto/mosquitto.conf` | — | mosquitto | 0.0.0.0:1883 |
| MariaDB | (systemd) | 1 | mariadbd | — | mysql | 127.0.0.1:3306 |

Catatan: PID adalah referensi historis — **selalu inspeksi ulang sebelum mengeksekusi**. Backend & bridge adalah child dari sesi agent sebelumnya (ppid 41084) sehingga berisiko mati saat sesi berakhir.

---

## 3. Existing Service Audit

| Unit systemd | Status | Enabled | Catatan |
| :-- | :-- | :-- | :-- |
| `mariadb.service` | active | enabled | Native, `127.0.0.1:3306` |
| `mosquitto.service` | active | enabled | Native, `0.0.0.0:1883`, `allow_anonymous true` (lab) |
| `supervisor.service` | inactive | — | Tidak dipakai |
| `measlescare-*` / `huawei-*` / `*-backend` / `*-bridge` | — | — | **Tidak ada** |

Process manager lain (supervisor/pm2/forever): **tidak ada**. Tidak ada potensi bentrok unit systemd.

---

## 4. Backend Startup Command Verification

- Entry point terverifikasi: `app/main.py`, blok `if __name__ == "__main__"` menjalankan:
  ```python
  uvicorn.run(app, host="127.0.0.1", port=8000)
  ```
- **Tidak** ada `--reload` (mode produksi), **tidak** ada `--workers` (single process; child multiprocessing yang teramati berasal dari library, bukan uvicorn worker).
- ASGI import path: `app.main:app` (objek FastAPI `app`).
- Interpreter: `/home/orangepi/backend-measlescare/venv/bin/python` (venv repo, BUKAN `/home/orangepi/venv`).
- WorkingDirectory: `/home/orangepi/backend-measlescare` (wajib, karena `main.py` di-root repo dan `load_dotenv()` membaca `.env` relatif cwd).
- Environment: proses berjalan **tanpa** env tambahan (tidak ada `DATABASE_URL`/`SECRET_KEY` di environ) — mengandalkan default di `app/core/config.py`. `.env` root **tidak ada**.
- Health: `GET http://127.0.0.1:8000/` → `200 {"status":"ok","app":"Huawei ICT Backend"}`.

Kesimpulan: command faithful untuk unit = `python main.py` (bukan `uvicorn` CLI), cwd = repo, venv = repo/venv.

---

## 5. MQTT Bridge Startup Command Verification

- Module entry point: `integrasi_sensor.bridge.mqtt_bridge` (dijalankan `python -m`).
- Bridge memuat konfigurasi sendiri dari `integrasi_sensor/config.env` (via `load_dotenv`, `override=False`), berisi `MQTT_HOST/PORT`, `MQTT_SUBSCRIBE_TOPIC=measlescare/+/reading`, `BACKEND_URL=http://127.0.0.1:8000`, `KIOSK_API_KEY` (secret perangkat kiosk, chmod 600).
- Bridge **tidak** menulis DB (adapter HTTP tipis → `POST /api/kiosk-session/reading`); jadi tidak butuh dependensi MariaDB.
- Bridge butuh Mosquitto (MQTT) dan Backend (HTTP, dengan retry+backoff sehingga tahan backend down).
- Mode produksi: **tanpa** `--verbose` (saat ini proses berjalan `--verbose`; unit akan non-verbose → level INFO).

---

## 6. Proposed Backend systemd Unit

Nama: `measlescare-backend.service` (baru).

```ini
[Unit]
Description=MeaslesCare FastAPI Backend
After=network.target mariadb.service
Requires=mariadb.service
Wants=mariadb.service

[Service]
Type=simple
User=orangepi
Group=orangepi
WorkingDirectory=/home/orangepi/backend-measlescare
ExecStart=/home/orangepi/backend-measlescare/venv/bin/python main.py
Restart=always
RestartSec=5
TimeoutStopSec=30
KillMode=mixed

[Install]
WantedBy=multi-user.target
```

Rasional:
- `Requires`+`After` mariadb: backend butuh DB saat startup (create_all + migrate + seed); urutan & dependensi keras.
- `Restart=always` + `RestartSec=5`: auto-restart tanpa tight-loop (systemd StartLimit default membatasi burst).
- `KillMode=mixed` + `TimeoutStopSec=30`: SIGTERM ke main process (menghentikan child multiprocessing) lalu tunggu.
- Tanpa `--reload`/`--workers`: reproduksi persis mode produksi terverifikasi.

---

## 7. Proposed Bridge systemd Unit

Nama: `measlescare-bridge.service` (penyempurnaan template existing).

```ini
[Unit]
Description=MeaslesCare MQTT Bridge (sensor -> backend)
After=network.target mosquitto.service measlescare-backend.service
Wants=mosquitto.service
Wants=measlescare-backend.service

[Service]
Type=simple
User=orangepi
Group=orangepi
WorkingDirectory=/home/orangepi/backend-measlescare
ExecStart=/home/orangepi/backend-measlescare/venv/bin/python -m integrasi_sensor.bridge.mqtt_bridge
Restart=always
RestartSec=3
TimeoutStopSec=20

[Install]
WantedBy=multi-user.target
```

Perbedaan vs template existing:
1. Hapus `mariadb.service` dari `After`/`Wants` (bridge tidak lagi menulis DB).
2. Tambah `Group=orangepi`.
3. Tambah `TimeoutStopSec=20`.
4. Tambah `Wants`+`After` `measlescare-backend.service` (soft — bridge punya retry, jadi tidak wajib backend siap lebih dulu; tetap diekspresikan untuk urutan boot yang rapi).
5. `ExecStart` tanpa `--verbose` (produksi).

Catatan: bridge memuat `config.env` sendiri (tidak butuh `EnvironmentFile`), sehingga `KIOSK_API_KEY` tidak pernah masuk unit file atau environment systemd.

---

## 8. Environment Configuration

Kondisi saat ini:
- Backend: **tanpa** `.env` root; memakai default `app/core/config.py` (berisi `DATABASE_URL` default — kredensial DB tersamar — dan `SECRET_KEY="change-me"`).
- Bridge: `integrasi_sensor/config.env` (chmod 600, milik orangepi) dibaca sendiri oleh bridge.

Keputusan untuk Phase 5.1 (konservatif, tidak mengubah perilaku terverifikasi):
- Unit backend **tidak** memakai `EnvironmentFile` — mereproduksi persis state yang sedang berjalan (default config.py). Tidak menyentuh kredensial DB yang tersamar.
- Unit bridge **tidak** memakai `EnvironmentFile` — bridge memuat `config.env` sendiri.

Rekomendasi lanjutan (TERPISAH, butuh approval sendiri karena menyentuh konfigurasi): pindahkan `DATABASE_URL` + `SECRET_KEY` ke file env terproteksi dan set `SECRET_KEY` acak yang kuat (saat ini `change-me`). Tidak dikerjakan di Phase 5.1.

---

## 9. Logging Architecture

Gunakan **systemd journal** (default) — kedua service log ke stdout/stderr, ditangkap journald.

| Service | Akses log |
| :-- | :-- |
| Backend | `journalctl -u measlescare-backend -f` (live), `-e` (tail), `--since today` |
| Bridge | `journalctl -u measlescare-bridge -f` |
| Startup failure | `systemctl status measlescare-backend` / `journalctl -u measlescare-backend -b` |
| Restart count | `systemctl show measlescare-backend -p NRestarts` |

Perintah inspeksi lain:
```bash
journalctl -u measlescare-backend -n 50 --no-pager
journalctl -u measlescare-bridge -n 50 --no-pager
systemctl show measlescare-backend -p NRestarts -p ActiveState -p SubState
```

Aturan no-secret di log:
- Bridge tidak mencatat `KIOSK_API_KEY`, password, atau token sesi (hanya status/reason/counter).
- Backend saat startup mencatat `admin`/`admin123` ke stdout **hanya bila** membuat akun admin baru (saat ini admin sudah ada → tidak akan tercetak lagi). Dicatat sebagai utang teknis di §13.

---

## 10. Startup Dependency Design

```
mariadb.service ──(Requires/After)──► measlescare-backend.service
mosquitto.service ──(Wants/After)───► measlescare-bridge.service
measlescare-backend.service ──(Wants/After, soft)──► measlescare-bridge.service
```

- Tidak ada dependensi sirkular.
- Backend tahan MariaDB belum siap: `Restart=always` + `RestartSec=5` mencoba ulang sampai DB siap.
- Bridge tahan backend/broker belum siap: worker bridge retry HTTP + `connect_async`+`loop_start` untuk MQTT; `Restart=always`.
- Bridge memakai `client_id` acak per start (tidak ada session MQTT persisten), sehingga tidak ada duplicate subscription lintas restart — idempotensi event_id di DB tetap menjadi pengaman duplikat.

---

## 11. Recovery Strategy

| Skenario | Perilaku |
| :-- | :-- |
| Backend crash | systemd `Restart=always` → hidup ulang; `RestartSec=5` mencegah tight-loop |
| Bridge crash | systemd `Restart=always` → hidup ulang; `RestartSec=3` |
| MariaDB down sementara | Backend gagal startup → retry otomatis sampai DB siap |
| Mosquitto down sementara | Bridge reconnect otomatis (paho `reconnect_delay_set` 1–30s) |
| Backend down (bridge tetap jalan) | Bridge retry HTTP eksponensial (1→2→4→8s, max 30s), tidak crash |
| Reboot | `WantedBy=multi-user.target` → keduanya auto-start; urutan via `After` |
| Duplikat proses | systemd adalah satu-satunya pemilik; proses background lama WAJIB dihentikan sebelum enable (lihat §14) |

---

## 12. Testing Matrix

| # | Uji | Perintah | Hasil diharapkan |
| :-- | :-- | :-- | :-- |
| 1 | Backend start | `sudo systemctl start measlescare-backend` + `curl -s localhost:8000/` | `{"status":"ok",...}` |
| 2 | Bridge start | `sudo systemctl start measlescare-bridge` + `journalctl -u measlescare-bridge -n 5` | log `subscribed: measlescare/+/reading` |
| 3 | Tahan terminal | tutup semua terminal agent | keduanya tetap `active` (dimiliki systemd) |
| 4 | Tahan sesi agent | akhiri sesi agent | keduanya tetap `active` |
| 5 | Auto-restart | `sudo systemctl kill -s KILL measlescare-backend` | `active` lagi ≤5s, `NRestarts` naik |
| 6 | No dup backend | `pgrep -fc 'main.py'` | 1 (hanya proses systemd) |
| 7 | No dup bridge | `pgrep -fc 'mqtt_bridge'` | 1 |
| 8 | MQTT jalan | `mosquitto_sub -h 127.0.0.1 -t 'measlescare/#' -C 1` | pesan diterima |
| 9 | DB jalan | `mysqladmin ping` (atau query ORM) | `mysqld is alive` |
| 10 | ESP32 publish | `mosquitto_pub ... -t measlescare/sensor/reading -m '<payload>'` | baris `sensor_readings` bertambah |
| 11 | API endpoint | `curl localhost:8000/api/gejala/history` (dengan auth) | 200/401 terstruktur |
| 12 | Log accessible | `journalctl -u measlescare-backend -n 5` | log terbaca |

**Uji reboot (#3-#4 pada level reboot penuh) HANYA dijalankan setelah user menyetujui secara eksplisit.**

---

## 13. Security Considerations

1. Unit `User=orangepi` (bukan root) — least privilege.
2. `KIOSK_API_KEY` tidak pernah masuk unit/env systemd (bridge memuat `config.env` chmod 600 sendiri); tidak dicatat di journal.
3. Backend bind `127.0.0.1` (loopback) — tidak terekspos ke LAN; tidak berubah.
4. Mosquitto masih `allow_anonymous true` (kondisi lab) — di luar scope Phase 5.1; dicatat sebagai risiko berlanjut.
5. Utang teknis (tidak dikerjakan): `SECRET_KEY="change-me"` di `config.py`; kredensial DB tersamar tertanam di source; startup mencetak password admin default hanya saat pembuatan akun pertama (tidak akan terulang karena admin sudah ada).
6. `RestartSec` + StartLimit default systemd mencegah restart-loop berlebihan.

---

## 14. Exact Deployment Commands

Semua blok `sudo` dijalankan oleh **user** (sudo membutuhkan password).

Langkah 1 — siapkan file unit (tanpa sudo, saya yang buat saat eksekusi):
```bash
cd /home/orangepi/backend-measlescare
# unit backend -> deploy/measlescare-backend.service
# unit bridge  -> deploy/measlescare-bridge.service (perbarui)
```

Langkah 2 — install unit (sudo):
```bash
sudo cp deploy/measlescare-backend.service /etc/systemd/system/
sudo cp deploy/measlescare-bridge.service /etc/systemd/system/
sudo systemctl daemon-reload
```

Langkah 3 — hentikan proses background lama (hindari `pkill -f`; gunakan PID spesifik / pipeline `grep -v grep`):
```bash
# backend
ps -ef | grep '[m]ain.py' | awk '{print $2}' | xargs -r kill
# bridge
ps -ef | grep '[m]qtt_bridge' | awk '{print $2}' | xargs -r kill
sleep 3
ss -tlnp | grep ':8000' && echo "MASIH ADA - periksa" || echo "port 8000 bebas"
```
(Catatan: `grep '[m]ain.py'` menghindari self-match tanpa `pkill -f`.)

Langkah 4 — enable + start (sudo):
```bash
sudo systemctl enable --now measlescare-backend
sudo systemctl enable --now measlescare-bridge
```

Langkah 5 — verifikasi:
```bash
systemctl is-active measlescare-backend measlescare-bridge
curl -s http://127.0.0.1:8000/
journalctl -u measlescare-bridge -n 10 --no-pager
```

Urutan WAJIB: install → daemon-reload → **hentikan proses lama** → start (jangan start sebelum proses lama mati, agar tidak ada bentrok port 8000 / bridge ganda).

Perkiraan downtime: < 30 detik (jeda antara kill proses lama dan start service).

---

## 15. Rollback Procedure

Kembalikan ke mode proses-manual (state sebelum Phase 5.1):

```bash
# 1. stop + disable service
sudo systemctl disable --now measlescare-backend measlescare-bridge

# 2. hapus unit
sudo rm /etc/systemd/system/measlescare-backend.service
sudo rm /etc/systemd/system/measlescare-bridge.service
sudo systemctl daemon-reload

# 3. jalankan ulang manual (seperti semula)
cd /home/orangepi/backend-measlescare
nohup ./venv/bin/python main.py > /tmp/measlescare_backend.log 2>&1 &
nohup ./venv/bin/python -m integrasi_sensor.bridge.mqtt_bridge > /tmp/measlescare_bridge.log 2>&1 &
```

Tidak ada perubahan kode/config/schema dalam Phase 5.1, sehingga rollback murni operasional (unit file + proses). Backup: `deploy/` unit file tertinggal di repo sebagai sumber pemulihan.

---

## 16. Approval Checklist

**APPROVAL GATE — DEPLOYMENT (dibutuhkan sebelum menulis unit ke /etc/systemd/system, enable, start, stop proses lama, atau reboot):**

- [ ] Menyetujui unit `measlescare-backend.service` (§6).
- [ ] Menyetujui unit `measlescare-bridge.service` (§7), termasuk penghapusan dependensi mariadb.
- [ ] Menyetujui urutan deployment §14 (termasuk menghentikan proses background lama 69553/69578/72105).
- [ ] Menyetujui estimasi downtime < 30 detik.
- [ ] Menyetujui bahwa perintah `sudo` (§14) dijalankan oleh user (saya siapkan file + verifikasi).
- [ ] Menyetujui rollback procedure (§15).
- [ ] (Opsional) Menyetujui uji reboot setelah service aktif.

**Status: BELUM ada yang dieksekusi. Menunggu persetujuan eksplisit.**

---

*Dokumen ini dihasilkan dari audit read-only terhadap proses, unit systemd, entry point, dan dependensi yang berjalan. Tidak ada perubahan yang dilakukan.*
