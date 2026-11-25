# PHASE 5.1 — UNIT FILES REPORT (TAHAP A: PREPARATION)

**Proyek:** MeaslesCare — Orange Pi 4 Pro
**Repo:** `/home/orangepi/backend-measlescare`
**Tanggal:** 20 November 2026
**Mode:** TAHAP A (preparation). Tidak ada `sudo`, tidak ada penyalinan ke `/etc/systemd/system/`, tidak ada `daemon-reload`, tidak ada start/stop/enable service, tidak ada reboot, tidak ada perubahan database/schema/business logic.
**Status gate:** MENUNGGU PERSETUJUAN EKSPLISIT PENGGUNA sebelum Tahap B (deployment).

---

## 1. Ringkasan Pekerjaan

| Item | Status |
| :-- | :-- |
| `deploy/measlescare-backend.service` | **DIBUAT** (710 byte) |
| `deploy/measlescare-bridge.service` | **DIPERBARUI** dari template lama (759 byte) |
| `main.py` | **DIUBAH MINIMAL**: `reload=True` hardcoded → `reload=os.getenv("UVICORN_RELOAD","0")=="1"` (default `False`). Lihat §1.1 — ini wajib, alasannya di bawah. |
| Validasi sintaks unit (`systemd-analyze verify`) | **LULUS** (exit 0) |
| Validasi import di environment bersih (simulasi systemd) | **LULUS** (backend & bridge) |
| Validasi dependency/urutan startup | **LULUS**, tanpa siklus |
| Scan secret pada unit file | **BERSIH** (tidak ada secret/kredensial) |
| Deployment | **BELUM DIJALANKAN** (menunggu approval) |

### 1.1 Temuan koreksi penting: `reload=True` di `main.py`

Audit Phase 5.1 menyimpulkan proses backend berjalan "tanpa `--reload`" dan child PID 69578 berasal dari library. **Itu tidak akurat.** `main.py` sebelumnya berisi:

```python
uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
```

`reload=True` membuat uvicorn men-spawn proses **reloader (parent) + child server** — persis pola dua PID (69553 parent, 69578 child `python -c from multiprocessing.spawn ...`) yang tercatat di audit. Konsekuensi bila dijalankan di bawah systemd `Type=simple`:

1. Melanggar syarat eksplisit Phase 5.1: *"Tidak menggunakan reload atau workers tambahan"*.
2. Menghasilkan **dua proses** per service (melanggar prinsip *zero duplicate process*).
3. `systemctl stop` mengirim SIGTERM hanya ke parent; child bisa tertinggal bila shutdown tidak rapi.
4. Watcher reload memantau filesystem terus-menerus — tidak perlu di produksi.

Perbaikan dilakukan **minimal dan reversibel**: default produksi `reload=False`, mode dev tetap tersedia via `UVICORN_RELOAD=1 python main.py`. Tidak ada perubahan pada `app/main.py`, router, model, service, maupun schema. Diff lengkap ada di Lampiran A.

---

## 2. Isi Lengkap Unit Backend — `deploy/measlescare-backend.service`

```ini
[Unit]
Description=MeaslesCare FastAPI Backend
Documentation=file:///home/orangepi/backend-measlescare/PHASE_5_1_UNIT_FILES_REPORT.md
After=network.target mariadb.service
Requires=mariadb.service
# Appliance: selalu coba pulih. RestartSec=5 mencegah tight-loop.
StartLimitIntervalSec=0

[Service]
Type=simple
User=orangepi
Group=orangepi
WorkingDirectory=/home/orangepi/backend-measlescare
Environment=PYTHONUNBUFFERED=1
ExecStart=/home/orangepi/backend-measlescare/venv/bin/python main.py
Restart=always
RestartSec=5
KillSignal=SIGTERM
KillMode=mixed
TimeoutStopSec=30
NoNewPrivileges=yes
StandardOutput=journal
StandardError=journal
SyslogIdentifier=measlescare-backend

[Install]
WantedBy=multi-user.target
```

Rasional tiap direktif:

