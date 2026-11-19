"""Driver modul RFID MFRC522 Mini (13.56 MHz, SPI) untuk Raspberry Pi / Orange Pi.

Port ringkas dari implementasi publik MFRC522-python (mxgxw) dengan abstraksi
GPIO multi-platform:
- Linux kernel chardev gpiod (Orange Pi 4 Pro / Allwinner A733 / Ubuntu 22.04)
- RPi.GPIO (Raspberry Pi)
- OPi.GPIO (Orange Pi legacy)

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
except (ImportError, RuntimeError):
    try:
        import OPi.GPIO as GPIO
    except (ImportError, RuntimeError):
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

    Backend prioritas:
    1. gpiod (Linux kernel chardev GPIO /dev/gpiochip*).
       Mendukung libgpiod v1.x (Ubuntu 22.04 LTS python3-libgpiod 1.6.3)
       dan libgpiod v2.x (gpiod.request_lines).
    2. RPi.GPIO / OPi.GPIO (fallback untuk Raspberry Pi / legacy SBC).
    """

    def __init__(self, pin_rst: int) -> None:
        import os

        self._backend: str | None = None
        self._gpio = None
        self._pin: int | None = None
        self._chip = None
        self._gpiod_v1_line = None
        self._gpiod_v2_req = None
        self._gpiod_v2_line: int | None = None

        chip_path = os.getenv("MFRC522_RST_CHIP", DEFAULT_RST_CHIP)
        line_no = int(os.getenv("MFRC522_RST_LINE", str(DEFAULT_RST_LINE)))

        # 1. Coba backend gpiod (prioritas utama pada Linux SBC modern seperti Orange Pi 4 Pro)
        try:
            import gpiod
            gpiod_available = True
        except ImportError:
            gpiod_available = False

        if gpiod_available:
            try:
                chip = gpiod.Chip(chip_path)
                self._chip = chip

                if hasattr(chip, "get_line"):
                    # API gpiod v1.x (Ubuntu 22.04 LTS python3-libgpiod 1.6.3)
                    line = chip.get_line(line_no)
                    line.request(
                        consumer="mfrc522-rst",
                        type=gpiod.LINE_REQ_DIR_OUT,
                        default_vals=[1],
                    )
                    self._gpiod_v1_line = line
                    self._backend = "gpiod_v1"
                    return
                elif hasattr(chip, "request_lines"):
                    # API gpiod v2.x
                    try:
                        from gpiod.line import Direction, Value
                        line_settings = gpiod.LineSettings(
                            direction=Direction.OUTPUT,
                            output_value=Value.ACTIVE
                        )
                        req = chip.request_lines(
                            consumer="mfrc522-rst",
                            config={line_no: line_settings}
                        )
                    except Exception:
                        req = chip.request_lines(
                            consumer="mfrc522-rst",
                            lines=[line_no],
                        )
                    self._gpiod_v2_req = req
                    self._gpiod_v2_line = line_no
                    self._backend = "gpiod_v2"
                    return
                else:
                    raise RuntimeError(f"API gpiod tidak dikenali pada chip: {chip}")

            except PermissionError as exc:
                self.cleanup()
                raise PermissionError(
                    f"Akses ke chip GPIO '{chip_path}' ditolak ({exc}). "
                    f"Pastikan user '{os.getenv('USER', 'orangepi')}' telah ditambahkan ke group 'gpio': "
                    f"sudo usermod -aG gpio $USER lalu login ulang."
                ) from exc
            except OSError as exc:
                self.cleanup()
                raise OSError(
                    f"Gagal menginisialisasi pin RST via gpiod ({chip_path}, line {line_no}): {exc}. "
                    f"Periksa apakah pin sedang digunakan proses lain atau device node tersedia."
                ) from exc

        # 2. Coba fallback RPi.GPIO / OPi.GPIO (hanya jika gpiod tidak terpasang)
        if GPIO is not None:
            try:
                GPIO.setmode(GPIO.BOARD)
                GPIO.setup(pin_rst, GPIO.OUT)
                GPIO.output(pin_rst, 1)
                self._gpio = GPIO
                self._pin = pin_rst
                self._backend = "gpio"
                return
            except Exception as exc:
                self.cleanup()
                raise RuntimeError(
                    f"Fallback GPIO (mode BOARD, pin {pin_rst}) gagal: {exc}"
                ) from exc

        # 3. Tidak ada backend yang tersedia
        raise RuntimeError(
            "Tidak ada pustaka GPIO yang dapat digunakan untuk mengontrol pin RST MFRC522. "
            "Untuk Orange Pi 4 Pro / Ubuntu 22.04: pasang python3-libgpiod (sudo apt install -y python3-libgpiod). "
            "Untuk Raspberry Pi: pasang RPi.GPIO (pip install RPi.GPIO)."
        )

    def output_high(self) -> None:
        """Kirim sinyal HIGH ke pin RST."""
        if self._gpiod_v1_line is not None:
            self._gpiod_v1_line.set_value(1)
        elif self._gpiod_v2_req is not None and self._gpiod_v2_line is not None:
            try:
                from gpiod.line import Value
                self._gpiod_v2_req.set_value(self._gpiod_v2_line, Value.ACTIVE)
            except Exception:
                self._gpiod_v2_req.set_value(self._gpiod_v2_line, 1)
        elif self._gpio is not None and self._pin is not None:
            self._gpio.output(self._pin, 1)

    def cleanup(self) -> None:
        """Lepaskan seluruh resource GPIO secara aman dan idempoten."""
        if self._gpiod_v1_line is not None:
            try:
                self._gpiod_v1_line.release()
            except Exception:
                pass
            self._gpiod_v1_line = None

        if self._gpiod_v2_req is not None:
            try:
                self._gpiod_v2_req.release()
            except Exception:
                pass
            self._gpiod_v2_req = None

        if self._chip is not None:
            try:
                self._chip.close()
            except Exception:
                pass
            self._chip = None

        if self._gpio is not None:
            try:
                if self._pin is not None:
                    self._gpio.cleanup(self._pin)
                else:
                    self._gpio.cleanup()
            except Exception:
                pass
            self._gpio = None
            self._pin = None
        self._backend = None


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
                "dan pastikan SPI aktif (/dev/spidev* ada)."
            ) from _SPI_ERROR

        self._spi = None
        self._rst_gpio = None
        self._rst = pin_rst

        try:
            self._spi = spidev.SpiDev()
            self._spi.open(bus, device)
            self._spi.max_speed_hz = speed

            self._rst_gpio = _RstGpio(pin_rst)
            self._rst_gpio.output_high()
            self._init()
        except Exception:
            self.close()
            raise

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
        """Tutup SPI dan bersihkan GPIO secara aman dan idempoten."""
        if hasattr(self, "_spi") and self._spi is not None:
            try:
                self._spi.close()
            except Exception:
                pass
            self._spi = None

        if hasattr(self, "_rst_gpio") and self._rst_gpio is not None:
            try:
                self._rst_gpio.cleanup()
            except Exception:
                pass
            self._rst_gpio = None
