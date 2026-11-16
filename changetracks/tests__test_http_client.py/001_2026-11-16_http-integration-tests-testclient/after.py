"""
HTTP Integration tests for MeaslesWatch AI API using FastAPI TestClient.
Project: MeaslesWatch AI — Huawei ICT Competition 2026–2027
Team: Inovexa

Menguji request HTTP multipart/form-data nyata melalui socket TestClient:
1. Upload gambar valid PNG (HTTP 200 & validasi Pydantic schema).
2. Upload gambar valid JPEG (HTTP 200 & validasi Pydantic schema).
3. Upload gambar valid WebP (HTTP 200 & validasi Pydantic schema).
4. Upload citra klinis riil dari dataset (MSID_measles11.png) -> Prediksi 'Measles'.
5. Upload file kosong -> HTTP 400 Bad Request.
6. Upload format tidak didukung (text, PDF, binary non-image) -> HTTP 415 Unsupported Media Type.
7. Upload gambar rusak (decode failure) -> HTTP 422 Unprocessable Content.
8. Upload file melebihi 10 MB -> HTTP 413 Content Too Large.
9. Penanganan kegagalan model (ModelLoadError) -> HTTP 503 Service Unavailable (safe message).
10. Penanganan kegagalan runtime (InferenceRuntimeError) -> HTTP 500 Internal Server Error (safe message).
"""

from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Ensure backend root is on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.routers.measles import router
from app.schemas.measles import (
    MeaslesClassEnum,
    MeaslesPredictResponse,
)
from app.services.measles_engine import (
    CLASS_NAMES,
    InferenceRuntimeError,
    ModelLoadError,
)