| Direktif | Alasan (berbasis kondisi aktual) |
| :-- | :-- |
| `After=network.target mariadb.service` + `Requires=mariadb.service` | `app/main.py` (`on_startup`) menjalankan `Base.metadata.create_all()` → `migrate_database()` → seeder Role/User/Gejala/Aturan. Tanpa DB, startup gagal. `Requires` = dependency keras; `After` = urutan. |
| `Type=simple` | Uvicorn berjalan di foreground; tanpa fork. Valid karena `reload=False` (single process). |
| `User=orangepi` / `Group=orangepi` | Non-root, uid/gid 1000 terverifikasi ada. |
| `WorkingDirectory=/home/orangepi/backend-measlescare` | Wajib: `main.py` di root repo dan `load_dotenv()` di `app/core/config.py` membaca `.env` relatif cwd. |
| `ExecStart=.../venv/bin/python main.py` | Persis command proses yang berjalan saat audit (`./venv/bin/python main.py`). Path `/home/orangepi/venv` **tidak ada** — tidak dipakai. |
| `Environment=PYTHONUNBUFFERED=1` | Log langsung ke journal tanpa buffering. Bukan secret. |
| `Restart=always` / `RestartSec=5` | Pulih dari crash, tidak tight-loop. |
| `StartLimitIntervalSec=0` | Appliance: jangan pernah berhenti mencoba (default systemd akan menyerah setelah 5 start/10s dan meninggalkan service `failed` permanen). `RestartSec=5` tetap menjadi pembatas laju. |
| `KillSignal=SIGTERM` + `KillMode=mixed` + `TimeoutStopSec=30` | SIGTERM ke proses utama (uvicorn graceful shutdown), SIGKILL ke cgroup setelah 30s bila menggantung. |
| `NoNewPrivileges=yes` | Hardening dasar tanpa mengubah perilaku aplikasi. |
| `StandardOutput/Error=journal`, `SyslogIdentifier` | Semua log ke journald dengan tag stabil. |
| **Tidak ada** `--workers`, `--reload`, `ExecReload`, `EnvironmentFile` | Sesuai syarat; tidak menambah proses; tidak menaruh secret di systemd env. |

---

## 3. Isi Lengkap Unit Bridge — `deploy/measlescare-bridge.service`

```ini
[Unit]
Description=MeaslesCare MQTT Bridge
Documentation=file:///home/orangepi/backend-measlescare/PHASE_5_1_UNIT_FILES_REPORT.md
After=network.target mosquitto.service measlescare-backend.service
Wants=mosquitto.service measlescare-backend.service
# Appliance: selalu coba pulih. RestartSec=3 mencegah tight-loop.
StartLimitIntervalSec=0

[Service]
Type=simple
User=orangepi
Group=orangepi
WorkingDirectory=/home/orangepi/backend-measlescare
Environment=PYTHONUNBUFFERED=1
ExecStart=/home/orangepi/backend-measlescare/venv/bin/python -m integrasi_sensor.bridge.mqtt_bridge
Restart=always
RestartSec=3
TimeoutStopSec=20
NoNewPrivileges=yes
StandardOutput=journal
StandardError=journal
SyslogIdentifier=measlescare-bridge

[Install]
WantedBy=multi-user.target
```

Perubahan vs template lama (yang ada di disk sebelum pekerjaan ini):

| # | Sebelum | Sesudah | Alasan |
| :-- | :-- | :-- | :-- |
| 1 | `After=... mosquitto.service mariadb.service`, `Wants=mosquitto.service mariadb.service` | `After=network.target mosquitto.service measlescare-backend.service`, `Wants=mosquitto.service measlescare-backend.service` | Bridge adalah adapter HTTP (`POST /api/kiosk-session/reading`); tidak meng-import `app.db.session`, tidak menulis DB. Dependency MariaDB **dihapus**. |
| 2 | — | `measlescare-backend.service` di `After=` + `Wants=` | Urutan startup: backend lebih dulu. **Soft** (`Wants`, bukan `Requires`) karena bridge sudah punya HTTP retry 4× dengan backoff 1→2→4→8s (maks 30s) — backend belum siap tidak boleh menggagalkan bridge. |
| 3 | tanpa `Group=` | `Group=orangepi` | Sesuai syarat. |
| 4 | tanpa `TimeoutStopSec` | `TimeoutStopSec=20` | Batas stop wajar: loop utama bridge tidur 5s, SIGTERM default menghentikan proses seketika. |
| 5 | `Description=MeaslesCare MQTT Bridge (sensor -> backend)` | `Description=MeaslesCare MQTT Bridge` | Sesuai spesifikasi Phase 5.1. |
| 6 | `--verbose` (proses manual) | **tanpa** `--verbose` | Mode produksi; level log INFO (bukan DEBUG). |
| 7 | tanpa journald eksplisit | `StandardOutput/Error=journal` + `SyslogIdentifier=measlescare-bridge` | Logging journald eksplisit. |
| 8 | (tidak ada) | `StartLimitIntervalSec=0`, `NoNewPrivileges=yes` | Idempotensi restart + hardening dasar. |

