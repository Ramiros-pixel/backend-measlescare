"""
Face engine: deteksi, penyimpanan sampel, training LBPH, dan pengenalan wajah.

Mengadaptasi logika dari `process-recognation/collect.py` (versi desktop)
untuk dipakai oleh API backend:
  - dataset per-user di  process-recognation/dataset/<NIK>/NNN.jpg
  - model LBPH di        process-recognation/trainer/face_model.yml
  - label mapping di     process-recognation/trainer/labels.json

Label diambil dari tabel `Users` (NIK + Name) sehingga hasil pengenalan
otomatis ter-label dengan identitas user yang terdaftar.
"""

import json
import threading

import cv2
import numpy as np
from pathlib import Path

from app.core.config import settings

# ==========================================
# KONFIGURASI
# ==========================================

FACE_DIR = Path(__file__).resolve().parents[2] / "process-recognation" / "dataset"
TRAINER_DIR = FACE_DIR.parent / "trainer"

MODEL_PATH = TRAINER_DIR / "face_model.yml"
LABEL_PATH = TRAINER_DIR / "labels.json"

SAMPLE_TARGET = 100          # jumlah sampel minimal sebelum boleh training
SAMPLE_MAX = 200             # batas sampel per user
FACE_SIZE = (200, 200)
CONFIDENCE_THRESHOLD = 70    # LBPH: semakin kecil = semakin yakin

TRAIN_LOCK = threading.Lock()   # training LBPH tidak boleh berjalan paralel

# ==========================================
# DETEKSI WAJAH
# ==========================================

_cascade = None


def _face_detector() -> cv2.CascadeClassifier:
    """Load Haar Cascade sekali, dipakai ulang antar request."""
    global _cascade
    if _cascade is None:
        cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
        detector = cv2.CascadeClassifier(str(cascade_path))
        if detector.empty():
            raise RuntimeError("Gagal memuat Haar Cascade Classifier")
        _cascade = detector
    return _cascade


def detect_face(gray):
    """
    Deteksi wajah dari citra grayscale.
    Return (face_roi_200x200, (x, y, w, h)) atau None bila tidak ada wajah.
    """
    faces = _face_detector().detectMultiScale(
        gray,
        scaleFactor=1.2,
        minNeighbors=5,
        minSize=(80, 80),
    )
    if len(faces) == 0:
        return None

    # Ambil wajah terbesar (paling dekat ke kamera)
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    face_roi = gray[y:y + h, x:x + w]
    face_roi = cv2.resize(face_roi, FACE_SIZE)
    return face_roi, (x, y, w, h)


# ==========================================
# DATASET
# ==========================================

def user_dir(nik: str) -> Path:
    """Folder dataset seorang user (dibuat bila belum ada)."""
    d = FACE_DIR / nik
    d.mkdir(parents=True, exist_ok=True)
    return d


def count_samples(nik: str) -> int:
    """
    Jumlah sampel wajah yang sudah tersimpan untuk seorang user.
    Membaca saja — TIDAK membuat folder, supaya endpoint status tidak
    meninggalkan folder kosong di dataset.
    """
    d = FACE_DIR / nik
    if not d.is_dir():
        return 0
    return len(list(d.glob("*.jpg")))


def count_all_samples() -> int:
    """Total sampel wajah seluruh folder di dataset."""
    return sum(len(list(d.glob("*.jpg"))) for d in FACE_DIR.iterdir() if d.is_dir())


def dataset_counts(known_niks: set[str] | None = None) -> tuple[int, int]:
    """
    Hitung (sampel_berlabel, sampel_tanpa_label) di dataset.

    Folder dataset yang namanya bukan NIK user terdaftar (mis. folder lama
    hasil script desktop dengan NIM) TIDAK ikut dilatih, jadi dipisahkan
    agar angka pada status tidak menyesatkan.
    """
    labeled = unlabeled = 0
    if not FACE_DIR.exists():
        return 0, 0
    for d in FACE_DIR.iterdir():
        if not d.is_dir():
            continue
        n = len(list(d.glob("*.jpg")))
        if known_niks is None or d.name in known_niks:
            labeled += n
        else:
            unlabeled += n
    return labeled, unlabeled


def model_trained_at() -> str | None:
    """Waktu training model aktif (ISO format) atau None bila belum ada."""
    if not MODEL_PATH.exists():
        return None
    from datetime import datetime, timezone

    ts = MODEL_PATH.stat().st_mtime
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def save_sample(nik: str, gray) -> tuple[int, bool]:
    """
    Deteksi wajah dari frame grayscale lalu simpan sebagai sampel.
    Return (jumlah_sampel_terkini, apakah_frame_memuat_wajah).
    Frame tanpa wajah TIDAK disimpan.
    """
    result = detect_face(gray)
    if result is None:
        return count_samples(nik), False

    face_roi, _ = result
    d = user_dir(nik)

    # Nama file lanjut dari sampel terakhir: 001.jpg, 002.jpg, ...
    existing = sorted(int(p.stem) for p in d.glob("*.jpg") if p.stem.isdigit())
    next_num = (existing[-1] + 1) if existing else 1
    if next_num > SAMPLE_MAX:
        return SAMPLE_MAX, True

    cv2.imwrite(str(d / f"{next_num:03d}.jpg"), face_roi)
    # Hitung ulang dari disk (bukan pakai next_num) agar tetap benar bila
    # penomoran file berlubang, mis. setelah sebagian sampel dihapus.
    return count_samples(nik), True


