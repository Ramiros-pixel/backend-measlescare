# PHASE 5.1 — REVIEW KHUSUS R1 (`main.py` reload flag)

**Tanggal:** 20 November 2026
**Mode:** READ-ONLY. Tidak ada perubahan kode tambahan, tidak ada deployment, tidak ada sudo, tidak ada service dijalankan, tidak ada database disentuh.
**Status:** menunggu persetujuan eksplisit pengguna.

Objek review: perubahan `main.py` dari `reload=True` (hardcoded) menjadi `reload=os.getenv("UVICORN_RELOAD","0")=="1"`.

---

## 1. Git diff lengkap

```
$ git status --short -- main.py
 M main.py

$ git diff -- main.py
diff --git a/main.py b/main.py
index b59dd05..1c4cf4c 100644
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

Hash:
- baseline `HEAD:main.py` → `b59dd05ec84aa85401e693eaf1563a5eb7d78c4a`
- working tree `main.py` → `1c4cf4c0ac112ff9717dc919e6870442bb47c552`

Statistik: 1 file, +16 / -2 baris. Tidak ada file lain yang berubah. `app/`, router, model, service, schema, migration: **tidak disentuh**.

---

## 2. Kondisi kode sebelum dan sesudah

### Sebelum (HEAD, 5 baris)

```python
"""Launcher: jalankan server dengan `py main.py` dari folder Backend."""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
```

### Sesudah (working tree, 21 baris)

```python
"""Launcher: jalankan server dengan `python main.py` dari folder Backend.

Mode produksi (systemd) TIDAK memakai reload: reload men-spawn proses
reloader + child (dua proses), yang bertentangan dengan unit `Type=simple`
dan menyebabkan proses ganda. Untuk pengembangan lokal:

    UVICORN_RELOAD=1 python main.py
"""
import os

import uvicorn

RELOAD = os.getenv("UVICORN_RELOAD", "0") == "1"

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=RELOAD,
    )
```

Perbedaan semantik:
- `host`, `port`, dan import string `"app.main:app"` **identik** — perilaku jaringan tidak berubah (tetap `127.0.0.1:8000`).
- `reload`: konstanta `True` → nilai dari env, default `False`.
- Tidak ada perubahan import aplikasi, tidak ada kode aplikasi yang dipanggil berbeda.

---

## 3. Alasan teknis perubahan diperlukan

### 3.1 Bukti dari source uvicorn yang terpasang (0.54.0)

`uvicorn.run()` memilih topologi proses secara eksplisit:

```python
if config.reload or config.workers > 1:
    if not isinstance(app, str):
        ... sys.exit(STARTUP_FAILURE)
else:
    config.load_app()

server = Server(config=config)
try:
    if config.should_reload:
        sock = config.bind_socket()
        ChangeReload(config, target=server.run, sockets=[sock]).run()
    elif config.workers > 1:
        sock = config.bind_socket()
        Multiprocess(config, sockets=[sock]).run()
    else:
        server.run()
```

`BaseReload` (dipakai `ChangeReload`) menjalankan server sebagai **subprocess**:

```python
def startup(self):
    self.process = get_subprocess(config=self.config, target=self.target, sockets=self.sockets)
    self.process.start()

def shutdown(self):
    self.process.terminate()
    self.process.join()