Catatan konfigurasi: bridge memuat **sendiri** `integrasi_sensor/config.env` lewat `load_dotenv(ROOT/"integrasi_sensor"/"config.env")` (`ROOT` dihitung dari `__file__`, bukan cwd). Karena itu **tidak ada `EnvironmentFile`** dan **tidak ada secret di unit file**. File `config.env` terverifikasi `-rw-------` (0600) milik `orangepi`.

---

## 4. Hasil Validasi Konfigurasi

### 4.1 Validasi sintaks systemd

```
$ systemd-analyze verify deploy/measlescare-backend.service deploy/measlescare-bridge.service
netplan-ovs-cleanup.service: Failed to open /run/systemd/system/...: Permission denied
exit=0
```

Exit code **0**. Satu-satunya baris adalah peringatan lingkungan (unit netplan sistem, tidak dapat dibaca tanpa root) — **bukan** dari unit kita. Tidak ada error `Unknown key`, `Invalid setting`, atau `Executable ... not found`.

### 4.2 Sensor resolusi ExecStart

| Unit | ExecStart | Hasil |
| :-- | :-- | :-- |
| backend | `/home/orangepi/backend-measlescare/venv/bin/python main.py` | ada, executable |
| bridge | `.../venv/bin/python -m integrasi_sensor.bridge.mqtt_bridge` | modul importable |

### 4.3 Validasi di environment bersih (simulasi systemd, `env -i`)

Systemd tidak mewarisi environment shell, jadi diuji dengan environment minimal:

```
$ env -i PATH=... HOME=/home/orangepi LANG=C.UTF-8 ./venv/bin/python -c "import app.main"
app import OK, routes= 14
(onnxruntime: GPU device discovery failed — benign, tidak ada GPU di Orange Pi)

$ env -i PATH=... HOME=/home/orangepi ./venv/bin/python -c "import integrasi_sensor.bridge.mqtt_bridge"
bridge import OK, ROOT= /home/orangepi/backend-measlescare
```

Tidak ada import yang bergantung pada env shell lama. `venv/bin/python` = Python 3.10.12, `uvicorn 0.54.0`, `fastapi 0.143.5`.

### 4.4 Validasi flag reload

```
$ ./venv/bin/python -c "import main; print(main.RELOAD)"          -> False
$ UVICORN_RELOAD=1 ./venv/bin/python -c "import main; print(main.RELOAD)" -> True
$ ./venv/bin/python -m py_compile main.py                          -> OK
```

Produksi: satu proses. Dev: `UVICORN_RELOAD=1 python main.py` tetap berfungsi.

### 4.5 Validasi konfigurasi runtime

| Pemeriksaan | Hasil |
| :-- | :-- |
| Koneksi DB dengan konfigurasi default `app/core/config.py` | **OK** → `db_huawei`, MariaDB 10.6.23 |
| `.env` root | tidak ada (sesuai kondisi audit) → unit **tidak** memakai `EnvironmentFile`, state direproduksi apa adanya |
| `integrasi_sensor/config.env` | `-rw-------` (0600), uid 1000 |
| `MQTT_HOST` / `MQTT_PORT` | `127.0.0.1` / `1883` |
| `MQTT_SUBSCRIBE_TOPIC` | `measlescare/+/reading` |
| `BACKEND_URL` | `http://127.0.0.1:8000` |
| `KIOSK_API_KEY` | **SET** (22 karakter, nilai tidak ditampilkan) → bridge tidak akan exit kode 2 |
| Port 8000 saat ini | **tidak ada listener** (proses lama sudah tidak berjalan) |
| Port 1883 | listening `0.0.0.0:1883` (Mosquitto) |

### 4.6 Scan secret pada unit file

```
$ grep -Ei 'secret|password|passwd|token|api_key|KIOSK' deploy/*.service
NO secret patterns found
```

---

## 5. Hasil Pemeriksaan Dependency

Graf (tidak ada siklus):

```
mariadb.service ──Requires + After──► measlescare-backend.service
mosquitto.service ──Wants + After──► measlescare-bridge.service
measlescare-backend.service ──Wants + After (soft)──► measlescare-bridge.service
```

