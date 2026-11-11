
import cv2
import numpy as np
import os
import json
import re

from pathlib import Path

# ==========================================
# KONFIGURASI
# ==========================================

BASE_DIR = Path(__file__).parent

DATASET_DIR = BASE_DIR / "dataset"
TRAINER_DIR = BASE_DIR / "trainer"

MODEL_PATH = TRAINER_DIR / "face_model.yml"
LABEL_PATH = TRAINER_DIR / "labels.json"

SAMPLE_TARGET = 100
FACE_SIZE = (200, 200)

# LBPH threshold: semakin kecil confidence,
# semakin mirip wajah yang dikenali.
CONFIDENCE_THRESHOLD = 70

DATASET_DIR.mkdir(exist_ok=True)
TRAINER_DIR.mkdir(exist_ok=True)

# Face detector Haar Cascade
face_detector_path = (
    Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
)

# Periksa apakah file tersedia
if not face_detector_path.is_file():
    raise FileNotFoundError(
        f"Haar Cascade tidak ditemukan: {face_detector_path}\n"
        "OpenCV 5 tidak menyertakan file ini. Jalankan "
        "`python -m pip install -r requirements.txt` dari root proyek "
        "untuk memasang OpenCV 4.x."
    )

# Load model deteksi wajah
face_detector = cv2.CascadeClassifier(
    str(face_detector_path)
)

# Pastikan model berhasil dimuat
if face_detector.empty():
    raise RuntimeError(
        "Gagal memuat Haar Cascade Classifier!"
    )

print("Face detector berhasil dimuat!")
print("Model:", face_detector_path)

# ==========================================
# FUNGSI DETEKSI WAJAH
# ==========================================

def detect_face(gray):

    faces = face_detector.detectMultiScale(
        gray,
        scaleFactor=1.2,
        minNeighbors=5,
        minSize=(80, 80)
    )

    if len(faces) == 0:
        return None

    # Ambil wajah terbesar
    face = max(
        faces,
        key=lambda f: f[2] * f[3]
    )

    x, y, w, h = face

    face_roi = gray[y:y+h, x:x+w]

    face_roi = cv2.resize(
        face_roi,
        FACE_SIZE
    )

    return face_roi, (x, y, w, h)


# ==========================================
# 1. REGISTRASI WAJAH
# ==========================================

def capture_faces():

    print("\n===== REGISTRASI WAJAH =====")

    user_id = input("Masukkan ID / NIM: ").strip()
    user_name = input("Masukkan nama: ").strip()

    if not user_id or not user_name:
        print("ID dan nama wajib diisi!")
        return

    # Validasi ID untuk nama folder
    if not re.fullmatch(r"[A-Za-z0-9_-]+", user_id):
        print("ID hanya boleh berisi huruf, angka, - dan _")
        return

    user_dir = DATASET_DIR / user_id
    user_dir.mkdir(exist_ok=True)

    existing = list(user_dir.glob("*.jpg"))

    if len(existing) >= SAMPLE_TARGET:
        print("User sudah memiliki 50 sampel.")
        return

    # Simpan identitas user
    metadata_path = DATASET_DIR / "users.json"

    if metadata_path.exists():
        with open(metadata_path, "r") as f:
            users = json.load(f)
    else:
        users = {}

    users[user_id] = {
        "name": user_name
    }

    with open(metadata_path, "w") as f:
        json.dump(users, f, indent=4)

    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Kamera tidak dapat dibuka.")
        return

    count = len(existing)

    print("\nArahkan wajah ke kamera.")
    print("Tekan SPACE untuk mengambil sampel.")
    print("Tekan Q untuk membatalkan.")

    while count < SAMPLE_TARGET:

        ret, frame = cap.read()

        if not ret:
            break

        frame = cv2.flip(frame, 1)

        gray = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2GRAY
        )

        result = detect_face(gray)

        if result is not None:

            face_roi, (x, y, w, h) = result

            cv2.rectangle(
                frame,
                (x, y),
                (x+w, y+h),
                (0, 255, 0),
                2
            )

            cv2.putText(
                frame,
                "Face detected",
                (x, y-10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )

            cv2.putText(
                frame,
                "Press SPACE to capture",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )

        else:
            cv2.putText(
                frame,
                "No face detected",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 255),
                2
            )

        cv2.putText(
            frame,
            f"Samples: {count}/{SAMPLE_TARGET}",
            (10, 65),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 255),
            2
        )

        cv2.imshow("Face Registration", frame)

        key = cv2.waitKey(1) & 0xFF

        if key == ord('q'):
            break

        # Capture hanya ketika wajah terdeteksi
        if key == 32 and result is not None:

            count += 1

            filename = user_dir / f"{count:03d}.jpg"

            cv2.imwrite(
                str(filename),
                face_roi
            )

            print(f"Captured: {count}/{SAMPLE_TARGET}")

    cap.release()
    cv2.destroyAllWindows()

    if count == SAMPLE_TARGET:
        print("\nRegistrasi 50 sampel berhasil!")
    else:
        print(f"\nRegistrasi dihentikan. Terkumpul: {count}")


