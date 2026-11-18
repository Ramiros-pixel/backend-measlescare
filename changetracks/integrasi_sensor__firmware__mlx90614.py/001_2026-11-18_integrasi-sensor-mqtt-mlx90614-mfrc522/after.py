"""Driver sensor suhu IR non-contact MLX90614 (GY-906 / HW-691) via I2C.

Alamat default 0x5A. Pembacaan suhu objek dan ambient dengan verifikasi PEC
(CRC-8, polinomial 0x07). Impor modul `smbus2` dilakukan saat inisialisasi agar
berkas tetap bisa diimpor (mis. untuk unit test) di mesin tanpa hardware.
"""

from __future__ import annotations

import statistics

try:  # pragma: no cover - tergantung hardware
    import smbus2
except ImportError as _exc:
    smbus2 = None
    _IMPORT_ERROR = _exc
else:
    _IMPORT_ERROR = None

MLX90614_I2C_ADDR = 0x5A
MLX90614_TA = 0x06    # register RAM: ambient temperature
MLX90614_TOBJ1 = 0x07  # register RAM: object temperature 1
SCALE_KELVIN = 0.02    # resolusi sensor: 0.02 K per LSB
ABSOLUTE_ZERO_K = 273.15


def _crc8(data: bytes) -> int:
    """CRC-8 (polinomial 0x07, init 0x00) — byte PEC milik MLX90614."""
    crc = 0x00
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = ((crc << 1) ^ 0x07) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


class MLX90614:
    """Pembaca MLX90614 via SMBus.

    Args:
        bus_number: nomor bus I2C (umumnya 1 di Raspberry Pi / Orange Pi).
        address: alamat I2C sensor (default 0x5A).
    """

    def __init__(self, bus_number: int = 1, address: int = MLX90614_I2C_ADDR) -> None:
        if smbus2 is None:
            raise RuntimeError(
                "modul 'smbus2' belum terpasang. Jalankan: "
                "pip install -r integrasi_sensor/requirements.txt "
                "dan pastikan I2C aktif (/dev/i2c-1 ada)."
            ) from _IMPORT_ERROR
        self.address = address
        self._bus = smbus2.SMBus(bus_number)

    def _read_temp_raw(self, reg: int) -> float:
        """Baca satu register suhu (3 byte: lsb, msb, pec) lalu konversi ke °C."""
        lsb, msb, pec = self._bus.read_i2c_block_data(self.address, reg, 3)
        expected = _crc8(bytes([(self.address << 1), reg, lsb, msb]))
        if expected != pec:
            raise ValueError(f"PEC mismatch: diharapkan {expected:#04x}, diterima {pec:#04x}")
        raw = (msb << 8) | lsb
        return raw * SCALE_KELVIN - ABSOLUTE_ZERO_K

    def read_ambient(self) -> float:
        """Suhu sekitar sensor (°C)."""
        return self._read_temp_raw(MLX90614_TA)

    def read_object(self) -> float:
        """Suhu objek yang diarahkan ke sensor (°C)."""
        return self._read_temp_raw(MLX90614_TOBJ1)

    def read_object_median(self, samples: int = 5) -> float:
        """Median dari beberapa pembacaan objek; pembacaan PEC-error dilewati."""
        values = []
        for _ in range(max(1, samples)):
            try:
                values.append(self.read_object())
            except (ValueError, OSError):
                continue
        if not values:
            raise RuntimeError(
                "gagal membaca MLX90614 (semua percobaan gagal / PEC salah). "
                "Cek wiring I2C dan pull-up SCL/SDA."
            )
        return statistics.median(values)