Pembuktian tidak ada siklus:
- `measlescare-backend.service` hanya mereferensikan `mariadb.service` dan `network.target` — **tidak** mereferensikan bridge.
- `measlescare-bridge.service` mereferensikan `mosquitto.service` + `measlescare-backend.service`.
- `mariadb.service` / `mosquitto.service` adalah unit bawaan dan tidak mereferensikan unit MeaslesCare.
- Himpunan edge: {M→B, Q→Br, B→Br}. Tidak ada jalur balik Br→B, sehingga acyclic.

Kebenaran dependency:

| Dependency | Unit | Dasar |
| :-- | :-- | :-- |
| MariaDB | backend (`Requires`) | `on_startup` memanggil `create_all` + `migrate_database` + seeder → gagal tanpa DB |
| MariaDB | bridge (**tidak**) | bridge hanya HTTP adapter; tidak meng-import layer DB |
| Mosquitto | bridge (`Wants`) | `paho.mqtt.client` subscribe `measlescare/+/reading` |
| Backend | bridge (`Wants`, soft) | target HTTP `127.0.0.1:8000`; sudah ada retry |

Catatan penting: `After=` **hanya** urutan start, bukan jaminan API siap menerima request. Karena itu dependency bridge→backend sengaja `Wants` (soft) dan mengandalkan mekanisme retry yang **sudah ada** di `mqtt_bridge.py` (`worker()`: 4 percobaan, backoff 1→2→4→8s; error 401/403/404/422 tidak di-retry; `connect_async` + `reconnect_delay_set(1..30)` untuk MQTT). Tidak ada mekanisme retry baru yang dibuat.

---

## 6. Startup Order

```
1. network.target
2. mariadb.service            (enabled, active)
3. Mosquitto (mosquitto.service, enabled, active)   ── sejajar, tidak saling bergantung
4. measlescare-backend.service  (butuh MariaDB)
5. measlescare-bridge.service   (setelah backend + Mosquitto)
```

- Boot: `WantedBy=multi-user.target` pada kedua unit → auto-start.
- Jika MariaDB lambat: backend gagal start → `Restart=always` + `RestartSec=5` + `StartLimitIntervalSec=0` mencoba ulang sampai DB siap.
- Jika backend crash sesudah bridge jalan: bridge tetap hidup, HTTP retry menahan payload, lalu pulih saat backend kembali.
- Jika Mosquitto restart: paho reconnect otomatis (1–30s), bridge tidak perlu di-restart.

---

## 7. Perintah Deployment (TAHAP B — dijalankan pengguna, butuh sudo)

Semua perintah dijalankan **dari** `/home/orangepi/backend-measlescare`. Dilarang memakai `pkill -f main.py` atau `pkill -f mqtt_bridge` (terbukti false positive terhadap shell wrapper agent).

### Langkah 1 — Backup kondisi unit sebelumnya (sebelum menimpa)

```bash
sudo mkdir -p /root/systemd-backup-phase51
sudo cp -a /etc/systemd/system/measlescare-backend.service /root/systemd-backup-phase51/ 2>/dev/null || echo "backend unit belum ada (baru)"
sudo cp -a /etc/systemd/system/measlescare-bridge.service  /root/systemd-backup-phase51/ 2>/dev/null || echo "bridge unit belum ada (baru)"
ls -l /root/systemd-backup-phase51/
```

### Langkah 2 — Salin unit file

```bash
sudo install -m 0644 -o root -g root deploy/measlescare-backend.service /etc/systemd/system/measlescare-backend.service
sudo install -m 0644 -o root -g root deploy/measlescare-bridge.service  /etc/systemd/system/measlescare-bridge.service
sudo systemctl daemon-reload
sudo systemd-analyze verify /etc/systemd/system/measlescare-backend.service /etc/systemd/system/measlescare-bridge.service
```

### Langkah 3 — Identifikasi proses lama secara spesifik (port + cmdline + cwd)

```bash
# Backend: pemilik port 8000 (jika ada)
ss -ltnp 'sport = :8000'
# Ambil PID dari kolom users:(("python",pid=NNNN,...))
ps -o pid,ppid,user,lstart,args -p <PID_BACKEND>

# Bridge: proses python yang modulnya mqtt_bridge, bukan shell wrapper
ps -eo pid,ppid,user,args | awk '$4 ~ /venv\/bin\/python/ && $0 ~ /integrasi_sensor\.bridge\.mqtt_bridge/ {print}'

# Verifikasi identitas sebelum kill (wajib): cwd, uid, cmdline
sudo readlink -f /proc/<PID>/cwd        # harus /home/orangepi/backend-measlescare
sudo tr '\0' ' ' < /proc/<PID>/cmdline; echo
ps -o uid= -p <PID>                      # harus 1000 (orangepi)
```

