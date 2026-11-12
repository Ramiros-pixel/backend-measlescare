# Dokumentasi API — Face Recognition (Registrasi Wajah)

Integrasi sistem face recognition (Haar Cascade + LBPH, sebelumnya script desktop
`process-recognation/collect.py`) ke dalam backend FastAPI.

Inti alur: user mendaftar dengan **NIK + Nama + Tanggal lahir** (diketik sekali), lalu
**pengumpulan data wajah berjalan otomatis selama wajah tertangkap kamera** — tanpa
mengetik apa pun. Hasil pengumpulan dipakai untuk training model, dan **NIK + Nama dari
tabel `Users` menjadi label** hasil pengenalan.

---

## 1. Alur lengkap

```
  ┌─────────────┐    ┌──────────────┐    ┌───────────────────┐    ┌────────────┐    ┌──────────────┐
  │ 1. REGISTER │───▶│  2. LOGIN    │───▶│ 3. CAPTURE WAJAH  │───▶│ 4. TRAIN   │───▶│ 5. FACE LOGIN│
  │ NIK, Nama,  │    │ NIK+password │    │ frame kamera      │    │ LBPH       │    │ 1 frame → JWT│
  │ Tgl lahir   │    │ → JWT        │    │ otomatis (loop)   │    │ sinkron    │    │ + profil user│
  └─────────────┘    └──────────────┘    └───────────────────┘    └────────────┘    └──────────────┘
        │                                         │                     │
        │ label: NIK + Name dari tabel Users ◀─────┴─────────────────────┘
        └─ dataset: process-recognation/dataset/<NIK>/001.jpg ...
```

- Langkah 1–2: input ketik hanya di sini (NIK, Nama, Tgl lahir, password).
- Langkah 3: klien mengirim frame JPEG base64 berkala (mis. tiap 200 ms). Server
  mendeteksi wajah; **frame yang mengandung wajah** disimpan sebagai sampel. Berhenti
  otomatis saat target sampel tercapai (`SAMPLE_TARGET`, default **100**).
- Langkah 4: training LBPH sinkron, label diambil dari DB (`NIK` → `Name`).
- Langkah 5: login tanpa password, cukup 1 frame wajah → JWT.

---

## 2. Yang ditambahkan / diubah

| Berkas | Status | Keterangan |
|---|---|---|
| `app/services/face_engine.py` | **baru** | Deteksi Haar, simpan sampel, training LBPH sinkron, pengenalan + cache model |
| `app/routers/face.py` | **baru** | 9 endpoint `/face/*` |
| `app/schemas/face.py` | **baru** | Schema request/response |
| `tools/face_api_smoke_test.py` | **baru** | Smoke test end-to-end (20 assertion) |
| `examples/face_register_client.html` | **baru** | Client contoh: register → capture otomatis → train → face login |
| `requirements.txt` | diubah | `opencv-contrib-python-headless`, `numpy` |
| `Dockerfile` | diubah | `libgl1`, `libglib2.0-0` untuk OpenCV headless |
| `docker-compose.yml` | diubah | Volume `./process-recognation:/app/process-recognation` (dataset & model persisten) |
| `app/main.py` | diubah | Router `face` didaftarkan |

Script lama `process-recognation/collect.py` tetap jalan (tidak diubah) — dipakai untuk
collect/train/recognize mode desktop.

---

## 3. Deploy / menjalankan

```bash
cd /compe-rams/huawei-inv/backend-measlescare
docker compose build backend      # install opencv (~1-2 menit)
docker compose up -d
curl http://127.0.0.1:8000/        # {"status":"ok","app":"Huawei ICT Backend"}
```

Akses publik (Tailscale funnel) tetap: `https://ramirosservers.tail2d4b04.ts.net/api`
(prefix `/api` dilepas oleh funnel, sehingga di dalam container path-nya `/face/...`).

Dokumentasi interaktif bawaan FastAPI:

- Swagger UI: `/docs`
- OpenAPI JSON: `/openapi.json`

> **Dataset wajah wajib persisten.** Compose sudah memount
> `./process-recognation` ke `/app/process-recognation`, jadi sampel & model
> (`trainer/face_model.yml`) tidak hilang saat container di-rebuild. Tanpa mount ini,
> data akan hilang setiap rebuild image.