# ==========================================
# 2. TRAINING MODEL LBPH
# ==========================================

def train_model():

    print("\n===== TRAINING FACE RECOGNITION =====")

    if not hasattr(cv2, "face"):
        print("Modul cv2.face tidak tersedia.")
        print("Install opencv-contrib-python.")
        return

    recognizer = cv2.face.LBPHFaceRecognizer_create()

    faces = []
    labels = []

    label_mapping = {}
    label_id = 0

    for user_dir in sorted(DATASET_DIR.iterdir()):

        if not user_dir.is_dir():
            continue

        image_files = sorted(
            user_dir.glob("*.jpg")
        )

        if len(image_files) == 0:
            continue

        for image_path in image_files:

            image = cv2.imread(
                str(image_path),
                cv2.IMREAD_GRAYSCALE
            )

            if image is None:
                continue

            image = cv2.resize(
                image,
                FACE_SIZE
            )

            faces.append(image)
            labels.append(label_id)

        # Ambil identitas dari users.json
        metadata_path = DATASET_DIR / "users.json"

        with open(metadata_path, "r") as f:
            users = json.load(f)

        user_id = user_dir.name

        if user_id not in users:
            continue

        label_mapping[str(label_id)] = {
            "user_id": user_id,
            "name": users[user_id]["name"]
        }

        print(
            f"Label {label_id}: "
            f"{users[user_id]['name']} "
            f"({len(image_files)} samples)"
        )

        label_id += 1

    if len(faces) == 0:
        print("Dataset masih kosong.")
        return

    recognizer.train(
        faces,
        np.array(labels, dtype=np.int32)
    )

    recognizer.write(str(MODEL_PATH))

    with open(LABEL_PATH, "w") as f:
        json.dump(label_mapping, f, indent=4)

    print("\nTraining berhasil!")
    print(f"Total sampel: {len(faces)}")
    print(f"Total user: {label_id}")


# ==========================================
# 3. FACE RECOGNITION
# ==========================================

def recognize_faces():

    print("\n===== FACE RECOGNITION =====")

    if not MODEL_PATH.exists() or not LABEL_PATH.exists():
        print("Model belum tersedia. Lakukan training dahulu.")
        return

    recognizer = cv2.face.LBPHFaceRecognizer_create()

    recognizer.read(str(MODEL_PATH))

    with open(LABEL_PATH, "r") as f:
        labels = json.load(f)

    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Kamera tidak dapat dibuka.")
        return

    print("Face recognition aktif.")
    print("Tekan Q untuk keluar.")

    while True:

        ret, frame = cap.read()

        if not ret:
            break

        frame = cv2.flip(frame, 1)

        gray = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2GRAY
        )

        result = detect_face(gray)

        if result is not None:

            face_roi, (x, y, w, h) = result

            label, confidence = recognizer.predict(
                face_roi
            )

            # Confidence lebih kecil = lebih cocok
            if (
                str(label) in labels
                and confidence <= CONFIDENCE_THRESHOLD
            ):

                user = labels[str(label)]

                name = user["name"]
                user_id = user["user_id"]

                display_text = name

                color = (0, 255, 0)

                status = "RECOGNIZED"

            else:

                display_text = "Unknown"

                user_id = "-"

                color = (0, 0, 255)

                status = "NOT RECOGNIZED"

            # Bounding box
            cv2.rectangle(
                frame,
                (x, y),
                (x+w, y+h),
                color,
                2
            )

            # Nama user
            cv2.putText(
                frame,
                display_text,
                (x, y-35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                color,
                2
            )

            # ID user
            cv2.putText(
                frame,
                f"ID: {user_id}",
                (x, y-10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                color,
                2
            )

            # Confidence
            cv2.putText(
                frame,
                f"Distance: {confidence:.2f}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )

            cv2.putText(
                frame,
                status,
                (10, 65),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                color,
                2
            )

        else:

            cv2.putText(
                frame,
                "No face detected",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 255),
                2
            )

        cv2.imshow(
            "Automatic Face Recognition",
            frame
        )

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


# ==========================================
# MENU UTAMA
# ==========================================

def main():

    while True:

        print("\n================================")
        print("       FACE RECOGNITION")
        print("================================")
        print("1. Register / Capture Face")
        print("2. Train Model")
        print("3. Start Face Recognition")
        print("4. Exit")
        print("================================")

        choice = input("Pilih menu: ")

        if choice == "1":
            capture_faces()

        elif choice == "2":
            train_model()

        elif choice == "3":
            recognize_faces()

        elif choice == "4":
            print("Program selesai.")
            break

        else:
            print("Pilihan tidak valid!")


if __name__ == "__main__":
    main()