class TestMeaslesHttpIntegration(unittest.TestCase):
    """Suite pengujian integrasi HTTP sungguhan via TestClient."""

    @classmethod
    def setUpClass(cls):
        """Buat temporary FastAPI application dan TestClient."""
        cls.app = FastAPI()
        cls.app.include_router(router)
        cls.client = TestClient(cls.app)

        # 1. Synthetic valid PNG
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        img[:, :, 0] = 50
        img[:, :, 1] = 120
        img[:, :, 2] = 200
        _, buf_png = cv2.imencode(".png", img)
        cls.valid_png = buf_png.tobytes()

        # 2. Synthetic valid JPEG
        _, buf_jpg = cv2.imencode(".jpg", img)
        cls.valid_jpg = buf_jpg.tobytes()

        # 3. Synthetic valid WebP
        _, buf_webp = cv2.imencode(".webp", img)
        cls.valid_webp = buf_webp.tobytes()

        # 4. Dataset test sample path
        cls.real_sample_path = (
            BASE_DIR.parent / "dataset_split" / "test" / "Measles" / "MSID_measles11.png"
        )

    def test_01_http_multipart_valid_png(self):
        """1. Request HTTP multipart dengan PNG valid mengembalikan HTTP 200 & schema valid."""
        response = self.client.post(
            "/v1/measles/predict",
            files={"file": ("test.png", self.valid_png, "image/png")},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        validated = MeaslesPredictResponse(**data)
        self.assertIn(validated.prediction.value, CLASS_NAMES)
        self.assertGreaterEqual(validated.confidence, 0.0)
        self.assertLessEqual(validated.confidence, 1.0)
        self.assertGreaterEqual(validated.inference_time_ms, 0.0)

    def test_02_http_multipart_valid_jpeg(self):
        """2. Request HTTP multipart dengan JPEG valid mengembalikan HTTP 200 & schema valid."""
        response = self.client.post(
            "/v1/measles/predict",
            files={"file": ("test.jpg", self.valid_jpg, "image/jpeg")},
        )
        self.assertEqual(response.status_code, 200)
        validated = MeaslesPredictResponse(**response.json())
        self.assertIn(validated.prediction.value, CLASS_NAMES)

    def test_03_http_multipart_valid_webp(self):
        """3. Request HTTP multipart dengan WebP valid mengembalikan HTTP 200 & schema valid."""
        response = self.client.post(
            "/v1/measles/predict",
            files={"file": ("test.webp", self.valid_webp, "image/webp")},
        )
        self.assertEqual(response.status_code, 200)
        validated = MeaslesPredictResponse(**response.json())
        self.assertIn(validated.prediction.value, CLASS_NAMES)

    def test_04_http_multipart_real_dataset_image(self):
        """4. Request HTTP multipart citra medis riil (MSID_measles11.png) -> Prediksi 'Measles'."""
        if not self.real_sample_path.exists():
            self.skipTest(f"Sample citra riil tidak ditemukan pada: {self.real_sample_path}")

        with open(self.real_sample_path, "rb") as f:
            real_bytes = f.read()

        response = self.client.post(
            "/v1/measles/predict",
            files={"file": ("MSID_measles11.png", real_bytes, "image/png")},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["prediction"], "Measles")
        self.assertEqual(data["class_index"], 4)
        self.assertGreater(data["confidence"], 0.95)

    def test_05_http_empty_file_rejected_400(self):
        """5. Request HTTP dengan file kosong (0 byte) ditolak dengan HTTP 400 Bad Request."""
        response = self.client.post(
            "/v1/measles/predict",
            files={"file": ("empty.png", b"", "image/png")},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("kosong", response.json().get("detail", "").lower())

    def test_06_http_unsupported_format_rejected_415(self):
        """6. Request HTTP dengan format bukan JPEG/PNG/WebP ditolak dengan HTTP 415."""
        unsupported_files = [
            ("notes.txt", b"This is a text file", "text/plain"),
            ("doc.pdf", b"%PDF-1.4 binary content...", "application/pdf"),
            ("zeros.bin", b"\x00" * 32, "application/octet-stream"),
        ]
        for fname, content, ctype in unsupported_files:
            response = self.client.post(
                "/v1/measles/predict",
                files={"file": (fname, content, ctype)},
            )
            self.assertEqual(
                response.status_code,
                415,
                f"File {fname} ({ctype}) tidak menghasilkan 415: {response.status_code}",
            )
            self.assertIn("tidak didukung", response.json().get("detail", "").lower())

    def test_07_http_corrupted_image_rejected_422(self):
        """7. Request HTTP dengan citra korup (magic bytes valid, body rusak) -> HTTP 422."""
        corrupted_png = b"\x89PNG\r\n\x1a\n" + b"GARBAGE_NON_IMAGE_BYTES_1234567890"
        response = self.client.post(
            "/v1/measles/predict",
            files={"file": ("corrupt.png", corrupted_png, "image/png")},
        )
        self.assertEqual(response.status_code, 422)
        self.assertIn("rusak", response.json().get("detail", "").lower())

    def test_08_http_oversized_file_rejected_413(self):
        """8. Request HTTP dengan berkas > 10 MB ditolak dengan HTTP 413 Content Too Large."""
        oversized_payload = b"\x89PNG\r\n\x1a\n" + b"A" * (10 * 1024 * 1024 + 1024)
        response = self.client.post(
            "/v1/measles/predict",
            files={"file": ("giant.png", oversized_payload, "image/png")},
        )
        self.assertEqual(response.status_code, 413)
        self.assertIn("10 mb", response.json().get("detail", "").lower())

    def test_09_http_model_load_failure_503(self):
        """9. Kegagalan memuat model (ModelLoadError) ditangani dengan HTTP 503 aman."""
        with patch("app.routers.measles.get_measles_engine") as mock_engine:
            mock_engine.return_value.predict_bytes.side_effect = ModelLoadError(
                "Internal model path /sensitive/path/weights.onnx not found"
            )
            response = self.client.post(
                "/v1/measles/predict",
                files={"file": ("sample.png", self.valid_png, "image/png")},
            )
            self.assertEqual(response.status_code, 503)
            detail = response.json().get("detail", "")
            self.assertIn("tidak tersedia", detail.lower())
            self.assertNotIn("/sensitive/path", detail)  # Tidak membocorkan path internal

    def test_10_http_inference_runtime_failure_500(self):
        """10. Kegagalan runtime model (InferenceRuntimeError) -> HTTP 500 aman."""
        with patch("app.routers.measles.get_measles_engine") as mock_engine:
            mock_engine.return_value.predict_bytes.side_effect = InferenceRuntimeError(
                "CUDA/CPU execution provider crash with pointer 0xdeadbeef"
            )
            response = self.client.post(
                "/v1/measles/predict",
                files={"file": ("sample.png", self.valid_png, "image/png")},
            )
            self.assertEqual(response.status_code, 500)
            detail = response.json().get("detail", "")
            self.assertIn("kesalahan", detail.lower())
            self.assertNotIn("0xdeadbeef", detail)  # Tidak membocorkan trace internal


if __name__ == "__main__":
    unittest.main(verbosity=2)