---

## 4. Referensi endpoint

Prefix default: `/api` (di produksi lewat funnel) atau `""` bila `API_PREFIX` kosong
(kondisi container saat ini, karena funnel melepas prefix `/api` sebelum proxy).
Endpoint yang sama jadi:

```
lokal   : http://127.0.0.1:8000/face/status
publik  : https://ramirosservers.tail2d4b04.ts.net/api/face/status
```

Contoh di dokumen ini memakai `BASE = http://127.0.0.1:8000` (tanpa `/api`).

| Method | Path | Auth | Fungsi |
|---|---|---|---|
| POST | `/auth/register` | — | Daftar akun: NIK, Nama, Tgl lahir, password, id_Role |
| POST | `/auth/login` | — | Login password → JWT |
| GET | `/face/status` | JWT | Status sampel & model user yang login |
| POST | `/face/capture` | JWT | Kirim 1 frame; disimpan bila ada wajah |
| POST | `/face/train` | JWT | Training LBPH (butuh sampel ≥ target) |
| GET | `/face/model` | Admin | Info model & dataset global |
| POST | `/face/retrain` | Admin | Training ulang seluruh dataset |
| DELETE | `/face/reset/{nik}` | JWT (diri sendiri/Admin) | Hapus sampel wajah seorang user |
| POST | `/face/recognize` | — | Identifikasi wajah pada 1 frame |
| POST | `/face/login` | — | Login dengan wajah → JWT + profil |

### 4.1 `POST /face/capture` — inti pengumpulan data otomatis

Request (JSON):

```json
{ "image": "/9j/4AAQSkZJRgABAQ..." }
```

`image` = frame JPEG/PNG dalam **base64**, boleh dengan prefix `data:image/jpeg;base64,`.

Response `200`:

```json
{
  "nik": "3201234567890097",
  "stored": 37,
  "target": 100,
  "face_detected": true,
  "completed": false,
  "message": "Wajah tertangkap, teruskan sesi pengambilan data."
}
```

- `stored` naik hanya bila wajah terdeteksi (frame tanpa wajah tidak disimpan).
- `completed: true` → target tercapai, klien berhenti mengirim frame dan lanjut training.
- Bila wajah tidak terdeteksi: `face_detected: false`, `stored` tidak berubah, `message`
  memberi tahu user untuk mendekat ke kamera. Klien cukup terus mengirim frame.

Contoh kirim 1 frame dengan `curl`:

```bash
BASE=http://127.0.0.1:8000
TOKEN=<jwt-dari-/auth/login>

python3 - <<'PY' > frame.json
import base64, json
print(json.dumps({"image": base64.b64encode(open("foto.jpg","rb").read()).decode()}))
PY

curl -s -X POST "$BASE/face/capture" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d @frame.json
```

### 4.2 `POST /face/train`

Syarat: sampel user ≥ `SAMPLE_TARGET`. Label otomatis dari tabel `Users`.

```bash
curl -s -X POST "$BASE/face/train" -H "Authorization: Bearer $TOKEN"
```

```json
{
  "status": "trained",
  "nik": "3201234567890097",
  "my_samples": 100,
  "total_samples": 100,
  "total_users": 1,
  "message": "Training selesai: 100 sampel dari 1 user. Sekarang Anda bisa login dengan wajah."
}
```

Error `400` bila sampel belum cukup:
`{"detail": "Sampel belum cukup: 43/100. Selesaikan capture dulu."}`

> Training **sinkron**: request selesai setelah model ditulis. Dataset kecil (< a few
> ribu sampel) selesai dalam hitungan detik. Penulisan file model bersifat atomik
> (tulis `.tmp` lalu rename) sehingga model lama tidak rusak bila request gagal.

### 4.3 `POST /face/recognize`

```bash
curl -s -X POST "$BASE/face/recognize" -H "Content-Type: application/json" \
  -d @frame.json
```

```json
{ "recognized": true, "user_id": "3201234567890097", "name": "Uji Wajah API", "confidence": 48.77 }
```

Tidak dikenali / tidak ada wajah:

```json
{ "recognized": false, "user_id": null, "name": null, "confidence": null }
```

`confidence` = LBPH distance: **semakin kecil semakin mirip**, cocok bila `<= 70`
(`CONFIDENCE_THRESHOLD`).

### 4.4 `POST /face/login`

```bash
curl -s -X POST "$BASE/face/login" -H "Content-Type: application/json" -d @frame.json
```

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": { "NIK": "3201234567890097", "Name": "Uji Wajah API", "role_name": "User" }
}
```

Wajah tidak dikenali → `401` `{"detail": "Wajah tidak dikenali atau model belum dilatih"}`.
Token hasil login wajah sama formatnya dengan login password, langsung bisa dipakai ke
endpoint ber-JWT (mis. `GET /auth/me`).

### 4.5 `GET /face/status`

```json
{
  "model_exists": true,
  "model_users": 1,
  "total_samples": 100,
  "unlabeled_samples": 100,
  "my_samples": 100,
  "target": 100,
  "trained_at": "2026-11-12T00:48:20.743147+00:00"
}
```

- `model_users` — jumlah user (label) di model aktif.
- `total_samples` — sampel yang **ikut training** (folder = NIK user terdaftar).
- `unlabeled_samples` — sampel di folder yang **tidak** punya user terdaftar (dilewati).
- `my_samples` — sampel user yang login; `target` — ambang boleh training.

### 4.6 `GET /face/model`, `POST /face/retrain`, `DELETE /face/reset/{nik}`

- `/face/model` (Admin): isi sama dengan `/face/status` tetapi `my_samples` milik admin.
- `/face/retrain` (Admin): training ulang seluruh dataset tanpa syarat target — dipakai
  setelah menghapus/merename dataset, atau untuk memperbarui nama label.
- `/face/reset/{nik}`: hapus semua sampel wajah seorang user. User biasa hanya boleh
  `nik`-nya sendiri; `403` bila mencoba nik lain. **Setelah reset, jalankan
  `/face/retrain`** (Admin) atau `/face/train` (user, bila sampelnya sudah ≥ target lagi)
  agar model tidak lagi memuat wajah tersebut.

---

## 5. Cara pakai dari frontend (yang dipakai di aplikasi)

Contoh siap pakai: **`examples/face_register_client.html`** (buka di browser, isi NIK/Nama/
Tgl lahir → klik "Daftar & mulai pengambilan wajah"). Inti kodenya:

```js
// 1) register + login sekali (input ketik hanya di sini)
await fetch(BASE + "/auth/register", { method: "POST", headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ NIK, Name, Tgl_lahir, Alamat, password, id_Role: "R2" }) });
const { access_token } = await (await fetch(BASE + "/auth/login", { method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ NIK, password }) })).json();

// 2) loop capture otomatis — tanpa input user
const video = document.getElementById("cam");
video.srcObject = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" }, audio: false });
const canvas = document.createElement("canvas");
canvas.width = 480; canvas.height = 360;

const timer = setInterval(async () => {
  canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
  const image = canvas.toDataURL("image/jpeg", 0.85).split(",")[1];   // base64 tanpa prefix
  const res = await fetch(BASE + "/face/capture", {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: "Bearer " + access_token },
    body: JSON.stringify({ image }),
  });
  const data = await res.json();
  updateProgressBar(data.stored, data.target, data.face_detected);
  if (data.completed) { clearInterval(timer); train(); }             // berhenti otomatis
}, 200);
```

Catatan penting untuk kamera browser:

- `getUserMedia` butuh **secure context**: `https://` atau `http://localhost`.
  Frontend yang di-serve lewat funnel HTTPS sudah aman; halaman yang dibuka via
  `file://` bisa diblokir Chrome.
- Interval 200 ms dan target 100 sampel ≈ **20–25 detik** bila wajah selalu terdeteksi.
- Arahkan wajah pelan-pelan ke kiri/kanan dan sedikit maju/mundur supaya variasi sampel
  bagus (model LBPH sensitif terhadap sudut & pencahayaan).
- Sediakan tombol "ulangi" → `DELETE /face/reset/{nik}` lalu capture lagi bila hasil
  pengenalan kurang bagus.

---