Kondisi terukur saat laporan ini dibuat: **port 8000 tidak listening** dan **tidak ada proses `main.py` / `mqtt_bridge` yang berjalan**. Artinya langkah 4 kemungkinan besar tidak diperlukan; tetap jalankan pemeriksaan di atas dan **jangan** kill apa pun bila PID tidak terverifikasi.

### Langkah 4 — Hentikan proses lama (hanya jika Langkah 3 menemukan proses valid)

```bash
# Hanya untuk PID yang sudah diverifikasi. Backend: sinyal ke parent (child reloader ikut mati).
kill -TERM <PID_BACKEND_PARENT>
kill -TERM <PID_BRIDGE>

sleep 3
ss -ltnp 'sport = :8000'                 # harus kosong
ps -p <PID_BACKEND_PARENT>,<PID_BRIDGE>  # harus "no such process" / kosong
```

Bila masih hidup setelah 10s: `kill -TERM` ulang, lalu `kill -KILL <PID>` **spesifik** (bukan pola).

### Langkah 5 — Aktifkan & jalankan backend

```bash
sudo systemctl enable --now measlescare-backend.service
sleep 4
systemctl status measlescare-backend --no-pager
curl -s http://127.0.0.1:8000/ ; echo
ss -ltnp 'sport = :8000'
sudo journalctl -u measlescare-backend -n 40 --no-pager
```

Harapan: `active (running)`, root endpoint `{"status":"ok",...}`, satu listener di `127.0.0.1:8000`.

### Langkah 6 — Aktifkan & jalankan bridge

```bash
sudo systemctl enable --now measlescare-bridge.service
sleep 3
systemctl status measlescare-bridge --no-pager
sudo journalctl -u measlescare-bridge -n 40 --no-pager
```

Harapan: `active (running)` dan log INFO berisi `subscribed: measlescare/+/reading`.

### Langkah 7 — Verifikasi akhir + cek duplikasi

```bash
systemctl is-enabled measlescare-backend measlescare-bridge
systemctl is-active  measlescare-backend measlescare-bridge
# Hitung proses nyata (bukan pola yang bisa false positive)
ss -ltnp 'sport = :8000' | grep -c 127.0.0.1
pgrep -a -u orangepi -f '^/home/orangepi/backend-measlescare/venv/bin/python ' | wc -l
```

Ekspektasi: backend **1** proses (tanpa reloader), bridge **1** proses → total **2**.

---

## 8. Perintah Monitoring

```bash
# Log live
sudo journalctl -u measlescare-backend -f
sudo journalctl -u measlescare-bridge  -f

# Status ringkas
sudo systemctl status measlescare-backend
sudo systemctl status measlescare-bridge

# Log sejak boot / hari ini (tanpa follow)
sudo journalctl -u measlescare-backend -b --no-pager
sudo journalctl -u measlescare-bridge  --since today --no-pager

# Metrik service
systemctl show measlescare-backend -p ActiveState -p SubState -p NRestarts -p MainPID
systemctl show measlescare-bridge  -p ActiveState -p SubState -p NRestarts -p MainPID

# Port & proses
ss -ltnp 'sport = :8000'
pgrep -a -u orangepi -f '^/home/orangepi/backend-measlescare/venv/bin/python '
```

Catatan privasi log: unit tidak memuat secret; bridge mencetak `rfid_uid`/`suhu`/`nik` hasil validasi tetapi **tidak** mencetak `KIOSK_API_KEY`, password, atau token. Backend mencetak kredensial admin default **hanya** bila akun admin belum ada (saat ini sudah ada) — dicatat sebagai utang teknis, bukan regresi Phase 5.1.

---

## 9. Testing Plan (setelah persetujuan)

### A. Backend