```

Dan yang paling penting: **socket listening di-bind oleh proses induk** (`config.bind_socket()`) lalu fd-nya diwariskan ke child. Jadi induk bukan sekadar pengawas — ia memegang port.

### 3.2 Bukti empiris pada file `main.py` yang asli (tanpa menjalankan server)

Blok `__main__` `main.py` dieksekusi dengan `uvicorn.run` di-stub, sehingga yang terekam adalah argumen yang benar-benar dikirim:

```
[default (systemd, tanpa env)]        app='app.main:app' host=127.0.0.1 port=8000 reload=False workers=None
[dev lokal UVICORN_RELOAD=1]         app='app.main:app' host=127.0.0.1 port=8000 reload=True  workers=None
[eksplisit UVICORN_RELOAD=0]         app='app.main:app' host=127.0.0.1 port=8000 reload=False workers=None
[nilai aneh UVICORN_RELOAD=false]    app='app.main:app' host=127.0.0.1 port=8000 reload=False workers=None
```

### 3.3 Konsekuensi yang dijadikan alasan

1. **Melanggar syarat eksplisit Phase 5.1**: unit backend dilarang memakai reload/workers tambahan.
2. **Proses ganda**: `reload=True` = supervisor + server + `multiprocessing.resource_tracker` = 3 proses per unit, sementara audit/target menyatakan satu proses.
3. **Port dimiliki supervisor**, bukan server → menghasilkan dua mode kegagalan serius yang dibuktikan di §5 (orphan yang memblokir restart, dan outage senyap dengan port tetap terikat).
4. **Watcher filesystem** (`watchfiles 1.3.0`) aktif terus-menerus di produksi tanpa manfaat.
5. **Tidak ada gunanya di produksi**: reload ditujukan untuk pengembangan; kode tidak berubah saat runtime.

Alternatif yang dipertimbangkan dan ditolak:
- `ExecStart=... -m uvicorn app.main:app` → menyimpang dari syarat "ExecStart harus `python main.py`" dan mengubah entry point terverifikasi.
- Menghapus file launcher → mengubah entry point yang dipakai audit.
- Membiarkan `reload=True` + systemd `KillMode=control-group` → tetap 3 proses dan tetap terkena hazard port; hanya menutupi gejala.

---

## 4. Dampak terhadap startup, shutdown, dan lifecycle

### 4.1 Startup (`systemctl start`)

| Aspek | `reload=False` (sesudah) | `reload=True` (sebelum) |
| :-- | :-- | :-- |
| Proses | 1 (uvicorn server in-process) | 3 (supervisor + server + resource_tracker) |
| MainPID systemd | proses server itu sendiri | supervisor |
| Binding port | oleh proses server | oleh supervisor, fd diwariskan |
| `Type=simple` cocok | ya | ya secara teknis, tetapi MainPID bukan server |
| Import app | `config.load_app()` di proses yang sama | di child |
| Startup event FastAPI (`create_all`/`migrate`/seed) | langsung di MainPID | di child; status systemd tidak mencerminkan hasilnya |

Catatan penting: pada `reload=True`, bila startup aplikasi gagal (mis. DB belum siap), yang mati adalah **child**, sedangkan supervisor tetap hidup dan memegang port. Unit tampak `active` walau API tidak pernah siap — dibuktikan di §5, kasus E.

### 4.2 Shutdown (`systemctl stop` → SIGTERM)

Diuji dengan request 5 detik yang sedang in-flight lalu SIGTERM ke MainPID (meniru `systemctl stop`):

| Config | Request in-flight | Proses setelah stop | Port |
| :-- | :-- | :-- | :-- |
| `reload=False` | `{"slow":"selesai"}` HTTP 200, selesai 5.00s | keluar | bebas seketika |
| `reload=True` | `{"slow":"selesai"}` HTTP 200, selesai 5.00s | keluar (child lalu supervisor) | bebas seketika |

Kesimpulan: **tidak ada regresi graceful shutdown**. Keduanya menuntaskan request in-flight; `KillMode=mixed` + `TimeoutStopSec=30` pada unit memberi ruang yang cukup (terukur ~3.8s sisa waktu tunggu setelah SIGTERM).

### 4.3 Lifecycle aplikasi

- Startup/shutdown event FastAPI (`@app.on_event("startup")` di `app/main.py`) berjalan di proses yang sama dengan server, sekali per boot/restart. Tidak ada duplikasi eksekusi seeding/migrasi.
- Pada `reload=True`, event startup berjalan di child; setiap child di-respawn (mis. karena sentuh file) event startup **berjalan ulang** — `create_all` + `migrate_database` + seeder dieksekusi ulang di produksi. Risiko tambahan yang hilang dengan `reload=False`.
- Reload watcher memantau direktori kerja; perubahan file apa pun (termasuk file log/sementara di repo) dapat memicu restart server di produksi.

---

## 5. Apakah berpotensi startup ganda, resource leak, atau konflik Uvicorn?

### 5.1 Startup ganda / duplikasi proses — TERBUKTI

- `reload=False`: 1 proses (`python launcher.py`, 0 child).
- `reload=True`: induk + 2 child (`multiprocessing.resource_tracker` + `multiprocessing.spawn`), total 3.

Selain itu, `restart()` pada supervisor melakukan `terminate()` + `join()` + spawn child baru. Jika `terminate()` tidak sempat menyelesaikan graceful shutdown, jendela tumpang-tindih proses sangat mungkin.

### 5.2 Orphan memblokir restart (EADDRINUSE) — TERBUKTI

Skenario: supervisor mati mendadak (SIGKILL / OOM killer / `systemctl kill -s KILL`) — persis yang bisa dilakukan systemd atau kernel.

```
parent(reloader)=8940, child=8942 8943
[parent di-SIGKILL]
port 8105 pemilik sekarang: 8943          <-- child jadi orphan (ppid=1)
layanan masih merespons: {"status":"ok"}  <-- masih melayani, tanpa supervisor
--- percobaan bind ulang (simulasi systemd restart) ---
BIND GAGAL: errno=98 Address already in use  <-- restart service akan gagal
```

Ini adalah jalur menuju crash-loop: orphan memegang port, systemd mencoba restart, `bind()` gagal, `Restart=always` mengulang, dan tidak ada yang membersihkan orphan karena systemd tidak lagi memiliki MainPID-nya (KillMode cgroup hanya membunuh anggota cgroup unit — orphan hasil SIGKILL supervisor tetap anggota cgroup selama unit sama, tetapi setelah unit berhenti dan start ulang, proses lama sudah tidak terlacak).

### 5.3 Outage senyap: MainPID hidup, layanan mati — TERBUKTI

Skenario: proses server (child) mati karena crash aplikasi, sedangkan supervisor tetap hidup.

```
parent alive? 8273
child state:    8276 Z            <-- zombie, tidak di-respawn
port 8104 bound by: 8273          <-- supervisor masih memegang port
sesudah (layanan masih hidup?): TIDAK ADA RESPONS
```

Systemd akan melaporkan `active (running)` (MainPID 8273 hidup) padahal API mati total dan port tetap terikat sehingga instance pengganti pun tidak bisa bind. `Restart=always` tidak akan pernah terpicu. Ini adalah mode kegagalan paling berbahaya untuk appliance.

### 5.4 Resource leak

- Proses: +2 proses permanen (supervisor + resource_tracker) selama reload aktif.
- Thread: supervisor menjalankan watcher `watchfiles` (Rust thread) + thread pemantau proses.
- Zombie: child yang mati tetap `Z` selama supervisor tidak melakukan `join()`/reap (terbukti di kasus D/E).
- File descriptor: socket listening dipegang supervisor **dan** diwariskan ke child — fd ganda untuk satu port.

### 5.5 Konflik dengan proses Uvicorn lain

Karena supervisor memegang port, satu instance reload-only dapat:
1. membuat instance baru gagal bind (EADDRINUSE) — kasus G;
2. tetap "menahan" port meski server sudah mati — kasus E;
3. meninggalkan server yang masih melayani setelah induknya hilang — kasus C.

Dengan `reload=False`, satu proses = satu pemilik port, dan kematian proses otomatis melepas port (kasus A: port bebas seketika setelah SIGTERM).

---

## 6. Hasil pengujian yang membuktikan perubahan aman

Metode: harness terpisah di `/home/orangepi/.hermes/cache/scratch/r1test/` memakai **dummy ASGI app** (bukan aplikasi MeaslesCare) dan port 8097–8105, sehingga **tidak ada** penulisan database, **tidak ada** sentuhan port 8000, dan **tidak ada** unit systemd yang dijalankan. Launcher uji memakai bentuk pemanggilan `uvicorn.run()` yang identik dengan `main.py`.

| # | Skenario | Config | Hasil terukur |
| :-- | :-- | :-- | :-- |
| 0 | Argumen `uvicorn.run` dari `main.py` asli (stub, tanpa server) | default | `reload=False`, host/port/app benar |
| A | Start normal, HTTP, lalu SIGTERM | `reload=False` | 1 proses, 0 child, HTTP 200, proses keluar, port bebas |
| B | Start normal, SIGTERM ke MainPID | `reload=True` | 3 proses, HTTP 200, semua keluar, port bebas |
| C | SIGKILL ke supervisor | `reload=True` | orphan (ppid=1) tetap melayani di port |
| D | SIGTERM ke child server saja | `reload=True` | supervisor hidup, child `Z`, port tetap terikat supervisor |
| E | Child mati (crash) | `reload=True` | **tidak ada respons HTTP**, port tetap terikat, systemd akan tetap "active" |
| F | Request 5s in-flight + SIGTERM | `reload=False` / `True` | keduanya menuntaskan request (HTTP 200, 5.00s), lalu keluar; port bebas |
| G | SIGKILL supervisor lalu bind ulang | `reload=True` | `errno=98 Address already in use` |

Validasi tambahan atas file `main.py`:
- `py_compile` OK.
- `runpy` eksekusi blok `__main__` dengan stub → argumen benar untuk default, `UVICORN_RELOAD=1`, `0`, dan nilai tak dikenal (`false` → False).
- Import `app.main` di environment bersih (`env -i`) OK, 14 route.
- Tidak ada referensi lain di repo yang memanggil `main.py` sebagai modul/import (hanya dokumentasi), sehingga perubahan ini tidak memengaruhi kode lain.

Kebersihan setelah pengujian (diverifikasi):
- semua proses uji dimatikan; tidak ada `multiprocessing.spawn`/`resource_tracker` tersisa;
- port 8097–8105 bebas;
- port 8000 tetap tidak terpakai;
- `git status` tidak memunculkan perubahan baru selain `main.py` (dan `deploy/` yang belum di-commit).

**Batasan pengujian (jujur):** harness memakai dummy app dan port uji, bukan aplikasi MeaslesCare di port 8000, karena menjalankan aplikasi asli akan mengeksekusi `create_all`/`migrate`/seeder (menulis database) — dilarang pada Tahap A. Perilaku proses yang diuji adalah perilaku **uvicorn**, bukan perilaku aplikasi, sehingga kesimpulan tetap valid untuk `main.py` yang memanggil `uvicorn.run()` dengan argumen sama.

---

## 7. Rollback khusus perubahan `main.py`

Tidak memerlukan git reset, tidak menyentuh database, tidak menyentuh unit systemd.

### Opsi 1 — kembalikan persis ke baseline HEAD

```bash
cd /home/orangepi/backend-measlescare
git checkout -- main.py
git hash-object main.py      # harus b59dd05ec84aa85401e693eaf1563a5eb7d78c4a
```

Konsekuensi: `reload=True` kembali → **3 proses** dan hazard §5 aktif. Ini hanya cocok bila Tahap B dibatalkan dan Anda kembali ke mode pengembangan.

### Opsi 2 — tulis ulang manual (tanpa git)

```bash
cat > /home/orangepi/backend-measlescare/main.py <<'EOF'
"""Launcher: jalankan server dengan `py main.py` dari folder Backend."""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
EOF
```

### Opsi 3 — tanpa mengubah file, paksa perilaku reload untuk sesi dev

```bash
UVICORN_RELOAD=1 /home/orangepi/backend-measlescare/venv/bin/python main.py
```

Verifikasi setelah rollback:

```bash
git diff --stat -- main.py       # kosong bila Opsi 1
venv/bin/python -m py_compile main.py
venv/bin/python -c "import runpy,uvicorn; \
  uvicorn.run=lambda a,**k: print(k); runpy.run_path('main.py', run_name='__main__')"
