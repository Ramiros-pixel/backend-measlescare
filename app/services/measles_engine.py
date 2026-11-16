"""
MeaslesWatch AI — ONNX Inference Engine & Preprocessing Service
Huawei ICT Competition 2026–2027 | Innovation Track
Team: Inovexa

Tanggung jawab modul:
1. Memuat dan mengelola siklus hidup sesi ONNX Runtime CPU secara thread-safe (singleton).
2. Memvalidasi dan mendekode byte gambar menggunakan OpenCV (tanpa ketergantungan HTTP/FastAPI).
3. Melakukan pra-pemrosesan citra deterministik sesuai konfigurasi training (Resize 224x224, BGR->RGB, ImageNet normalization).
4. Menjalankan inferensi model MobileNetV3 Small (opset 17).
5. Menerapkan softmax yang stabil secara numerik dan memetakan 6 kelas klasifikasi penyakit.
"""

from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import cv2
import numpy as np
import onnxruntime as ort

logger = logging.getLogger(__name__)

# =============================================================================
# KONFIGURASI DAN KONSTANTA MODEL
# =============================================================================

DEFAULT_MODEL_PATH: Path = (
    Path(__file__).resolve().parents[1] / "models" / "weights" / "mobilenetv3_measleswatch.onnx"
)

CLASS_NAMES: list[str] = [
    "Chickenpox",
    "Cowpox",
    "HFMD",
    "Healthy",
    "Measles",
    "Monkeypox",
]

NUM_CLASSES: int = len(CLASS_NAMES)
EXPECTED_INPUT_NAME: str = "input"
EXPECTED_OUTPUT_NAME: str = "logits"
EXPECTED_INPUT_SHAPE: tuple[int, int, int] = (3, 224, 224)
TARGET_IMAGE_SIZE: tuple[int, int] = (224, 224)  # (width, height) untuk cv2.resize

# Parameter Normalisasi Standar ImageNet (identik dengan pipeline PyTorch saat training)
IMAGENET_MEAN: np.ndarray = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD: np.ndarray = np.array([0.229, 0.224, 0.225], dtype=np.float32)

DISCLAIMER_TEXT: str = (
    "Hasil analisis citra merupakan estimasi probabilitas model kecerdasan buatan "
    "(AI inference confidence) dan tidak menggantikan diagnosis klinis tenaga medis profesional."
)


# =============================================================================
# CUSTOM EXCEPTIONS
# =============================================================================

class MeaslesEngineError(Exception):
    """Base exception untuk MeaslesWatch AI engine."""
    pass


class ModelLoadError(MeaslesEngineError):
    """Dilempar saat file model tidak ditemukan atau inisialisasi sesi ONNX gagal."""
    pass


class InvalidImageError(MeaslesEngineError):
    """Dilempar saat byte citra tidak valid, kosong, atau gagal didekode."""
    pass


class InferenceRuntimeError(MeaslesEngineError):
    """Dilempar saat terjadi kegagalan eksekusi inferensi pada ONNX Runtime."""
    pass


# =============================================================================
# INFERENCE ENGINE IMPLEMENTATION
# =============================================================================

