# HARDWARE_DOCUMENTATION — MeaslesCare

Dokumentasi hardware & sistem kerja integrasi sensor kiosk: **GPIO tiap sensor**,
**cara menjalankan**, dan **cara kerja sistem** (RFID + suhu IR → MQTT → database).

| Item | Nilai |
| :--- | :--- |
| Sensor suhu | MLX90614 (GY-906 / HW-691) — IR non-contact, I2C |
| Sensor RFID | MFRC522 Mini — 13.56 MHz, SPI |
| Board target | Raspberry Pi / Orange Pi 4 Pro (Allwinner A733, header 40-pin) |
| Transport data | MQTT QoS 1 via broker Mosquitto (Docker / native) |
| Penerima data | `integrasi_sensor/bridge/mqtt_bridge.py` → MySQL `db_huawei` |

> [!IMPORTANT]
> **Status Verifikasi Hardware:**
> Pemetaan pin header 40-pin Orange Pi 4 Pro (Allwinner A733) di bawah ini merupakan konfigurasi device-tree kernel Linux 6.6 (`sun60iw2`) melalui overlay `i2c0` dan `spi3-cs0-cs1-spidev`. Pemetaan ini **berstatus perlu verifikasi lebih lanjut terhadap skematik resmi board dan pengukuran tegangan fisik sebelum implementasi produksi**. Pada audit Phase 4, pengujian software dan integrasi MQTT berhasil (PASS), namun sensor fisik MLX90614 dan reader MFRC522 **belum terdeteksi secara fisik** (jalur I2C 0.0V / SPI register 0x37 mengembalikan `0xFF`). Jangan mengklaim sensor fisik berfungsi sebelum pengujian langsung di board membuktikan pembacaan nyata.

---

## 1. GPIO tiap sensor

Nomor pin = **pin fisik header 40-pin (mode BOARD)**. Pastikan hanya memakai
**3.3V** (bukan 5V). Nomor GPIO/bus di bawah **sudah disesuaikan Orange Pi 4 Pro
(A733)** — di kolom Raspberry Pi dicantumkan untuk pembanding.

### 1.1 MLX90614 (GY-906 / HW-691) — I2C

| Kaki modul | Pin fisik | OPI 4 Pro | RPi (BCM) | Arah |
| :--- | :--- | :--- | :--- | :--- |
| VIN | 1 | 3.3V | 3.3V | daya |
| GND | 6 | GND | GND | ground |
| SDA | 3 | SDA.0 → PB3 (GPIO 35) | GPIO2 (SDA.1) | data |
| SCL | 5 | SCL.0 → PB2 (GPIO 34) | GPIO3 (SCL.1) | clock |

- Alamat I2C: `0x5A`.
- **OPI 4 Pro: bus I2C 0** (`/dev/i2c-0`, TWI0) — diaktifkan lewat overlay
  `i2c0` di `/boot/orangepiEnv.txt`.
- Raspberry Pi: bus I2C 1 (`/dev/i2c-1`).
- Jika pembacaan gagal (PEC salah), tambahkan resistor pull-up **4,7 kΩ**
  SDA dan SCL ke 3.3V (sebagian modul GY-906 belum ada pull-up onboard).

### 1.2 MFRC522 Mini — SPI

| Kaki modul | Pin fisik | OPI 4 Pro | RPi (BCM) | Arah |
| :--- | :--- | :--- | :--- | :--- |
| SDA (SS) | 24 | CE.0 → GPIO 140 | GPIO8 (CE0) | chip select |
| SCK | 23 | SCLK.3 → GPIO 129 | GPIO11 (SCLK) | clock |
| MOSI | 19 | MOSI.3 → GPIO 130 | GPIO10 (MOSI) | data keluar |
| MISO | 21 | MISO.3 → GPIO 131 | GPIO9 (MISO) | data masuk |
| IRQ | — | (tidak dipakai) | — | — |
| RST | 22 | PD23 (GPIO 119) | GPIO25 | reset reader |
| 3.3V | 1 atau 17 | 3.3V | 3.3V | daya |
| GND | 6 atau 9 | GND | GND | ground |

- **OPI 4 Pro: SPI bus 3** (`/dev/spidev3.0`, SPI3) — diaktifkan lewat overlay
  `spi3-cs0-cs1-spidev` di `/boot/orangepiEnv.txt`.