| # | Uji | Perintah | Kriteria lulus |
| :-- | :-- | :-- | :-- |
| A1 | Service aktif | `systemctl is-active measlescare-backend` | `active` |
| A2 | Port listening | `ss -ltnp 'sport = :8000'` | satu listener `127.0.0.1:8000`, bukan `0.0.0.0` |
| A3 | Health endpoint | `curl -s http://127.0.0.1:8000/` | `{"status":"ok","app":...}` |
| A4 | Tanpa error startup | `journalctl -u measlescare-backend -n 60` | tidak ada traceback; ada log startup uvicorn |
| A5 | Satu proses | `pgrep -a -u orangepi -f '^/home/orangepi/backend-measlescare/venv/bin/python '` | hanya 1 baris `python main.py` |

### B. MQTT Bridge

| # | Uji | Perintah | Kriteria lulus |
| :-- | :-- | :-- | :-- |
| B1 | Service aktif | `systemctl is-active measlescare-bridge` | `active` |
| B2 | Terhubung broker | `journalctl -u measlescare-bridge -n 30` | `subscribed: measlescare/+/reading` |
| B3 | Dapat menghubungi backend | publish 1 payload uji (C2) lalu cek log | `ACCEPTED`/`REJECTED`/`duplicate`, **bukan** `gagal kirim setelah retry` |
| B4 | Tanpa duplikasi | `pgrep -a -u orangepi -f mqtt_bridge` (verifikasi manual tiap PID) | tepat 1 proses bridge |

### C. Integrasi sensor

| # | Uji | Perintah | Kriteria lulus |
| :-- | :-- | :-- | :-- |
| C1 | Subscriber menerima payload ESP32 | `mosquitto_sub -h 127.0.0.1 -t 'measlescare/+/reading' -v -C 1` + publish | payload tampil |
| C2 | Bridge meneruskan | publish payload kontrak ↓ | log bridge memproses, tidak ada error permanen |
| C3 | Respons validasi backend | payload dengan `rfid_uid` dikenal | `ACCEPTED` + `nik` pada log |
| C4 | Tidak menulis tabel Gejala otomatis | `SELECT COUNT(*) FROM Gejala;` sebelum/sesudah publish | **jumlah tidak berubah** (hanya `sensor_readings` bertambah) |

Contoh publish payload uji (aman, satu event):

```bash
mosquitto_pub -h 127.0.0.1 -t 'measlescare/kiosk-01/reading' -q 1 -m '{
  "event_id": "phase51-test-0001",
  "device_id": "kiosk-01",
  "rfid_uid": "<UID_KARTU_TERDAFTAR>",
  "object_temp": 37.2,
  "ambient_temp": 29.5,
  "uptime_ms": 123456
}'
```

C4 dijalankan dengan query **baca saja**; tidak ada DDL/DML manual ke database.

### D. Persistence

| # | Uji | Cara | Kriteria |
| :-- | :-- | :-- | :-- |
| D1 | Tahan terminal ditutup | tutup semua terminal/sesi agent, lalu cek dari sesi baru | kedua service tetap `active` |
| D2 | Tidak bergantung sesi Hermes | `systemctl show ... -p MainPID` lalu `ps -o ppid= -p <MainPID>` | PPID = **1** (systemd), bukan PID sesi agent |
| D3 | Auto-start saat boot | **butuh reboot — hanya dengan persetujuan eksplisit** | kedua service `active` setelah boot |

### E. Recovery (butuh persetujuan terpisah)

```bash
systemctl show measlescare-backend -p Restart -p RestartSec -p NRestarts
sudo systemctl kill -s KILL measlescare-backend      # simulasi crash
sleep 8
systemctl is-active measlescare-backend
systemctl show measlescare-backend -p NRestarts
```

Kriteria: kembali `active`, `NRestarts` bertambah, tidak ada proses duplikat.

---

## 10. Security Notes

| Aspek | Status |
| :-- | :-- |
| User non-root | `User=orangepi`, `Group=orangepi` (uid/gid 1000) pada kedua unit |
| Secret di unit file | Tidak ada. `KIOSK_API_KEY` tetap di `integrasi_sensor/config.env` (0600) dan dibaca bridge sendiri |
| `EnvironmentFile` | Tidak dibuat (tidak diperlukan implementasi aktual) |
| Permission konfigurasi | `config.env` `-rw-------` milik `orangepi` — sesuai |
| Port terekspos | Backend bind `127.0.0.1:8000` di kode (`main.py`), bukan `0.0.0.0` → tidak terekspos ke LAN |
| Mosquitto | `0.0.0.0:1883` dengan anonymous access — **tidak diubah** di fase ini (sesuai instruksi), dicatat sebagai risiko Phase 6 |
| Firewall | **tidak diubah** |
| Privilege escalation | `NoNewPrivileges=yes` |
| Tambahan hardening (ProtectHome/ProtectSystem/PrivateTmp) | **sengaja tidak dipakai**: aplikasi hidup di `/home/orangepi` dan memuat file model/face data; menambah sandbox di luar scope berisiko memecah Phase 5 |

