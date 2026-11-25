# PHASE 5.1 FINAL REVIEW — systemd Unit Files

**Tanggal:** 20 November 2026
**Mode:** READ-ONLY — tidak ada proses dihentikan, tidak ada unit diubah/dibuat, tidak ada sudo, tidak ada enable/start/reboot. Dokumen ini hanya hasil inspeksi.

---

## 1. Temuan Kritikal Sebelum Review

1. **`deploy/measlescare-backend.service` BELUM ADA di disk.** Yang ada hanya proposal di `PHASE_5_1_SERVICE_STABILIZATION_PLAN.md` §6. Isi di bawah adalah PROPOSAL, ditandai jelas sebagai "belum dibuat". Deployment TIDAK boleh dilakukan sebelum file ini benar-benar ditulis.
2. **`deploy/measlescare-bridge.service` masih template lama** (masih menyertakan `mariadb.service`, belum ada `Group=`, belum ada `TimeoutStopSec`). Isi disk ditampilkan di §3; versi yang akan dideploy (diusulkan) di §5.
3. **`pgrep -f` menghasilkan false positive** pada proses ini (terbukti saat audit: pola `main.py`/`mqtt_bridge` ikut mencocokkan shell wrapper agent `bash -c ...` dengan PID 77668/77680/77694). Identifikasi PID harus memakai metode yang lebih tegas (§9).

---

## 2. Verifikasi Path & Lingkungan (fakta terukur)

| Item | Hasil |
| :-- | :-- |
| venv python | `venv/bin/python -> python3 -> /usr/bin/python3` (ada; backend & bridge SEDANG berjalan dengan path ini → valid) |
| Brief `/home/orangepi/venv` | **TIDAK ADA** — jangan dipakai |
| Modul bridge importable | `integrasi_sensor.bridge.mqtt_bridge` → `True` |
| cwd proses live | `/home/orangepi/backend-measlescare` |
| User proses live | `orangepi` (uid 1000, gid 1000) |
| `config.env` permission | `-rw-------` (600, milik orangepi) |
| Proses backend live | PID 69553 `./venv/bin/python main.py` (parent), child 69578 |
| Proses bridge live | PID 72105 `./venv/bin/python -m integrasi_sensor.bridge.mqtt_bridge --verbose` |

---

## 3. Isi File Saat Ini — deploy/measlescare-bridge.service (DI DISK)