- Raspberry Pi: bus SPI 0, device 0 (`/dev/spidev0.0`).
- Pin RST dikendalikan driver `mfrc522.py`: prioritas backend **gpiod**
  (`/dev/gpiochip0`, line 119 pada OPI 4 Pro; override env
  `MFRC522_RST_CHIP`/`MFRC522_RST_LINE`), fallback `RPi.GPIO`/`OPi.GPIO`
  mode BOARD untuk Raspberry Pi.

> Catatan Orange Pi 4 Pro: pinout 40-pin kompatibel posisi dengan Raspberry Pi,
> tapi pemetaan fungsinya berbeda (I2C = TWI0 di pin 3/5, SPI = SPI3 di pin
> 19/21/23/24). Verifikasi dengan `gpio readall` (wiringOP bawaan).

---

## 2. Cara menjalankan

### 2.1 Prasyarat

```bash
# 1) Aktifkan I2C dan SPI
#    Raspberry Pi    : sudo raspi-config -> Interface Options -> I2C/SPI: enable
#    Orange Pi 4 Pro : edit /boot/orangepiEnv.txt, tambahkan baris:
#        overlays=i2c0 spi3-cs0-cs1-spidev
#      lalu reboot (node device-tree TWI0/SPI3 hanya bisa diaktifkan saat boot).
ls -l /dev/i2c-0 /dev/spidev3.0     # OPI 4 Pro: harus ada setelah reboot
ls -l /dev/i2c-1 /dev/spidev0.0     # Raspberry Pi: harus ada

# 2) Izin akses (OPI 4 Pro): user harus anggota group i2c dan gpio
sudo usermod -aG i2c,gpio orangepi      # lalu login ulang
# Aturan udev: /etc/udev/rules.d/90-sensor-permissions.rules
#   (gpiochip* + spidev -> group gpio, i2c-dev -> group i2c)

# 3) Paket sistem Ubuntu (APT) untuk backend GPIO gpiod & diagnosa I2C
sudo apt update && sudo apt install -y python3-libgpiod libgpiod2 i2c-tools

# 4) Virtual Environment Python (wajib gunakan --system-site-packages agar gpiod terbaca)
python3 -m venv --system-site-packages .venv-sensor
source .venv-sensor/bin/activate

# 5) Dependensi Python (pip)
cd backend-measlescare
pip install -r integrasi_sensor/requirements.txt
```

### 2.2 Urutan menjalankan

```bash
# 1) Broker Mosquitto (Docker)
docker compose up -d mosquitto
docker compose ps mosquitto          # harus Up (healthy)

# 2) Bridge (subscriber MQTT -> MySQL)  — terminal 1
python3 -m integrasi_sensor.bridge.mqtt_bridge --verbose

# 3) Publisher (baca sensor)          — terminal 2
python3 -m integrasi_sensor.firmware.sensor_publisher --verbose
```

Tempelkan kartu ke reader, arahkan MLX90614 ke dahi (jarak ±3–5 cm).
Satu baris `Gejala` baru otomatis tersimpan.

### 2.3 Uji tanpa hardware

```bash
docker compose exec mosquitto mosquitto_pub -t "measlescare/kiosk-01/reading" \
  -m '{"device_id":"kiosk-01","rfid_uid":"E0040100ABCDEF0001","suhu":36.7,"sensor":"mlx90614","ts":"2026-11-18T15:04:05+00:00"}'
```

---

## 3. Sistem kerja

```
[ MFRC522 ] --SPI--> [ sensor_publisher.py ] --MQTT QoS 1--> [ Mosquitto ] --> [ mqtt_bridge.py ] --> MySQL db_huawei
[ MLX90614 ] --I2C--> [   (Orange Pi/Pi)   ]                 (Docker :1883)      (subscriber)
                                                                                     |
                                  1. scan kartu -> UID hex            1. validasi payload
                                  2. ukur suhu (median)               2. rfid_uid -> patient_cards -> NIK
                                  3. publish JSON                    3. kartu baru? -> daftarkan otomatis
                                                                     4. insert Gejala (Suhu, Batuk NULL)
```

### 3.1 Publisher (firmware)

1. `MFRC522.read_card_serial()` — deteksi kartu di medan (REQA + anticoll),
   ambil **UID 4 byte**, konversi ke hex huruf besar (contoh `E0040100`).
2. `MLX90614.read_object_median(5)` — ukur suhu objek 5×, ambil median,
   verifikasi CRC (PEC) tiap pembacaan.
3. Publish JSON QoS 1 ke topik `measlescare/<DEVICE_ID>/reading`:

```json
{
  "device_id": "kiosk-01",
  "rfid_uid": "E0040100ABCDEF0001",
  "suhu": 36.7,
  "sensor": "mlx90614",
  "ts": "2026-11-18T15:04:05+00:00"
}
```

