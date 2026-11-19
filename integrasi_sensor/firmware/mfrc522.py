"""Driver modul RFID MFRC522 Mini (13.56 MHz, SPI) untuk Raspberry Pi / Orange Pi.

Port ringkas dari implementasi publik MFRC522-python (mxgxw) dengan abstraksi
GPIO: memakai `RPi.GPIO` (Raspberry Pi) dan otomatis `OPi.GPIO` (Orange Pi).
Modul `spidev` dan pustaka GPIO diimpor saat inisialisasi agar berkas tetap
bisa diimpor di mesin tanpa hardware.
"""

from __future__ import annotations

try:  # pragma: no cover - tergantung hardware
    import spidev
except ImportError as _exc:
    spidev = None
    _SPI_ERROR = _exc
else:
    _SPI_ERROR = None

try:  # pragma: no cover
    import RPi.GPIO as GPIO
except ImportError:
    try:
        import OPi.GPIO as GPIO
    except ImportError:
        GPIO = None

# Pin fisik (mode BOARD) — sesuaikan bila pinout board Anda berbeda.
NRSTPD = 22

# Orange Pi 4 Pro (Allwinner A733): pin fisik 22 = PD23 = line 119 di gpiochip0.
# Dapat dioverride via env MFRC522_RST_CHIP / MFRC522_RST_LINE.
DEFAULT_RST_CHIP = "/dev/gpiochip0"
DEFAULT_RST_LINE = 119

# Register MFRC522
COMMAND_REG = 0x01
COMIEN_REG = 0x02
DIVIEN_REG = 0x03
COMIRQ_REG = 0x04
DIVIRQ_REG = 0x05
ERROR_REG = 0x06
STATUS1_REG = 0x07
FIFODATA_REG = 0x09
FIFOLEVEL_REG = 0x0A
CONTROL_REG = 0x0C
BITFRAMING_REG = 0x0D
MODE_REG = 0x11
TXMODE_REG = 0x12
RXMODE_REG = 0x13
TXCONTROL_REG = 0x14
TXAUTO_REG = 0x15
CRC_RESULT_REG_H = 0x21
CRC_RESULT_REG_L = 0x22
TMODE_REG = 0x2A
TPRESCALER_REG = 0x2B
TRELOAD_REG_H = 0x2C
TRELOAD_REG_L = 0x2D

# Perintah PCD
PCD_IDLE = 0x00
PCD_TRANSCEIVE = 0x0C
PCD_RESETPHASE = 0x0F

# Perintah PICC
PICC_REQIDL = 0x26
PICC_ANTICOLL = 0x93
PICC_HALT = 0x50

# Flag error / irq
ERR_BUFFER_OVERFLOW = 0x04
ERR_PARITY = 0x08
ERR_PROTOCOL = 0x10
IRQ_SET1 = 0x01
IRQ_TX = 0x08
IRQ_RX = 0x10


def uid_to_hex(uid: list[int]) -> str:
    """UID 4 byte -> string hex huruf besar tanpa pemisah (format di patient_cards)."""
    return "".join(f"{b:02X}" for b in uid)


class _RstGpio:
    """Kontrol pin RST MFRC522.

    Backend prioritas: gpiod (chardev kernel, bekerja di Sunxi/Allwinner tanpa
    tabel papan seperti OPi.GPIO). Fallback: RPi.GPIO / OPi.GPIO mode BOARD
    (Raspberry Pi).
    """

    def __init__(self, pin_rst: int) -> None:
        import os

        self._gpio = None
        self._gpiod_line = None
        chip_path = os.getenv("MFRC522_RST_CHIP", DEFAULT_RST_CHIP)
        line_no = int(os.getenv("MFRC522_RST_LINE", str(DEFAULT_RST_LINE)))
        try:
            import gpiod

            chip = gpiod.Chip(chip_path)
            line = chip.get_line(line_no)
            line.request(
                consumer="mfrc522-rst",
                type=gpiod.LINE_REQ_DIR_OUT,
                default_vals=[1],
            )
            self._gpiod_line = line
            self._chip = chip
        except (ImportError, OSError, PermissionError):
            # Fallback lama untuk Raspberry Pi (RPi.GPIO) / Orange Pi (OPi.GPIO)
            if GPIO is None:
                raise RuntimeError(
                    "tidak ada backend GPIO: gpiod (apt install python3-libgpiod) "
                    "atau RPi.GPIO / OPi.GPIO"
                )
            GPIO.setmode(GPIO.BOARD)
            GPIO.setup(pin_rst, GPIO.OUT)
            GPIO.output(pin_rst, 1)
            self._gpio = GPIO
            self._pin = pin_rst

    def output_high(self) -> None:
        if self._gpiod_line is not None:
            self._gpiod_line.set_value(1)
        elif self._gpio is not None:
            self._gpio.output(self._pin, 1)

    def cleanup(self) -> None:
        if self._gpiod_line is not None:
            try:
                self._gpiod_line.release()
                self._chip.close()
            except Exception:
                pass
        elif self._gpio is not None:
            try:
                self._gpio.cleanup()
            except Exception:
                pass