```ini
[Unit]
Description=MeaslesCare MQTT Bridge (sensor -> backend)
After=network.target mosquitto.service mariadb.service
Wants=mosquitto.service mariadb.service

[Service]
Type=simple
User=orangepi
WorkingDirectory=/home/orangepi/backend-measlescare
ExecStart=/home/orangepi/backend-measlescare/venv/bin/python -m integrasi_sensor.bridge.mqtt_bridge
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

---

## 4. Isi File Diusulkan — deploy/measlescare-backend.service (BELUM DIBUAT)

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

---

## 5. Isi File Diusulkan — deploy/measlescare-bridge.service (UPDATE dari disk)

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

---

## 6. Audit Poin-Demi-Poin

### 6.1 Validitas ExecStart & path venv
- Backend `ExecStart=.../venv/bin/python main.py` → **VALID**. Persis command proses yang berjalan sekarang (PID 69553), cwd repo, bind 127.0.0.1:8000 via `uvicorn.run()` di `main.py`.
- Bridge `ExecStart=.../venv/bin/python -m integrasi_sensor.bridge.mqtt_bridge` → **VALID**. Persis command proses bridge (PID 72105); modul importable.
- Path venv `/home/orangepi/backend-measlescare/venv/bin/python` → **VALID** (ada, terpakai live). Path brief `/home/orangepi/venv` **salah** dan tidak boleh dipakai.

### 6.2 WorkingDirectory / User / Group
- Keduanya `WorkingDirectory=/home/orangepi/backend-measlescare` → benar (wajib: `main.py` di root repo; bridge load `config.env` relatif repo).
- Backend: `User=orangepi` + `Group=orangepi` → benar (gid 1000).
- Bridge (disk): **belum ada `Group=`** → ditambahkan di versi usulan.

### 6.3 Requires / Wants / After
- Backend: `Requires`+`After=mariadb.service` → benar (startup backend butuh DB: create_all/migrate/seed). Catatan minor: `Wants=mariadb.service` **redundan** karena `Requires` sudah mengimplikasikan pull-in; tidak membatalkan, hanya pembersihan kosmetik.
- Bridge (disk): `After/Wants=... mariadb.service` → **salah/kadaluwarsa**; bridge adalah adapter HTTP (tidak import `app.db.session`, tidak menulis DB) → dihapus di versi usulan.
- Bridge (usulan): `Wants/After=mosquitto.service` (perlu) + `Wants/After=measlescare-backend.service` (soft). Tidak ada siklus: backend tidak mereferensikan bridge.

### 6.4 Restart / RestartSec
- Backend `Restart=always`, `RestartSec=5` → tepat; StartLimit default systemd mencegah tight-loop.
- Bridge `Restart=always`, `RestartSec=3` → tepat.

### 6.5 Logging (journald)
- Keduanya `Type=simple`, log stdout/stderr → otomatis ke journald. Tidak perlu `StandardOutput=` tambahan.
- Akses: `journalctl -u measlescare-backend -f` / `-u measlescare-bridge -f`.

### 6.6 Mekanisme retry bridge saat backend belum siap
**ADA dan terverifikasi di kode** (`integrasi_sensor/bridge/mqtt_bridge.py`):
- HTTP retry: `for _attempt in range(4)` (L154) dengan backoff eksponensial (`delay = min(delay*2, 30)`, L188); `_is_retryable` (L138) menganggap 401/403/404/422 permanen (tidak retry), error koneksi/timeout diretry.
- MQTT reconnect: `reconnect_delay_set(min_delay=1, max_delay=30)` (L281) + `connect_async` (L284) + `loop_start` (L285) → tahan broker belum siap.
- Kesimpulan: bridge **tidak wajib** backend siap lebih dulu; `After=measlescare-backend.service` adalah preferensi urutan, bukan syarat keras.

### 6.7 Konfigurasi aman / tidak mengekspos secret
- Unit backend: hanya path & flag; **tidak ada** secret.
- Unit bridge: **tanpa `EnvironmentFile`** — bridge memuat `config.env` (600) sendiri via `load_dotenv`, sehingga `KIOSK_API_KEY` tidak masuk unit/env systemd dan tidak dicatat journald.
- Catatan di luar unit: `config.py` menanam `SECRET_KEY="change-me"` dan kredensial DB tersamar di source — utang teknis terpisah, bukan isu unit file ini.

---

## 7. Perbedaan yang WAJIB diterapkan sebelum deploy

| # | File | Perubahan |
| :-- | :-- | :-- |
| 1 | backend unit | **Buat file** (belum ada) dari §4 |
| 2 | bridge unit | Hapus `mariadb.service` dari `After`/`Wants` |
| 3 | bridge unit | Tambah `Group=orangepi` |
| 4 | bridge unit | Tambah `TimeoutStopSec=20` |
| 5 | bridge unit | Tambah `Wants/After=measlescare-backend.service` (soft) |

---

## 8. Simulasi Urutan Deployment yang Aman

### 8.1 Identifikasi PID lama (tanpa false positive)

**Backend — via PORT (paling tegas):**
```bash
ss -tlnp | grep ':8000'
# -> LISTEN ... users:(("python",pid=69553,fd=3),("python",pid=69578,fd=3))
# pid pemegang port = 69553 (child 69578 berbagi fd)
```

**Bridge — via comm=python + filter arg (bukan `pgrep -f`):**
```bash
ps -eo pid,user,comm,args | grep -F 'integrasi_sensor.bridge.mqtt_bridge' | grep -v -F 'bash'
# -> hanya baris python asli (cmdline dimulai path python, bukan /usr/bin/bash)
```

PENTING — jangan `pkill -f`/`pgrep -f`: audit membuktikan pola `main.py`/`mqtt_bridge` ikut mencocokkan shell wrapper agent (`bash -c ...`, PID 77668/77680/77694), sehingga berisiko menghentikan proses yang tidak terkait.

### 8.2 Verifikasi tiap PID sebelum kill
```bash
readlink /proc/<PID>/cwd      # harus /home/orangepi/backend-measlescare
ps -o user= -p <PID>          # harus orangepi
tr '\0' ' ' < /proc/<PID>/cmdline   # harus persis ./venv/bin/python main.py / ...mqtt_bridge
```

### 8.3 Urutan lengkap (simulasi — TIDAK dieksekusi)
```
1. sudo cp deploy/measlescare-backend.service /etc/systemd/system/     (setelah file dibuat)
2. sudo cp deploy/measlescare-bridge.service  /etc/systemd/system/     (setelah di-update)
3. sudo systemctl daemon-reload
4. Hentikan proses lama (urutan: bridge dulu agar tidak sempat publish saat backend mati):
     kill <PID-bridge>        # SIGTERM
     kill <PID-backend>       # 69553, lalu child 69578 bila masih hidup
     sleep 3
     ss -tlnp | grep ':8000'  # pastikan bebas; ps -ef | grep mqtt_bridge | grep -v grep # pastikan kosong