4. Tunggu kartu dilepas (≤10 detik) + jeda `RFID_DEBOUNCE_SEC` sebelum scan
   berikutnya.

### 3.2 Bridge (subscriber → database)

1. Subscribe `measlescare/+/reading` (QoS 1).
2. **Validasi payload**: `rfid_uid` string 2–64 karakter; `suhu` angka dalam
   rentang 25–45 °C (variabel `SUHU_MIN`/`SUHU_MAX`). Payload invalid dilewati.
3. **Dedupe**: pengiriman ulang QoS 1 yang membawa payload identik (kunci
   `rfid_uid:suhu:ts`) dalam 60 detik tidak disimpan dua kali.
4. **Cari kartu** di `patient_cards` (`rfid_uid`):
   - Ditemukan → pakai `NIK` pemilik kartu.
   - **Tidak ditemukan → kartu didaftarkan otomatis** (lihat §4), lalu lanjut.
5. **Simpan**: `INSERT Gejala (id_gejala, NIK, Suhu, Batuk=NULL)` —
   `Tanggal` otomatis (waktu server).

### 3.3 Tabel database yang terlibat

| Tabel | Kolom yang dipakai | Peran |
| :--- | :--- | :--- |
| `patient_cards` | `rfid_uid`, `NIK` | pemetaan kartu → pasien |
| `Users` | `NIK`, `Name`, `password`, `id_Role` | pasien (dibuat otomatis bila kartu baru) |
| `Role` | `id_Role` | `R2` = pasien |
| `Gejala` | `id_gejala`, `NIK`, `Suhu`, `Batuk`, `Tanggal` | riwayat pengukuran |

Tidak ada perubahan skema: semua kolom sudah tersedia di database backend.

---

## 4. Auto-registrasi kartu RFID

Ketika kartu terbaca dan **belum terdaftar**, bridge otomatis membuat data
pasien baru seolah-olah kartu sudah "memiliki" data — data diturunkan dari
hex UID chip (tidak perlu menulis apa pun ke kartu):

| Field | Nilai yang dibuat |
| :--- | :--- |
| `patient_cards.rfid_uid` | hex UID dari chip (huruf besar) |
| `Users.NIK` | **16 digit numerik deterministik** dari hash SHA-256 hex UID (`f"{int(hashlib.sha256(rfid.encode()).digest()[:8], 'big') % 10**16:016d}"`) |
| `Users.Name` | `Pasien <HEX-UID>` |
| `Users.Tempat_Tgl_Lahir` | `-` |
| `Users.Golongan_darah` | NULL |
| `Users.Email` | NULL |
| `Users.Alamat` | `-` |
| `Users.password` | hash `rfid123` (bisa login bila perlu) |
| `Users.id_Role` | `R2` |

Sifat NIK otomatis:

- **Deterministik** — kartu yang sama selalu menghasilkan NIK yang sama,
  jadi tidak akan dobel daftar meski kartu dilepas-tempel berulang kali.
- **Konsisten 16 digit** — sesuai format NIK yang dipakai endpoint lain.

Pengaturan (opsional, `integrasi_sensor/config.example.env`):

| Variabel | Default | Keterangan |
| :--- | :--- | :--- |
| `RFID_AUTO_REGISTER` | `true` | matikan → kartu tak dikenal dilewati seperti versi awal |
| `RFID_DEFAULT_PASSWORD` | `rfid123` | password akun pasien yang dibuat otomatis |

---

## 5. Troubleshooting cepat

| Gejala | Penyebab / solusi |
| :--- | :--- |
| `smbus2 belum terpasang` | `pip install -r integrasi_sensor/requirements.txt` |
| `gagal membaca MLX90614 (PEC)` | cek wiring SDA/SCL; tambah pull-up 4,7 kΩ; cek `i2cdetect -y 1` (harus ada `5A`) |
| Reader RFID tidak mendeteksi | cek pin SPI (24/23/19/21) & RST (22); pastikan `spidev` aktif; kartu Mifare 13.56 MHz |
| `koneksi ditolak broker` | broker belum up / port beda; autentikasi aktif tapi `MQTT_USER` kosong |
| Bridge tidak menyimpan | kartu di luar rentang suhu (25–45 °C); cek log `--verbose` |
| NIK tabrakan (jarang) | hash 8 byte mod 10^16 — probabilitas sangat kecil; data sudah ada di `Users` dengan NIK sama, dilewati & dicatat log |