```

Catatan operasional: **jangan** mengganti `main.py` saat service sedang berjalan dengan topologi berbeda. Bila service sudah aktif dengan `reload=False` lalu file dikembalikan ke `reload=True`, lakukan `systemctl stop` lebih dulu — mengganti topologi proses secara live berisiko meninggalkan orphan yang memegang port 8000 (bukti kasus C/G).

---

## Ringkasan untuk keputusan

| Pertanyaan | Jawaban |
| :-- | :-- |
| Perubahan hanya di launcher? | Ya, `main.py` (5 → 21 baris), `app/` tidak tersentuh |
| Mengubah host/port/entry point? | Tidak: `127.0.0.1:8000`, `app.main:app` tetap |
| Menyebabkan startup ganda? | Tidak — justru menghilangkan (3 proses → 1) |
| Aman untuk graceful shutdown? | Ya, request in-flight tetap selesai (diuji) |
| Resource leak? | Tidak ada pada `reload=False`; leak/orphan adalah sifat `reload=True` |
| Bisa direproduksi ke mode dev? | Ya, `UVICORN_RELOAD=1` tanpa ubah file |
| Rollback? | `git checkout -- main.py`, hash terverifikasi |

**Rekomendasi R1:** terima perubahan. Tanpa perubahan ini, unit `Type=simple` + `Restart=always` tidak bisa memenuhi syarat "tanpa reload / zero duplicate process", dan dua mode kegagalan §5.2/§5.3 akan terbawa ke produksi.
