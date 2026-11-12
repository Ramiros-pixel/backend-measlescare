#!/usr/bin/env python3
"""
Smoke test end-to-end API face recognition (register -> capture -> train ->
recognize -> login wajah).

Butuh: opencv (cv2) untuk menyiapkan frame uji dari file dataset.

Cara jalan:
  # dari dalam container backend
  docker exec -i huawei-backend python - < tools/face_api_smoke_test.py

  # atau di host yang punya opencv & akses API
  BASE_URL=http://127.0.0.1:8000 python3 tools/face_api_smoke_test.py

Env:
  BASE_URL    default http://127.0.0.1:8000
  DATASET_DIR default /app/process-recognation/dataset
  SOURCE_NIK  default 152024081 (folder dataset sumber frame uji)
  TEST_NIK    default 3201234567890097 (akun uji yang didaftarkan)
  TEST_PASS   default rahasia123
  TARGET      default 100 (jumlah sampel wajah)
"""

import base64
import glob
import json
import os
import urllib.error
import urllib.request

import cv2
import numpy as np

BASE = os.getenv("BASE_URL", "http://127.0.0.1:8000")
DATASET = os.getenv("DATASET_DIR", "/app/process-recognation/dataset")
SOURCE_NIK = os.getenv("SOURCE_NIK", "152024081")
TEST_NIK = os.getenv("TEST_NIK", "3201234567890097")
TEST_PASS = os.getenv("TEST_PASS", "rahasia123")
TARGET = int(os.getenv("TARGET", "100"))
ADMIN_NIK = os.getenv("ADMIN_NIK", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "admin123")

PASS, FAIL = [], []


def check(name: str, ok: bool, detail: str = "") -> None:
    (PASS if ok else FAIL).append(name)
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}{(' -> ' + detail) if detail else ''}")


def req(method: str, path: str, body=None, token=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, method=method)
    r.add_header("Content-Type", "application/json")
    if token:
        r.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            return resp.status, json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"{}")
        except Exception:
            return e.code, {}


# ---------- frame uji dari dataset ----------

def frame_b64(path: str, flip: bool = False, canvas=(480, 360)) -> str:
    """
    Tempel crop wajah ke kanvas abu-abu lebih besar supaya menyerupai frame
    kamera sungguhan (detector Haar butuh sedikit margin di sekitar wajah).
    """
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    h, w = canvas
    out = np.full((h, w), 128, dtype=np.uint8)
    fh, fw = img.shape
    scale = min(h * 0.7 / fh, w * 0.7 / fw)
    face = cv2.resize(img, (int(fw * scale), int(fh * scale)))
    if flip:
        face = cv2.flip(face, 1)
    fh, fw = face.shape
    y, x = (h - fh) // 2, (w - fw) // 2
    out[y:y + fh, x:x + fw] = face
    ok, buf = cv2.imencode(".jpg", out, [cv2.IMWRITE_JPEG_QUALITY, 92])
    if not ok:
        raise RuntimeError("gagal encode frame uji")
    return base64.b64encode(buf.tobytes()).decode()


def blank_frame_b64(canvas=(480, 360)) -> str:
    out = np.full(canvas, 128, dtype=np.uint8)
    ok, buf = cv2.imencode(".jpg", out)
    return base64.b64encode(buf.tobytes()).decode()