Hardening MQTT (auth broker, TLS, ACL) tetap dijadwalkan pada fase keamanan berikutnya.

---

## 11. Rollback Procedure

Dijalankan hanya bila deployment Tahap B gagal. **Tidak** melakukan reset git, `DROP TABLE`, atau perubahan database — skema & business logic tidak berubah di Phase 5.1.

```bash
# 1. Hentikan & nonaktifkan service baru
sudo systemctl disable --now measlescare-bridge.service
sudo systemctl disable --now measlescare-backend.service

# 2. Pulihkan unit sebelumnya (jika backup ada); jika tidak ada, hapus unit baru
if [ -f /root/systemd-backup-phase51/measlescare-backend.service ]; then
  sudo cp -a /root/systemd-backup-phase51/measlescare-backend.service /etc/systemd/system/
else
  sudo rm -f /etc/systemd/system/measlescare-backend.service
fi
if [ -f /root/systemd-backup-phase51/measlescare-bridge.service ]; then
  sudo cp -a /root/systemd-backup-phase51/measlescare-bridge.service /etc/systemd/system/
else
  sudo rm -f /etc/systemd/system/measlescare-bridge.service
fi

# 3. Reload & bersihkan state gagal
sudo systemctl daemon-reload
sudo systemctl reset-failed measlescare-backend.service measlescare-bridge.service 2>/dev/null

# 4. Verifikasi tidak ada sisa proses MeaslesCare
ss -ltnp 'sport = :8000'          # harus kosong
ps -eo pid,args | awk '$0 ~ /venv\/bin\/python/ && ($0 ~ /main\.py/ || $0 ~ /mqtt_bridge/)'
```

Setelah rollback, kondisi kembali ke "tidak ada service" (kondisi sebelum Phase 5.1) — proses background lama **tidak** dihidupkan otomatis. Bila operasional butuh backend segera, jalankan manual dengan cara lama yang terverifikasi:

```bash
cd /home/orangepi/backend-measlescare
nohup ./venv/bin/python main.py > /tmp/backend-manual.log 2>&1 &
nohup ./venv/bin/python -m integrasi_sensor.bridge.mqtt_bridge > /tmp/bridge-manual.log 2>&1 &
```

Rollback kode (hanya jika `main.py` perlu kembali ke mode dev reload):

```bash
# Tidak memakai git reset. Kembalikan reload ke mode dev hanya bila memang diinginkan:
UVICORN_RELOAD=1 ./venv/bin/python main.py    # tanpa mengubah file
```

Perubahan `main.py` bersifat aditif-kompatibel: perilaku dev lama dapat direproduksi lewat env var, sehingga rollback file tidak wajib.

---

## 12. Approval Checklist

| # | Item | Status |
| :-- | :-- | :-- |
| 1 | `deploy/measlescare-backend.service` dibuat | ✅ |
| 2 | `deploy/measlescare-bridge.service` diperbarui (tanpa MariaDB, ada `Group`, `TimeoutStopSec`, journald) | ✅ |
| 3 | ExecStart memakai venv repo (`/home/orangepi/backend-measlescare/venv/bin/python`) | ✅ |
| 4 | Backend `python main.py`, bridge `-m integrasi_sensor.bridge.mqtt_bridge` tanpa `--verbose` | ✅ |
| 5 | `Requires`/`After` MariaDB hanya di backend | ✅ |
| 6 | Bridge `After` Mosquitto + backend, tanpa MariaDB | ✅ |
| 7 | `Restart=always` (5s backend / 3s bridge), `TimeoutStopSec` ada | ✅ |
| 8 | Logging journald eksplisit pada kedua unit | ✅ |
| 9 | Tidak ada secret di unit file / tidak ada `EnvironmentFile` | ✅ |
| 10 | `systemd-analyze verify` exit 0 | ✅ |
| 11 | Import backend & bridge lolos di environment bersih | ✅ |
| 12 | `main.py`: `reload` dinonaktifkan untuk produksi (satu proses) | ✅ **(butuh persetujuan — lihat risiko R1)** |
| 13 | Tidak ada `sudo`, penyalinan unit, `daemon-reload`, start/stop service, atau reboot di Tahap A | ✅ |
| 14 | Database & business logic tidak diubah | ✅ |
| 15 | **Persetujuan pengguna untuk Tahap B** | ⏳ **MENUNGGU** |