def reset_samples(nik: str) -> int:
    """Hapus seluruh sampel wajah seorang user. Return jumlah yang terhapus."""
    d = FACE_DIR / nik
    if not d.is_dir():
        return 0
    removed = 0
    for p in d.glob("*.jpg"):
        p.unlink()
        removed += 1
    return removed


# ==========================================
# TRAINING (sinkron, dilindungi lock)
# ==========================================

def train_model() -> dict:
    """
    Training ulang model LBPH dari seluruh dataset di disk.
    Label diambil dari tabel `Users` — user tanpa akun terdaftar dilewati.
    Return ringkasan hasil training.
    """
    from app.db.session import SessionLocal
    from app.models.gejala import User

    with TRAIN_LOCK:
        if not hasattr(cv2, "face"):
            raise RuntimeError(
                "cv2.face tidak tersedia. Install 'opencv-contrib-python-headless'."
            )

        # Mapping NIK -> identitas dari database (sumber label)
        db = SessionLocal()
        try:
            users = {u.NIK: u.Name for u in db.query(User).all()}
        finally:
            db.close()

        recognizer = cv2.face.LBPHFaceRecognizer_create()
        faces: list = []
        labels: list = []
        label_mapping: dict = {}
        label_id = 0

        for udir in sorted(FACE_DIR.iterdir()):
            if not udir.is_dir():
                continue
            nik = udir.name
            if nik not in users:
                continue  # folder sampah / user sudah dihapus -> tidak dilatih

            image_files = sorted(udir.glob("*.jpg"))
            if not image_files:
                continue

            for image_path in image_files:
                image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
                if image is None:
                    continue
                image = cv2.resize(image, FACE_SIZE)
                faces.append(image)
                labels.append(label_id)

            label_mapping[str(label_id)] = {
                "user_id": nik,
                "name": users[nik],
            }
            label_id += 1

        if len(faces) == 0 or label_id == 0:
            raise ValueError("Dataset kosong / tidak ada user terdaftar untuk dilatih.")

        recognizer.train(faces, np.array(labels, dtype=np.int32))

        # Tulis ke file sementara lalu rename atomik agar model lama tidak rusak
        TRAINER_DIR.mkdir(parents=True, exist_ok=True)
        tmp_model = MODEL_PATH.with_suffix(".yml.tmp")
        tmp_label = LABEL_PATH.with_suffix(".json.tmp")
        recognizer.write(str(tmp_model))
        tmp_model.replace(MODEL_PATH)
        with open(tmp_label, "w") as f:
            json.dump(label_mapping, f, indent=4)
        tmp_label.replace(LABEL_PATH)

        return {
            "total_samples": len(faces),
            "total_users": label_id,
            "model_path": str(MODEL_PATH.name),
        }


# ==========================================
# PENGENALAN
# ==========================================

class _RecognizerCache:
    """Cache model LBPH di memori; reload otomatis saat file berubah."""

    def __init__(self):
        self._recognizer = None
        self._labels: dict = {}
        self._mtime: float = 0.0

    def get(self):
        if not (MODEL_PATH.exists() and LABEL_PATH.exists()):
            return None, {}

        latest_mtime = max(MODEL_PATH.stat().st_mtime, LABEL_PATH.stat().st_mtime)
        if self._recognizer is None or latest_mtime > self._mtime:
            recognizer = cv2.face.LBPHFaceRecognizer_create()
            recognizer.read(str(MODEL_PATH))
            with open(LABEL_PATH) as f:
                self._labels = json.load(f)
            self._recognizer = recognizer
            self._mtime = latest_mtime
        return self._recognizer, self._labels


_recognizer_cache = _RecognizerCache()


def recognize(gray) -> dict | None:
    """
    Kenali wajah dari frame grayscale.
    Return {"user_id": NIK, "name": Nama, "confidence": float} bila dikenali
    (confidence <= threshold), selain itu None (unknown / tidak ada wajah).
    """
    recognizer, label_mapping = _recognizer_cache.get()
    if recognizer is None:
        return None

    result = detect_face(gray)
    if result is None:
        return None

    face_roi, _ = result
    label, confidence = recognizer.predict(face_roi)

    if str(label) in label_mapping and confidence <= CONFIDENCE_THRESHOLD:
        entry = label_mapping[str(label)]
        return {
            "user_id": entry["user_id"],
            "name": entry["name"],
            "confidence": round(float(confidence), 2),
        }
    return None