def main() -> int:
    files = sorted(glob.glob(os.path.join(DATASET, SOURCE_NIK, "*.jpg")))
    print(f"Frame uji dari: {DATASET}/{SOURCE_NIK} ({len(files)} file)")
    if len(files) < 60:
        print("Dataset sumber kurang dari 60 file — tidak cukup untuk uji.")
        return 2

    print("\n=== 1. Register akun (NIK + Nama + Tgl lahir) ===")
    s, d = req("POST", "/auth/register", {
        "NIK": TEST_NIK, "Name": "Uji Wajah API", "Tgl_lahir": "2001-02-03",
        "Alamat": "Test", "password": TEST_PASS, "id_Role": "R2",
    })
    check("POST /auth/register", s in (201, 409), f"HTTP {s}"

          + (f" detail={d.get('detail')}" if s == 409 else ""))

    print("\n=== 2. Login akun uji (JWT) ===")
    s, d = req("POST", "/auth/login", {"NIK": TEST_NIK, "password": TEST_PASS})
    check("POST /auth/login", s == 200, f"HTTP {s}")
    tok = d.get("access_token")
    if not tok:
        print("Tidak dapat token, uji dihentikan.")
        return 2

    print("\n=== 3. Guard: tanpa token ===")
    s, _ = req("POST", "/face/capture", {"image": blank_frame_b64()})
    check("POST /face/capture tanpa token -> 401", s == 401, f"HTTP {s}")

    print("\n=== 4. Status + guard training ===")
    s, _ = req("DELETE", f"/face/reset/{TEST_NIK}", token=tok)
    check("DELETE /face/reset/{nik} (bersihkan sisa uji)", s == 200, f"HTTP {s}")
    s, d = req("GET", "/face/status", token=tok)
    check("GET /face/status", s == 200 and d.get("my_samples") == 0,
          f"HTTP {s} my_samples={d.get('my_samples')}")
    s, d = req("POST", "/face/train", token=tok)
    check("POST /face/train dgn 0 sampel -> 400", s == 400, f"HTTP {s} detail={d.get('detail')}")

    print(f"\n=== 5. Capture {TARGET} frame (tanpa ketik apa pun) ===")
    attempts, stored, detected_frames = 0, 0, 0
    idx = 0
    max_attempts = TARGET * 3
    while stored < TARGET and attempts < max_attempts:
        i = (idx % 50) + 1
        flip = idx >= 50  # separuh frame dari 1-50 normal, separuh di-flip
        if idx >= 100:
            i = ((idx - 100) % 50) + 1
        payload = {"image": frame_b64(files[i - 1], flip=flip and idx < 100)}
        s, d = req("POST", "/face/capture", payload, token=tok)
        attempts += 1
        idx += 1
        if s != 200:
            print(f"    entry gagal HTTP {s}: {d}")
            break
        stored = d["stored"]
        detected_frames += 1 if d["face_detected"] else 0
    rate = 100.0 * detected_frames / max(attempts, 1)
    check(f"POST /face/capture x{attempts} -> {stored} sampel tersimpan",
          stored >= TARGET, f"deteksi wajah {rate:.0f}% dari frame")
    s, d = req("GET", "/face/status", token=tok)
    check("GET /face/status menunjukkan my_samples >= target",
          s == 200 and d.get("my_samples", 0) >= TARGET, f"my_samples={d.get('my_samples')}")

    print("\n=== 6. Training LBPH (label otomatis dari tabel Users) ===")
    s, d = req("POST", "/face/train", token=tok)
    check("POST /face/train", s == 200,
          f"HTTP {s} total_users={d.get('total_users')} detail={d.get('detail')}")

    print("\n=== 7. Recognize frame yang TIDAK dipakai training (hold-out) ===")
    s, d = req("POST", "/face/recognize", {"image": frame_b64(files[59])})  # file ke-60
    check("POST /face/recognize -> dikenali sebagai akun uji",
          s == 200 and d.get("recognized") and d.get("user_id") == TEST_NIK,
          f"HTTP {s} result={d}")
    s, d = req("POST", "/face/recognize", {"image": blank_frame_b64()})
    check("POST /face/recognize frame kosong -> recognized=false",
          s == 200 and d.get("recognized") is False, f"HTTP {s} result={d}")
    s, d = req("POST", "/face/recognize", {"image": "bukan-base64-valid"})
    check("POST /face/recognize payload rusak -> 422", s == 422, f"HTTP {s}")

    print("\n=== 8. Login dengan wajah ===")
    s, d = req("POST", "/face/login", {"image": frame_b64(files[59])})
    ok = s == 200 and d.get("user", {}).get("NIK") == TEST_NIK and d.get("access_token")
    check("POST /face/login -> JWT + profil user", bool(ok),
          f"HTTP {s} nik={d.get('user', {}).get('NIK')}")
    face_tok = d.get("access_token")
    if face_tok:
        s, d = req("GET", "/auth/me", token=face_tok)
        check("JWT hasil login wajah dipakai ke /auth/me", s == 200 and d.get("NIK") == TEST_NIK,
              f"HTTP {s} NIK={d.get('NIK')}")
    s, d = req("POST", "/face/login", {"image": blank_frame_b64()})
    check("POST /face/login wajah tak dikenal -> 401", s == 401, f"HTTP {s}")

    print("\n=== 9. Otorisasi ===")
    s, d = req("GET", "/face/model", token=tok)
    check("GET /face/model sebagai user biasa -> 403", s == 403, f"HTTP {s}")
    s, d = req("POST", "/face/retrain", {}, token=tok)
    check("POST /face/retrain sebagai user biasa -> 403", s == 403, f"HTTP {s}")
    s, d = req("DELETE", "/face/reset/3201234567890001", token=tok)
    check("DELETE /face/reset/{nik lain} sebagai user biasa -> 403", s == 403, f"HTTP {s}")

    s, d = req("POST", "/auth/login", {"NIK": ADMIN_NIK, "password": ADMIN_PASS})
    admin_tok = d.get("access_token")
    if admin_tok:
        s, d = req("GET", "/face/model", token=admin_tok)
        check("GET /face/model sebagai admin", s == 200 and d.get("model_exists") is True,
              f"HTTP {s} model_users={d.get('model_users')} total_samples={d.get('total_samples')} "
              f"trained_at={d.get('trained_at')}")
        s, d = req("POST", "/face/retrain", {}, token=admin_tok)
        check("POST /face/retrain sebagai admin", s == 200,
              f"HTTP {s} total_users={d.get('total_users')} detail={d.get('detail')}")

    print(f"\n===== HASIL: {len(PASS)} PASS / {len(FAIL)} FAIL =====")
    if FAIL:
        print("Gagal:", ", ".join(FAIL))
    return 0 if not FAIL else 1


if __name__ == "__main__":
    raise SystemExit(main())