class MFRC522:
    """Pembaca MFRC522 via SPI (spidev) + GPIO.

    Args:
        bus: bus SPI (default 0).
        device: device SPI / CE (default 0 -> CE0).
        speed: kecepatan clock SPI dalam Hz.
        pin_rst: pin fisik RST (default 22, mode BOARD).
    """

    def __init__(
        self,
        bus: int = 0,
        device: int = 0,
        speed: int = 1_000_000,
        pin_rst: int = NRSTPD,
    ) -> None:
        if spidev is None:
            raise RuntimeError(
                "modul 'spidev' belum terpasang. Jalankan: "
                "pip install -r integrasi_sensor/requirements.txt "
                "dan pastikan SPI aktif (/dev/spidev0.0 ada)."
            ) from _SPI_ERROR
        if GPIO is None:
            raise RuntimeError(
                "pustaka GPIO tidak tersedia (butuh RPi.GPIO atau OPi.GPIO). "
                "pip install RPi.GPIO  (atau: pip install OPi.GPIO di Orange Pi)"
            )
        self._spi = spidev.SpiDev()
        self._spi.open(bus, device)
        self._spi.max_speed_hz = speed
        self._rst = pin_rst
        self._rst_gpio = _RstGpio(pin_rst)
        self._rst_gpio.output_high()
        self._init()

    # ---------- low level ----------
    def _write(self, addr: int, value: int) -> None:
        self._spi.xfer2([(addr << 1) & 0x7E, value])

    def _read(self, addr: int) -> int:
        return self._spi.xfer2([((addr << 1) & 0x7E) | 0x80, 0])[1]

    def _set_bit(self, addr: int, mask: int) -> None:
        self._write(addr, self._read(addr) | mask)

    def _clear_bit(self, addr: int, mask: int) -> None:
        self._write(addr, self._read(addr) & (~mask & 0xFF))

    def _init(self) -> None:
        """Konfigurasi dasar (mode ISO14443A, timer) + antena menyala."""
        self._write(COMMAND_REG, PCD_RESETPHASE)
        self._write(TMODE_REG, 0x8D)
        self._write(TPRESCALER_REG, 0x3E)
        self._write(TRELOAD_REG_L, 30)
        self._write(TRELOAD_REG_H, 0)
        self._write(TXAUTO_REG, 0x40)
        self._write(MODE_REG, 0x3D)
        self._antenna_on()

    def _antenna_on(self) -> None:
        if not (self._read(TXCONTROL_REG) & 0x03):
            self._set_bit(TXCONTROL_REG, 0x03)

    def _transceive(self, data: list[int], bit_framing: int = 0x00) -> tuple[int, list[int], int]:
        """Kirim data via PCD_TRANSCEIVE. Kembalikan (status, back_data, back_len)."""
        self._write(COMMAND_REG, PCD_IDLE)
        self._write(COMIRQ_REG, 0x7F)          # bersihkan semua IRQ
        self._write(FIFOLEVEL_REG, 0x80)       # flush FIFO
        for byte in data:
            self._write(FIFODATA_REG, byte)
        self._write(BITFRAMING_REG, bit_framing)
        self._write(COMMAND_REG, PCD_TRANSCEIVE)
        if bit_framing == 0x00:
            self._set_bit(BITFRAMING_REG, 0x80)  # StartSend
        for _ in range(2000):  # timeout polling
            irq = self._read(COMIRQ_REG)
            if irq & IRQ_SET1 and irq & (IRQ_TX | IRQ_RX):
                break
        else:
            return (1, [], 0)  # timeout: tidak ada kartu
        error = self._read(ERROR_REG)
        if error & (ERR_BUFFER_OVERFLOW | ERR_PARITY | ERR_PROTOCOL):
            return (2, [], 0)
        back_len = self._read(FIFOLEVEL_REG)
        back = [self._read(FIFODATA_REG) for _ in range(back_len)]
        return (0, back, back_len)

    # ---------- operasi kartu ----------
    def request(self, mode: int = PICC_REQIDL) -> tuple[int, int | None]:
        """Cek ada kartu di medan. Kembalikan (status, tag_type)."""
        self._write(BITFRAMING_REG, 0x07)
        status, back, _ = self._transceive([mode])
        return (status, back[0] if back else None)

    def anticoll(self) -> tuple[int, list[int], int]:
        """Antikolisi: baca UID (4 byte + BCC). Kembalikan (status, uid, len)."""
        self._write(BITFRAMING_REG, 0x00)
        status, back, back_len = self._transceive([PICC_ANTICOLL, 0x20])
        if status == 0 and back_len == 5:
            bcc_check = back[0] ^ back[1] ^ back[2] ^ back[3]
            if bcc_check != back[4]:
                return (2, [], 0)
            return (0, back, back_len)
        return (status, [], 0)

    def halt(self) -> None:
        """Hentikan kartu (kembali ke mode idle)."""
        self._write(BITFRAMING_REG, 0x00)
        self._transceive([PICC_HALT, 0x00])

    def read_card_serial(self) -> list[int] | None:
        """Cek & baca kartu satu kali. Kembalikan UID (list 4 byte) atau None."""
        status, _ = self.request()
        if status != 0:
            return None
        status, uid, _ = self.anticoll()
        if status != 0 or not uid:
            return None
        return uid[:4]

    def close(self) -> None:
        """Tutup SPI dan bersihkan GPIO."""
        self._spi.close()
        if self._rst_gpio is not None:
            self._rst_gpio.cleanup()