5. sudo systemctl enable --now measlescare-backend
6. sudo systemctl enable --now measlescare-bridge
7. Verifikasi:
     systemctl is-active measlescare-backend measlescare-bridge
     curl -s http://127.0.0.1:8000/
     journalctl -u measlescare-bridge -n 10 --no-pager
```
Catatan: `kill` adalah SIGTERM; `kill -9` hanya bila proses tidak berhenti dalam ~5 detik. Jangan `pkill -f`.

---

## 9. Risiko & Downtime

| Risiko | Level | Mitigasi |
| :-- | :-- | :-- |
| Backend unit belum dibuat → deploy gagal | Blocker | Buat file dulu (§7 #1) |
| `pgrep -f` salah target | Tinggi | Pakai metode §8.1 + verifikasi §8.2 |
| Bentrok port 8000 (proses lama belum mati) | Sedang | Stop lama SEBELUM start service; verifikasi port bebas |
| Bridge ganda (lama + systemd) | Sedang | Stop bridge lama SEBELUM enable |
| Restart backend = seed/create_all di startup | Rendah | Idempoten (sudah ada); tidak mengubah data |
| Downtime | — | < 30 detik (jeda stop lama → start systemd) |

---

## 10. REKOMENDASI AKHIR

**NO-GO untuk deploy SEKARANG**, dengan alasan teknis spesifik:

1. `deploy/measlescare-backend.service` **belum ada di disk** — hanya proposal. Deploy akan gagal di langkah `cp`.
2. `deploy/measlescare-bridge.service` di disk masih **template lama** (dependensi `mariadb.service` kadaluwarsa, tanpa `Group=`/`TimeoutStopSec`).

Setelah dua file tersebut ditulis/diperbarui persis sesuai §4 dan §5, rekomendasi berubah menjadi **GO** — seluruh audit teknis lain (path venv, ExecStart, User/Group/WorkingDirectory, Requires/Wants/After, Restart/RestartSec, journald, retry bridge, non-ekspos secret) lolos.

**Urutan agar menjadi GO:** (1) saya tulis `deploy/measlescare-backend.service` dari §4, (2) saya perbarui `deploy/measlescare-bridge.service` ke §5, (3) Anda menjalankan perintah sudo di §8.3 (dengan metode identifikasi PID §8.1–§8.2), (4) saya verifikasi pasca-deploy.

*Dokumen ini dihasilkan dari inspeksi read-only; tidak ada file, proses, atau service yang diubah.*