## 6. Konfigurasi

Di `app/services/face_engine.py`:

| Konstanta | Default | Arti |
|---|---|---|
| `SAMPLE_TARGET` | 100 | Minimal sampel sebelum boleh training |
| `SAMPLE_MAX` | 200 | Batas maksimum sampel per user |
| `FACE_SIZE` | (200, 200) | Ukuran crop wajah yang disimpan |
| `CONFIDENCE_THRESHOLD` | 70 | Ambang cocok LBPH (kecil = lebih mirip) |
| `SAMPLE_TARGET`/detektor | `scaleFactor=1.2, minNeighbors=5, minSize=(80,80)` | Parameter Haar Cascade |

`SAMPLE_TARGET` juga dipakai sebagai `target` pada response `/face/capture` &
`/face/status`, jadi frontend otomatis mengikuti bila nilainya diubah.

---

## 7. Label & dataset (aturan penting)

- Folder dataset **harus bernama NIK user yang ada di tabel `Users`**:
  `process-recognation/dataset/<NIK>/001.jpg`.
- Folder yang namanya bukan NIK terdaftar **dilewati saat training** (tidak error) dan
  dihitung di `unlabeled_samples`. Contoh saat ini: folder lama `152024081` (100 foto
  hasil script desktop, memakai NIM) → tidak ikut training.
- Format label `trainer/labels.json` tetap kompatibel dengan script lama:
  `{"0": {"user_id": "<NIK>", "name": "<Nama>"}}`.
- **Migrasi folder lama biar ikut terpakai**: rename folder dataset menjadi NIK user yang
  terdaftar, lalu Admin memanggil `POST /face/retrain`:

  ```bash
  mv process-recognation/dataset/152024081 process-recognation/dataset/<NIK-terdaftar>
  curl -s -X POST "$BASE/face/retrain" -H "Authorization: Bearer $ADMIN_TOKEN"
  ```
- Mengubah `Name` user di DB tidak otomatis mengubah label model — panggil
  `POST /face/retrain` (Admin) setelah perubahan nama.

---

## 8. Troubleshooting

| Gejala | Penyebab / solusi |
|---|---|
| `face_detected: false` terus-menerus | Pencahayaan kurang, wajah terlalu jauh/kecil (< 80 px), atau wajah terpotong. Dekatkan wajah, hadapkan frontal, tambah cahaya |
| `stored` tidak naik padahal wajah terlihat | Wajah terdeteksi sebagai objek kecil; pastikan resolusi kamera ≥ 480×360 dan wajah memenuhi ~30% frame |
| `400 Sampel belum cukup: x/100` | Pengumpulan belum selesai — jalankan `/face/capture` sampai `completed: true` |
| `401` di `/face/capture` | Token hilang/kedaluwarsa (`ACCESS_TOKEN_EXPIRE_MINUTES`, default 120 menit) → login ulang |
| `403 Akses khusus Admin` | `/face/model` & `/face/retrain` hanya untuk role Admin (nama role = "Admin" di tabel `Role`) |
| `recognize` selalu `false` | Model belum dilatih (`POST /face/train`) atau confidence > 70 → tambah/kualitas sampel, lalu train ulang |
| Salah orang terus | Wajah mirip / sampel kurang variatif: `DELETE /face/reset/{nik}` → capture ulang dengan variasi sudut → train |
| `422 Frame tidak dapat didekode` | Body bukan JPEG/PNG base64. Kirim `canvas.toDataURL("image/jpeg", 0.85).split(",")[1]` |
| Model hilang setelah rebuild | Volume `./process-recognation` belum terpasang di compose |
| `cv2.face tidak tersedia` | Image dibangun tanpa `opencv-contrib-python-headless` → `docker compose build backend` |

---

## 9. Testing

```bash
# smoke test end-to-end (register → capture 100 frame → train → recognize → login wajah)
docker exec -i huawei-backend python - < tools/face_api_smoke_test.py
```

Env opsional: `BASE_URL`, `DATASET_DIR`, `SOURCE_NIK` (folder sumber frame uji),
`TEST_NIK`, `TARGET`.

Hasil verifikasi terakhir: **20 PASS / 0 FAIL**, termasuk:

- capture 100 sampel dengan deteksi wajah 69% dari frame uji (frame uji = crop dataset
  yang ditempel ke kanvas 480×360; kamera asli biasanya lebih tinggi);
- recognition frame **hold-out** (tidak dipakai training) → NIK benar, confidence 48.77;
- frame kosong → `recognized: false`; payload rusak → `422`;
- login wajah → JWT valid (dipakai ke `/auth/me`);
- guard otorisasi: tanpa token `401`, user biasa di endpoint Admin `403`,
  reset sampel milik orang lain `403`.

Data uji yang ditinggalkan di sistem (aman dihapus kapan saja):

- Akun uji **`3201234567890097` / password `rahasia123`** (nama "Uji Wajah API")
  dengan 100 sampel wajah di `dataset/3201234567890097/` dan sudah masuk model —
  bisa langsung dipakai demo login wajah. Hapus:
  `DELETE /face/reset/3201234567890097` lalu `POST /face/retrain` (Admin).
- Folder `dataset/152024081` (100 foto lama hasil script desktop, memakai NIM) tetap
  ada dan **tidak** ikut training — cara memakainya ada di bagian 7.

---

## 10. Catatan keamanan

- `/face/recognize` dan `/face/login` bersifat **publik** (tanpa token) karena dipakai
  untuk identifikasi/login. Artinya siapa pun yang bisa mengirim frame bisa mencoba
  menebak identitas user. Untuk produksi: batasi dengan rate limit, aktifkan
  `liveness detection` (mis. blink/turn challenge), dan/atau taruh di balik jaringan
  internal.
- Login wajah **tidak menggantikan** password: NIK+password tetap dipakai untuk
  registrasi/akun. Login wajah adalah alternatif praktis.
- Dataset wajah = data pribadi (biometrik). Simpan folder `process-recognation/dataset`
  di volume terbatas akses dan jangan commit ke Git publik.
- Default akun seed `admin/admin123` — segera ganti.
- Detail kredensial DB & deploy ada di `integration.md` (jangan dibagikan publik).

CEKECKEKCKEKCKEKEKCEKECKCEKCEKKECKECK

Ya — dan host ini memang server itu sendiri (hostname ramirosservers, host yang sama dengan funnel).

Bukti yang baru saya cek:

  Container   huawei-backend  Up 38 menit, ports 127.0.0.1:8000->8000/tcp (loopback saja)
  Image       sha256:f4309b6… created 2026-11-12T01:55:51Z — build final dari repo
  Kode        penanda patch terakhir ada di dalam container (face_engine "TIDAK membuat folder",
              routers/face.py "my_samples") → image = kode repo, bukan versi lama
  Funnel      https://ramirosservers.tail2d4b04.ts.net  →  /api proxy http://127.0.0.1:8000
  Uji publik  GET /api/                → {"status":"ok","app":"Huawei ICT Backend"}
              GET /api/face/status     → HTTP 401 (butuh token, sesuai desain)
              POST /api/face/recognize → 422 untuk payload rusak (sebelumnya terverifikasi)

Jadi endpoint face sudah hidup dan bisa diakses publik, contoh:

  POST https://ramirosservers.tail2d4b04.ts.net/api/face/capture
  POST https://ramirosservers.tail2d4b04.ts.net/api/face/login
  Docs: https://ramirosservers.tail2d4b04.ts.net/api/docs

Yang belum / perlu keputusan Anda (bukan bagian deploy):
  - Belum ada commit ke git (perubahan masih working tree).
  - Password admin seed masih admin123, dan /face/recognize + /face/login belum ada rate limit/liveness.
  - Kalau frontend lomba Anda di-serve lewat HTTPS, getUserMedia aman; kalau dibuka dari lokal pakai
    http://localhost, arahkan Base URL ke http://127.0.0.1:8000 (tanpa /api).

Penting untuk demo: endpoint publik lewat funnel sudah pasti jalan, tapi kualitas pengenalan tergantung
kamera klien. Folder dataset/152024081 (100 foto lama) belum ikut model — kalau mau dipakai demo,
rename foldernya ke NIK user terdaftar lalu POST /api/face/retrain sebagai Admin.