### Risiko yang masih tersisa

| # | Risiko | Dampak | Mitigasi |
| :-- | :-- | :-- | :-- |
| R1 | `main.py` diubah (reload → env-gated, default off) | Perubahan file di luar unit systemd; mode dev perlu `UVICORN_RELOAD=1` | Diff minimal (Lampiran A), reversibel, tidak menyentuh `app/`. Tanpa ini syarat "tanpa reload / zero duplicate process" tidak bisa dipenuhi |
| R2 | `on_startup` menjalankan `create_all` + `migrate_database` + seeder setiap start | DDL berulang saat crash-loop (idempotent, tapi menambah waktu start & beban DB) | `RestartSec` membatasi frekuensi; perbaikan desain = Phase 6 (migrasi terpisah) |
| R3 | `SECRET_KEY` default `"change-me"` dan kredensial DB default ada di `app/core/config.py` | Risiko keamanan token & kredensial di source | Pre-existing; tidak diubah di Phase 5.1; wajib Phase 6 (proteksi env file) |
| R4 | `StartLimitIntervalSec=0` (retry tanpa batas) | Crash-loop persisten hanya dibatasi `RestartSec` (log bisa ramai) | Disengaja untuk appliance; monitoring `NRestarts` di §8 |
| R5 | Mosquitto anonymous di `0.0.0.0:1883` | Siapa pun di LAN bisa publish payload palsu | Tidak diubah sesuai instruksi; Phase keamanan berikutnya |
| R6 | Bridge tidak graceful-drain antrian saat SIGTERM (thread worker daemon) | Payload yang masih di queue bisa hilang saat restart | `TimeoutStopSec=20`; payload ESP32 dapat dikirim ulang dengan `event_id` sama dan backend men-dedup (`duplicate`) |
| R7 | `After=` bukan jaminan API siap | Payload awal setelah boot bisa kena retry | Retry HTTP + backoff sudah ada; `Wants` soft |
| R8 | Uji reboot belum dilakukan | Perilaku boot penuh belum terbukti | Dijadwalkan di §9-D3, butuh persetujuan eksplisit |

---

## Rekomendasi

**GO untuk Tahap B**, dengan syarat persetujuan eksplisit pengguna dan urutan deployment §7 dijalankan apa adanya (identifikasi PID spesifik; tanpa `pkill -f`).

Alasan: kedua unit lolos `systemd-analyze verify`, command & working directory identik dengan proses yang terverifikasi di Phase 5, tidak ada dependency sirkular, tidak ada secret di unit, dan satu-satunya perubahan kode (`main.py`) diperlukan agar service berjalan sebagai satu proses.

---

## Lampiran A — Diff `main.py`

```diff
--- a/main.py
+++ b/main.py
@@ -1,5 +1,21 @@
-"""Launcher: jalankan server dengan `py main.py` dari folder Backend."""
+"""Launcher: jalankan server dengan `python main.py` dari folder Backend.
+
+Mode produksi (systemd) TIDAK memakai reload: reload men-spawn proses
+reloader + child (dua proses), yang bertentangan dengan unit `Type=simple`
+dan menyebabkan proses ganda. Untuk pengembangan lokal:
+
+    UVICORN_RELOAD=1 python main.py
+"""
+import os
+
 import uvicorn
 
+RELOAD = os.getenv("UVICORN_RELOAD", "0") == "1"
+
 if __name__ == "__main__":
-    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
+    uvicorn.run(
+        "app.main:app",
+        host="127.0.0.1",
+        port=8000,
+        reload=RELOAD,
+    )
```

## Lampiran B — Artefak

| File | Ukuran | Status |
| :-- | :-- | :-- |
| `/home/orangepi/backend-measlescare/deploy/measlescare-backend.service` | 710 B | baru |
| `/home/orangepi/backend-measlescare/deploy/measlescare-bridge.service` | 759 B | diperbarui |
| `/home/orangepi/backend-measlescare/main.py` | 536 B | diubah (Lampiran A) |
| `/home/orangepi/backend-measlescare/PHASE_5_1_UNIT_FILES_REPORT.md` | dokumen ini | baru |