class MeaslesEngine:
    """
    Service inferensi mandiri untuk klasifikasi ruam kulit MeaslesWatch AI.
    
    Menggunakan ONNX Runtime CPUExecutionProvider dengan arsitektur MobileNetV3 Small.
    Dirancang thread-safe dan independen dari lapisan transport HTTP/FastAPI.
    """

    def __init__(self, model_path: Optional[Union[str, Path]] = None) -> None:
        self.model_path: Path = Path(model_path) if model_path else DEFAULT_MODEL_PATH
        self._session: Optional[ort.InferenceSession] = None
        self._init_lock: threading.Lock = threading.Lock()
        self._input_name: str = ""
        self._output_name: str = ""
        self._input_shape: list[Any] = []
        self._output_shape: list[Any] = []
        
        self._load_session()

    def _load_session(self) -> None:
        """Memuat ONNX InferenceSession dan memvalidasi metadata input/output."""
        with self._init_lock:
            if self._session is not None:
                return

            if not self.model_path.exists():
                raise ModelLoadError(
                    f"Model ONNX tidak ditemukan pada jalur: {self.model_path.resolve()}"
                )

            try:
                # Konfigurasi opsi sesi ONNX Runtime CPU
                sess_options = ort.SessionOptions()
                sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
                
                # Inisialisasi sesi CPU
                self._session = ort.InferenceSession(
                    str(self.model_path.resolve()),
                    sess_options=sess_options,
                    providers=["CPUExecutionProvider"],
                )
            except Exception as e:
                raise ModelLoadError(
                    f"Gagal menginisialisasi sesi ONNX Runtime: {type(e).__name__} - {str(e)}"
                ) from e

            # Validasi input metadata
            inputs = self._session.get_inputs()
            if not inputs:
                raise ModelLoadError("Model ONNX tidak memiliki tensor input terdaftar.")
            
            inp = inputs[0]
            self._input_name = inp.name
            self._input_shape = list(inp.shape)

            if self._input_name != EXPECTED_INPUT_NAME:
                raise ModelLoadError(
                    f"Nama tensor input tidak sesuai. Diharapkan: '{EXPECTED_INPUT_NAME}', "
                    f"Ditemukan: '{self._input_name}'"
                )

            # Validasi channel dan resolusi input (dimensi 1, 2, 3)
            if len(self._input_shape) != 4 or self._input_shape[1:] != [3, 224, 224]:
                raise ModelLoadError(
                    f"Bentuk tensor input tidak valid: {self._input_shape}. "
                    f"Diharapkan: [batch_size, 3, 224, 224]"
                )

            # Validasi output metadata
            outputs = self._session.get_outputs()
            if not outputs:
                raise ModelLoadError("Model ONNX tidak memiliki tensor output terdaftar.")
            
            out = outputs[0]
            self._output_name = out.name
            self._output_shape = list(out.shape)

            if self._output_name != EXPECTED_OUTPUT_NAME:
                raise ModelLoadError(
                    f"Nama tensor output tidak sesuai. Diharapkan: '{EXPECTED_OUTPUT_NAME}', "
                    f"Ditemukan: '{self._output_name}'"
                )

            if len(self._output_shape) != 2 or self._output_shape[1] != NUM_CLASSES:
                raise ModelLoadError(
                    f"Bentuk tensor output tidak valid: {self._output_shape}. "
                    f"Diharapkan: [batch_size, {NUM_CLASSES}]"
                )

            logger.info(
                f"MeaslesEngine berhasil memuat model dari: {self.model_path.name} "
                f"(Input: {self._input_name}{self._input_shape}, Output: {self._output_name}{self._output_shape})"
            )

    @property
    def session(self) -> ort.InferenceSession:
        """Mengembalikan sesi ONNX Runtime aktif."""
        if self._session is None:
            self._load_session()
        assert self._session is not None
        return self._session

    @property
    def input_name(self) -> str:
        return self._input_name

    @property
    def output_name(self) -> str:
        return self._output_name

    @property
    def input_shape(self) -> list[Any]:
        return self._input_shape

    @property
    def output_shape(self) -> list[Any]:
        return self._output_shape

    # -------------------------------------------------------------------------
    # DEKODE & PRA-PEMROSESAN CITRA
    # -------------------------------------------------------------------------

    @staticmethod
    def decode_image(image_bytes: bytes) -> np.ndarray:
        """
        Mendekode byte mentah gambar menjadi array NumPy BGR menggunakan OpenCV.
        
        Args:
            image_bytes: Byte mentah citra (format JPEG, PNG, BMP, WEBP, dll.)
            
        Returns:
            np.ndarray: Citra format BGR dengan tipe uint8 (H, W, 3).
            
        Raises:
            InvalidImageError: Jika byte kosong, bukan bertipe bytes, atau korup.
        """
        if not isinstance(image_bytes, (bytes, bytearray)):
            raise InvalidImageError(
                f"Tipe data tidak didukung: {type(image_bytes).__name__}. Diharapkan bytes atau bytearray."
            )

        if len(image_bytes) == 0:
            raise InvalidImageError("Data citra kosong (0 byte).")

        try:
            np_arr = np.frombuffer(image_bytes, dtype=np.uint8)
            img_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        except Exception as e:
            raise InvalidImageError(f"Terjadi kesalahan saat parsing buffer citra: {str(e)}") from e

        if img_bgr is None or img_bgr.size == 0:
            raise InvalidImageError(
                "Gagal mendekode citra: format tidak didukung atau konten file korup."
            )

        return img_bgr

    @staticmethod
    def preprocess_image(img_bgr: np.ndarray) -> np.ndarray:
        """
        Menjalankan pipeline pra-pemrosesan citra deterministik sesuai spesifikasi model:
        1. Konversi ruang warna BGR ke RGB.
        2. Resize ke 224 x 224 menggunakan interpolasi bilinear (cv2.INTER_LINEAR).
        3. Konversi ke float32 dan scaling [0, 1] melalui pembagian 255.0.
        4. Normalisasi ImageNet: (pixel - mean) / std.
        5. Transpose tata letak saluran dari HWC ke CHW.
        6. Penambahan dimensi batch -> [1, 3, 224, 224].
        7. Memastikan array bersifat contiguous float32 dalam memori.
        
        Args:
            img_bgr: Citra OpenCV format BGR uint8.
            
        Returns:
            np.ndarray: Tensor input siap inferensi berdimensi [1, 3, 224, 224] bertipe float32.
        """
        if not isinstance(img_bgr, np.ndarray):
            raise InvalidImageError("Input pra-pemrosesan harus berupa NumPy ndarray.")

        if img_bgr.ndim != 3 or img_bgr.shape[2] != 3:
            raise InvalidImageError(
                f"Dimensi citra tidak valid: {img_bgr.shape}. Diharapkan citra 3-saluran (H, W, 3)."
            )

        try:
            # 1. BGR ke RGB
            img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

            # 2. Resize 224x224 (cv2.INTER_LINEAR)
            img_resized = cv2.resize(img_rgb, TARGET_IMAGE_SIZE, interpolation=cv2.INTER_LINEAR)

            # 3. Konversi float32 & scaling [0.0, 1.0]
            img_float = img_resized.astype(np.float32) / 255.0

            # 4. ImageNet Normalization: (X - mean) / std
            img_norm = (img_float - IMAGENET_MEAN) / IMAGENET_STD

            # 5. Transpose HWC -> CHW
            img_chw = np.transpose(img_norm, (2, 0, 1))

            # 6. Tambahkan batch dimension -> [1, 3, 224, 224]
            tensor = np.expand_dims(img_chw, axis=0)

            # 7. Pastikan contiguous memory layout
            tensor = np.ascontiguousarray(tensor, dtype=np.float32)

            return tensor
        except Exception as e:
            raise InvalidImageError(f"Kegagalan pada tahap pra-pemrosesan citra: {str(e)}") from e

    # -------------------------------------------------------------------------
    # POST-PROCESSING & SOFTMAX
    # -------------------------------------------------------------------------

    @staticmethod
    def apply_softmax(logits: np.ndarray) -> np.ndarray:
        """
        Menerapkan fungsi Softmax yang stabil secara numerik pada tensor logits.
        
        Formula: exp(z - max(z)) / sum(exp(z - max(z)))
        """
        if not isinstance(logits, np.ndarray):
            raise InferenceRuntimeError("Logits harus berupa NumPy array.")
        
        # Kurangi max logit untuk mencegah overflow pada np.exp
        shift_logits = logits - np.max(logits, axis=-1, keepdims=True)
        exp_logits = np.exp(shift_logits)
        probabilities = exp_logits / np.sum(exp_logits, axis=-1, keepdims=True)

        if not np.all(np.isfinite(probabilities)):
            raise InferenceRuntimeError("Perhitungan probabilitas Softmax menghasilkan nilai non-finite.")

        return probabilities

    # -------------------------------------------------------------------------
    # PREDICTION INTERFACE
    # -------------------------------------------------------------------------

    def predict_bytes(self, image_bytes: bytes) -> dict[str, Any]:
        """
        Menjalankan end-to-end inferensi klasifikasi ruam dari byte citra mentah.
        
        Args:
            image_bytes: Byte mentah citra.
            
        Returns:
            dict berisi:
                - prediction: str (nama kelas terprediksi)
                - class_index: int (indeks kelas 0..5)
                - confidence: float (probabilitas kelas terpilih)
                - probabilities: dict[str, float] (probabilitas untuk seluruh 6 kelas)
                - inference_time_ms: float (durasi pra-pemrosesan + eksekusi model dlm milidetik)
                - disclaimer: str (penjelasan batas medis AI)
        """
        t_start = time.perf_counter()

        # 1. Dekode citra
        img_bgr = self.decode_image(image_bytes)

        # 2. Pra-pemrosesan ke tensor [1, 3, 224, 224]
        tensor = self.preprocess_image(img_bgr)

        # 3. Inferensi ONNX Runtime
        try:
            outputs = self.session.run(
                [self._output_name],
                {self._input_name: tensor},
            )
            logits = outputs[0]
        except Exception as e:
            raise InferenceRuntimeError(
                f"Kesalahan internal saat eksekusi inferensi model ONNX: {type(e).__name__} - {str(e)}"
            ) from e

        if logits.shape != (1, NUM_CLASSES):
            raise InferenceRuntimeError(
                f"Bentuk tensor logits ({logits.shape}) tidak sesuai dengan kelas target (1, {NUM_CLASSES})."
            )

        # 4. Softmax pasca-pemrosesan
        probabilities = self.apply_softmax(logits)[0]  # shape (6,)

        class_idx = int(np.argmax(probabilities))
        predicted_class = CLASS_NAMES[class_idx]
        confidence = float(probabilities[class_idx])

        # 5. Pemetaan probabilitas seluruh kelas
        prob_dict = {
            CLASS_NAMES[i]: round(float(probabilities[i]), 6)
            for i in range(NUM_CLASSES)
        }

        t_elapsed_ms = (time.perf_counter() - t_start) * 1000.0

        return {
            "prediction": predicted_class,
            "class_index": class_idx,
            "confidence": round(confidence, 6),
            "probabilities": prob_dict,
            "inference_time_ms": round(t_elapsed_ms, 2),
            "disclaimer": DISCLAIMER_TEXT,
        }

    def predict(self, image: Union[bytes, np.ndarray]) -> dict[str, Any]:
        """
        Metode inferensi fleksibel yang menerima byte gambar atau OpenCV ndarray BGR.
        """
        if isinstance(image, (bytes, bytearray)):
            return self.predict_bytes(image)
        elif isinstance(image, np.ndarray):
            t_start = time.perf_counter()
            tensor = self.preprocess_image(image)
            try:
                outputs = self.session.run([self._output_name], {self._input_name: tensor})
                logits = outputs[0]
            except Exception as e:
                raise InferenceRuntimeError(f"Kesalahan internal inferensi: {str(e)}") from e
            probabilities = self.apply_softmax(logits)[0]
            class_idx = int(np.argmax(probabilities))
            prob_dict = {CLASS_NAMES[i]: round(float(probabilities[i]), 6) for i in range(NUM_CLASSES)}
            t_elapsed_ms = (time.perf_counter() - t_start) * 1000.0
            return {
                "prediction": CLASS_NAMES[class_idx],
                "class_index": class_idx,
                "confidence": round(float(probabilities[class_idx]), 6),
                "probabilities": prob_dict,
                "inference_time_ms": round(t_elapsed_ms, 2),
                "disclaimer": DISCLAIMER_TEXT,
            }
        else:
            raise InvalidImageError(f"Input tidak didukung: {type(image).__name__}")


# =============================================================================
# SINGLETON LIFECYCLE MANAGEMENT
# =============================================================================

_engine_instance: Optional[MeaslesEngine] = None
_singleton_lock: threading.Lock = threading.Lock()


def get_measles_engine(model_path: Optional[Union[str, Path]] = None) -> MeaslesEngine:
    """
    Mengembalikan instance singleton dari MeaslesEngine secara thread-safe.
    
    Model hanya dimuat ke dalam memori satu kali selama lifecycle aplikasi berlangsung.
    """
    global _engine_instance
    if _engine_instance is None:
        with _singleton_lock:
            if _engine_instance is None:
                _engine_instance = MeaslesEngine(model_path=model_path)
    return _engine_instance


def reset_measles_engine() -> None:
    """
    Mereset instance singleton MeaslesEngine.
    Hanya digunakan untuk isolasi pengujian otomatis (unit testing).
    """
    global _engine_instance
    with _singleton_lock:
        _engine_instance = None
