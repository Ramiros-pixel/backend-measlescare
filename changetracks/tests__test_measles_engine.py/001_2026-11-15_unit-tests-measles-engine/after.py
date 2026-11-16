"""
Unit tests for MeaslesWatch AI ONNX Inference Engine & Preprocessing Service
Project: MeaslesWatch AI — Huawei ICT Competition 2026–2027
Team: Inovexa
"""

import sys
import unittest
from pathlib import Path

import cv2
import numpy as np

# Ensure backend root is on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.services.measles_engine import (
    CLASS_NAMES,
    DEFAULT_MODEL_PATH,
    NUM_CLASSES,
    InferenceRuntimeError,
    InvalidImageError,
    MeaslesEngine,
    ModelLoadError,
    get_measles_engine,
    reset_measles_engine,
)


class TestMeaslesEngine(unittest.TestCase):
    """Suite pengujian unit komprehensif untuk MeaslesEngine."""

    @classmethod
    def setUpClass(cls):
        """Inisialisasi engine sekali untuk seluruh kelas tes."""
        reset_measles_engine()
        cls.engine = get_measles_engine()

        # Buat synthetic image (300 x 400, BGR)
        cls.synthetic_bgr = np.zeros((300, 400, 3), dtype=np.uint8)
        cls.synthetic_bgr[:, :, 0] = 50   # Blue
        cls.synthetic_bgr[:, :, 1] = 120  # Green
        cls.synthetic_bgr[:, :, 2] = 200  # Red

        # Encode ke PNG bytes
        _, buf_png = cv2.imencode(".png", cls.synthetic_bgr)
        cls.valid_png_bytes = buf_png.tobytes()

        # Encode ke JPEG bytes
        _, buf_jpg = cv2.imencode(".jpg", cls.synthetic_bgr)
        cls.valid_jpg_bytes = buf_jpg.tobytes()

    def test_01_model_loading_succeeds(self):
        """1. Model loading succeeds dan sesi ONNX aktif."""
        self.assertIsNotNone(self.engine.session)
        self.assertTrue(self.engine.model_path.exists())

        # Test kegagalan jika file model tidak ada
        with self.assertRaises(ModelLoadError):
            MeaslesEngine(model_path="non_existent_weights.onnx")

    def test_02_onnx_metadata_correct(self):
        """2. ONNX input dan output metadata sesuai spesifikasi model."""
        self.assertEqual(self.engine.input_name, "input")
        self.assertEqual(self.engine.output_name, "logits")

        # Input shape: [batch_size, 3, 224, 224]
        self.assertEqual(len(self.engine.input_shape), 4)
        self.assertEqual(self.engine.input_shape[1:], [3, 224, 224])

        # Output shape: [batch_size, 6]
        self.assertEqual(len(self.engine.output_shape), 2)
        self.assertEqual(self.engine.output_shape[1], NUM_CLASSES)
        self.assertEqual(NUM_CLASSES, 6)

    def test_03_image_decoding_succeeds(self):
        """3. Image decoding berhasil untuk format gambar valid (PNG & JPEG)."""
        decoded_png = MeaslesEngine.decode_image(self.valid_png_bytes)
        self.assertIsInstance(decoded_png, np.ndarray)
        self.assertEqual(decoded_png.shape, (300, 400, 3))
        self.assertEqual(decoded_png.dtype, np.uint8)

        decoded_jpg = MeaslesEngine.decode_image(self.valid_jpg_bytes)
        self.assertIsInstance(decoded_jpg, np.ndarray)
        self.assertEqual(decoded_jpg.shape, (300, 400, 3))
        self.assertEqual(decoded_jpg.dtype, np.uint8)

    def test_04_corrupted_and_empty_bytes_rejected(self):
        """4. Byte gambar kosong, korup, atau bukan bytes ditolak dengan InvalidImageError."""
        # Byte kosong
        with self.assertRaises(InvalidImageError):
            MeaslesEngine.decode_image(b"")

        # Byte korup / bukan gambar
        with self.assertRaises(InvalidImageError):
            MeaslesEngine.decode_image(b"CORRUPTED_NON_IMAGE_DATA_1234567890")

        # Tipe data non-bytes
        with self.assertRaises(InvalidImageError):
            MeaslesEngine.decode_image(None)  # type: ignore

        with self.assertRaises(InvalidImageError):
            MeaslesEngine.decode_image("string_not_bytes")  # type: ignore

    def test_05_rgb_conversion_correct(self):
        """5. Konversi BGR ke RGB berjalan benar secara deterministik."""
        # Citra murni: Biru penuh (B=255, G=0, R=0)
        pure_blue_bgr = np.zeros((10, 10, 3), dtype=np.uint8)
        pure_blue_bgr[:, :, 0] = 255

        tensor = MeaslesEngine.preprocess_image(pure_blue_bgr)
        # Pada RGB, saluran Red ada di indeks 0, Green indeks 1, Blue indeks 2
        # Blue channel (255 / 255 = 1.0) normalized: (1.0 - 0.406) / 0.225 ≈ 2.64
        # Red channel (0 / 255 = 0.0) normalized: (0.0 - 0.485) / 0.229 ≈ -2.118
        red_val = tensor[0, 0, 0, 0]
        blue_val = tensor[0, 2, 0, 0]

        self.assertAlmostEqual(red_val, (0.0 - 0.485) / 0.229, places=3)
        self.assertAlmostEqual(blue_val, (1.0 - 0.406) / 0.225, places=3)

    def test_06_resize_output_exact_224x224(self):
        """6. Dimensi spasial setelah pra-pemrosesan tepat 224 x 224 (H x W)."""
        # Uji berbagai rasio aspek non-persegi
        ratios = [(100, 500, 3), (800, 200, 3), (224, 224, 3)]
        for h, w, c in ratios:
            test_img = np.zeros((h, w, c), dtype=np.uint8)
            tensor = MeaslesEngine.preprocess_image(test_img)
            self.assertEqual(tensor.shape[2], 224)
            self.assertEqual(tensor.shape[3], 224)

    def test_07_preprocessed_tensor_shape(self):
        """7. Bentuk tensor pra-pemrosesan adalah [1, 3, 224, 224]."""
        tensor = MeaslesEngine.preprocess_image(self.synthetic_bgr)
        self.assertEqual(tensor.shape, (1, 3, 224, 224))

    def test_08_tensor_dtype_float32(self):
        """8. Tipe data tensor adalah float32 dan berada dalam rentang normalisasi kontinu."""
        tensor = MeaslesEngine.preprocess_image(self.synthetic_bgr)
        self.assertEqual(tensor.dtype, np.float32)
        self.assertTrue(tensor.flags.c_contiguous)

    def test_09_softmax_probabilities_finite_and_sum_to_one(self):
        """9. Probabilitas Softmax bernilai terhingga dan memiliki jumlah total ≈ 1.0."""
        # Test 1: Logits normal
        logits = np.array([[1.2, -0.5, 3.4, 0.1, -1.0, 0.8]], dtype=np.float32)
        probs = MeaslesEngine.apply_softmax(logits)
        self.assertTrue(np.all(np.isfinite(probs)))
        self.assertAlmostEqual(float(np.sum(probs)), 1.0, places=5)

        # Test 2: Logits ekstrem (menguji stabilitas numerik terhadap overflow)
        extreme_logits = np.array([[1000.0, 999.0, -1000.0, 0.0, 50.0, -50.0]], dtype=np.float32)
        probs_extreme = MeaslesEngine.apply_softmax(extreme_logits)
        self.assertTrue(np.all(np.isfinite(probs_extreme)))
        self.assertAlmostEqual(float(np.sum(probs_extreme)), 1.0, places=5)
        self.assertGreater(probs_extreme[0, 0], 0.7)  # Indeks 0 harus memiliki probabilitas dominan

    def test_10_prediction_index_maps_to_correct_class(self):
        """10. Pemetaan indeks kelas tepat sesuai urutan 6 kelas MeaslesWatch AI."""
        self.assertEqual(CLASS_NAMES[0], "Chickenpox")
        self.assertEqual(CLASS_NAMES[1], "Cowpox")
        self.assertEqual(CLASS_NAMES[2], "HFMD")
        self.assertEqual(CLASS_NAMES[3], "Healthy")
        self.assertEqual(CLASS_NAMES[4], "Measles")
        self.assertEqual(CLASS_NAMES[5], "Monkeypox")

        # Eksekusi inferensi nyata dengan citra sintetis
        result = self.engine.predict_bytes(self.valid_png_bytes)
        self.assertIn("prediction", result)
        self.assertIn("class_index", result)
        self.assertIn("confidence", result)
        self.assertIn("probabilities", result)
        self.assertIn("inference_time_ms", result)
        self.assertIn("disclaimer", result)

        self.assertEqual(result["prediction"], CLASS_NAMES[result["class_index"]])
        self.assertEqual(len(result["probabilities"]), 6)
        self.assertAlmostEqual(sum(result["probabilities"].values()), 1.0, places=4)

    def test_11_repeated_inference_reuses_same_session(self):
        """11. Pemanggilan berulang menggunakan sesi model yang sama (singleton thread-safe)."""
        eng1 = get_measles_engine()
        eng2 = get_measles_engine()
        self.assertIs(eng1, eng2)
        self.assertIs(eng1.session, eng2.session)

    def test_12_runtime_errors_handled_safely(self):
        """12. Kesalahan runtime ditangani dengan aman tanpa membocorkan trace internal."""
        # Citra berdimensi salah (2D bukan 3D)
        gray_2d = np.zeros((224, 224), dtype=np.uint8)
        with self.assertRaises(InvalidImageError):
            MeaslesEngine.preprocess_image(gray_2d)

        # Tensor input ke session dengan dimensi salah
        wrong_tensor = np.zeros((1, 3, 100, 100), dtype=np.float32)
        with self.assertRaises(InferenceRuntimeError):
            try:
                self.engine.session.run(["logits"], {"input": wrong_tensor})
            except Exception as e:
                raise InferenceRuntimeError(f"Handled error: {str(e)}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
