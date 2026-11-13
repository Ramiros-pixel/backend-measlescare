"""
Sumber tunggal (single source of truth) dimensi enclosure MeaslesWatch AI.

Satuan  : milimeter (mm)
Orientasi: origin (0,0) = sudut KIRI-BAWAH plat muka.
           X ke kanan, Y ke atas, Z ke belakang (kedalaman bodi).
           Jadi pengamat/user berada di sisi Z negatif.

Semua nilai di sini dipakai bersama oleh:
  - gen2d.py      -> SVG 1:1 (untuk diimpor ke Tinkercad / laser cut) + DXF
  - gen3d.py      -> STL siap cetak 3D / siap diimpor ke Tinkercad
  - openscad/*.scad -> versi parametrik OpenSCAD (script CAD)
  - documentation.md

Sumber angka:
  [RAB] = RAB MeaslesWatchAI.pdf (daftar komponen yang benar-benar dibeli)
  [DS]  = datasheet / halaman produk resmi pabrikan (tautan di documentation.md)
  [DES] = keputusan desain kami (lihat bagian "Asumsi" di documentation.md)
"""

# =====================================================================
# 0. BAHAN & KETEBALAN
# =====================================================================
PANEL_T     = 6.0     # tebal plat muka & belakang (akrilik/plywood/3D print) [DES]
WALL_T      = 4.0     # tebal dinding bodi (3D print)                             [DES]
DEPTH_BODY  = 54.0    # kedalaman bodi (dinding samping)                          [DES]
DEPTH_TOTAL = DEPTH_BODY + PANEL_T          # = 60 mm total kedalaman kiosk      [DES]

SCREW_M3_CLEAR  = 3.4   # lubang lewat M3
SCREW_M25_CLEAR = 2.7   # lubang lewat M2.5
SCREW_M2_CLEAR  = 2.2   # lubang lewat M2
INSET_CORNER    = 8.0   # jarak baut sudut dari tepi plat

# =====================================================================
# 1. PLAT MUKA  (front bezel) - 220 x 300 mm
# =====================================================================
FRONT_W = 220.0
FRONT_H = 300.0

# --- 1a. Layar: 7" IPS 1024x600 HDMI kapasitif, modul 164.9 x 106.96 x 8  [RAB][DS]
#         Active area presisi: 154.2144 x 85.92 mm  [DS]
#         Layar ditanam LANDSCAPE (lanskap) di tengah plat.
#         Cutout = active area + bezel 1.9/2.04 mm tiap sisi -> menutup pinggir
#         kaca sentuh sehingga tidak ada celah cahaya bocor.
LCD_ACTIVE_W = 154.2144     # [DS]
LCD_ACTIVE_H = 85.92        # [DS]
LCD_MODULE_W = 164.90       # [DS] outline modul (Waveshare 7inch HDMI LCD (C))
LCD_MODULE_H = 106.96       # [DS] termasuk area konektor/board
LCD_MODULE_T = 8.0          # [DS] tebal total modul (kaca + PCB)
LCD_BEZEL_OVERLAP = 2.0     # [DES] tumpuan plat muka menutupi tepi kaca

SCREEN_CUT_W = LCD_ACTIVE_W + 2 * LCD_BEZEL_OVERLAP     # 158.21
SCREEN_CUT_H = LCD_ACTIVE_H + 2 * LCD_BEZEL_OVERLAP     # 89.92
SCREEN_CX    = 110.0        # [DES] center X (tengah plat)
SCREEN_CY    = 118.0        # [DES] center Y

SCREEN_CUT_X0 = SCREEN_CX - SCREEN_CUT_W / 2            # 30.9
SCREEN_CUT_X1 = SCREEN_CX + SCREEN_CUT_W / 2            # 189.1
SCREEN_CUT_Y0 = SCREEN_CY - SCREEN_CUT_H / 2            # 73.0
SCREEN_CUT_Y1 = SCREEN_CY + SCREEN_CUT_H / 2            # 163.0

# Sudut kaca layar (sudut luar) untuk referensi gambar kerja:
LCD_GLASS_W = 164.90        # [DS] lebar kaca (sumbu X tampak depan)
LCD_GLASS_H = 100.00        # [DS] tinggi kaca (bagian 106.96 sisanya = board konektor)

# --- 1b. Kamera: modul USB IMX415, PCB 38 x 38 mm (kompatibel 32 x 32)  [RAB][DS]
#         Lens holder M12, OD barrel + jam nut ~ 16 mm  [DS]
CAM_CX      = 110.0
CAM_CY      = 246.0                 # [DES] 54 mm dari tepi atas plat
CAM_HOLE_D  = 24.0                  # [DES] lihat hitungan vignetting di documentation.md
CAM_CHAMFER_D = 30.0                # [DES] chamfer 45 deg di sisi dalam
CAM_RECESS  = 3.0                   # [DES] lensa depan maks 3 mm di belakang plat muka
CAM_PCB_A   = 38.0                  # [DS] lubang baut pada PCB 38x38
CAM_PCB_B   = 32.0                  # [DS] varian PCB 32x32
CAM_PCB_HOLE_A = 30.0               # [DS] jarak lubang baut utk PCB 38x38 (2 x 15 mm dari center)
CAM_PCB_HOLE_B = 24.0               # [DS] jarak lubang baut utk PCB 32x32

# --- 1c. Sensor suhu inframerah MLX90614 (modul GY-906)  [RAB]
#         PCB modul 17 x 11 mm, can TO-39 OD 9.1 mm, FOV 90 deg  [DS]
IR_CX       = 110.0
IR_CY       = 205.0                 # [DES] 26 mm di bawah kamera, sebidang center
IR_HOLE_D   = 16.0                  # [DES] wajib: 14 mm -> vignetting (31.5 < 45 deg), lihat documentation.md
IR_CAN_OD   = 9.1                   # [DS]
IR_PCB_W    = 17.0                  # [DS]
IR_PCB_H    = 11.0                  # [DS]
IR_RECESS   = 1.5                   # [DES] permukaan can maks 1.5 mm di belakang plat muka

# --- 1d. Mikrofon ganda pada modul kamera (perlu jalur suara)  [DS]
MIC_HOLES_X  = (96.0, 110.0, 124.0)
MIC_HOLES_Y  = 222.0
MIC_HOLE_D   = 2.5

# --- 1e. Panel indikator & tombol (baris bawah)  [DES]
LED_PWR_XY   = (85.0, 34.0)
LED_ACT_XY   = (105.0, 34.0)
LED_HOLE_D   = 5.0
BTN_XY       = (160.0, 34.0)
BTN_HOLE_D   = 12.0                 # tombol push-metal / rocker mini

# --- 1f. Baut plat muka
FRONT_SCREWS = [
    (INSET_CORNER, INSET_CORNER),
    (FRONT_W - INSET_CORNER, INSET_CORNER),
    (INSET_CORNER, FRONT_H - INSET_CORNER),
    (FRONT_W - INSET_CORNER, FRONT_H - INSET_CORNER),
    (INSET_CORNER, FRONT_H / 2),
    (FRONT_W - INSET_CORNER, FRONT_H / 2),
]
FRONT_LOGO_BOX = (110.0, 52.0, 60.0, 14.0)   # area logo (tidak dipotong)

# =====================================================================
# 2. BODI (tray) - 220 x 300 x 54, buka di sisi muka
# =====================================================================
BODY_W = FRONT_W
BODY_H = FRONT_H
BODY_D = DEPTH_BODY
BODY_INNER_W = BODY_W - 2 * WALL_T      # 212
BODY_INNER_H = BODY_H - 2 * WALL_T      # 292

# --- 2a. Lubang keluar kabel di dinding belakang
#         HARUS di bawah tepi bawah PCB Orange Pi (board 56 mm, center PI_CY=72
#         -> tepi bawah y=44); kalau di tengah (110,60) lubangnya tertutup board.
GLAND_XY = (110.0, 24.0)                # [DES] 20 mm dari tepi bawah
GLAND_D  = 20.0                         # grommet PG-7/PG-9 + HDMI + USB-C

# --- 2b. Saklar daya utama (opsional, dinding belakang)
SWITCH_XY = (110.0, 200.0)
SWITCH_D  = 13.0                        # rocker KCD1

# --- 2c. Ventilasi: slot menembus dinding samping kiri & kanan
#         Slot berbentuk persegi panjang pada bidang Y-Z (tebal 4 mm searah X,
#         menembus dinding setebal WALL_T). Bukan diruang kosong rongga.
VENT_SLOT_Y = 4.0                       # tinggi slot (sumbu Y)
VENT_SLOT_Z = 30.0                      # panjang slot (sumbu Z, arah kedalaman)
VENT_Z_START = 12.0                     # mulai 12 mm dari plat muka
VENT_Y_START = 60.0                     # slot pertama (sumbu Y)
VENT_Y_PITCH = 14.0
VENT_COUNT = 6                          # 6 slot tiap sisi -> Y 60..130
# ventilasi tambahan di dinding belakang (di atas panel layar)
VENT_BACK_COLS = 7
VENT_BACK_ROWS = 2
VENT_BACK_X0 = 50.0
VENT_BACK_XPITCH = 20.0
VENT_BACK_Y0 = 262.0
VENT_BACK_YPITCH = 22.0
VENT_BACK_LEN = 20.0
VENT_BACK_W = 4.0

# --- 2d. Slot cable tie / jalur kabel (RAB no.13 "bracket, bauttie, spacer, cable")
TIETIE_SLOT_W = 4.0
TIETIE_SLOT_H = 8.0
TIETIE_XY = [(60.0, 20.0), (160.0, 20.0), (60.0, 280.0), (160.0, 280.0)]

# --- 2e. Boss baut untuk Orange Pi 4 Pro (89 x 56 mm)  [RAB][DS]
#         PENTING: jarak lubang baut board ini BELUM diverifikasi ke unit fisik.
#         Karena itu dipakai lubang OVAL (slotted) supaya toleran +/- 2 mm.
PI_BOARD_W = 89.0                       # [DS]
PI_BOARD_H = 56.0                       # [DS]
PI_HOLE_INSET = 3.5                     # [DS] standar SBC
PI_BOSS_H = 8.0
PI_CX = 110.0
PI_CY = 72.0                            # [DES] PCB 89x56 -> x 65.5..154.5, y 44..100
PI_SPACING_X = PI_BOARD_W - 2 * PI_HOLE_INSET      # 82
PI_SPACING_Y = PI_BOARD_H - 2 * PI_HOLE_INSET      # 49
PI_SLOT_LEN = 4.0                       # panjang slot (toleransi verifikasi)

# --- 2f. Boss baut untuk PCB layar (dipegang ring bracket, bukan langsung)
LCD_POST_XY_FROM_CUT = 6.0              # post M3 di sudut cutout layar + 6 mm ke luar

# =====================================================================
# 3. BRACKET
# =====================================================================
CAM_BRACKET_W = 46.0
CAM_BRACKET_H = 46.0
CAM_BRACKET_T = 4.0
CAM_BRACKET_HOLE_D = 16.0               # leher lensa M12

IR_BRACKET_W = 26.0
IR_BRACKET_H = 20.0
IR_BRACKET_T = 4.0
IR_POCKET_W = IR_PCB_W + 0.6            # 17.6 -> PCB masuk pas
IR_POCKET_H = IR_PCB_H + 0.6            # 11.6

CORNER_BRACKET_W = 30.0
CORNER_BRACKET_H = 30.0
CORNER_BRACKET_T = 4.0

LCD_STANDOFF_OD = 8.0
LCD_STANDOFF_H = 16.0                   # jarak kaca ke plat muka

FOOT_W = 60.0
FOOT_D = 40.0
FOOT_T = 8.0
TRIPOD_INSERT_D = 9.0                   # boss untuk mur 1/4"-20

# =====================================================================
# 4. RINGKASAN UNTUK DOKUMENTASI / VERIFIKASI
# =====================================================================
def clearances():
    """Hitungan bebas-vignetting (dipakai verifikasi otomatis + dokumentasi)."""
    import math
    out = {}

    # Kamera: 90 deg horizontal FOV -> half 45 deg.
    r_hole = CAM_HOLE_D / 2.0
    r_lens = 16.0 / 2.0                 # OD barrel + jam nut
    out["camera"] = {
        "fov_half_deg": 45.0,
        "allowable_half_deg": math.degrees(math.atan2(r_hole - r_lens, CAM_RECESS)),
        "ok": math.degrees(math.atan2(r_hole - r_lens, CAM_RECESS)) >= 45.0,
    }

    # MLX90614: 90 deg FOV -> half 45 deg, can OD 9.1 mm.
    r_hole = IR_HOLE_D / 2.0
    r_can = IR_CAN_OD / 2.0
    out["ir"] = {
        "fov_half_deg": 45.0,
        "allowable_half_deg": math.degrees(math.atan2(r_hole - r_can, IR_RECESS)),
        "ok": math.degrees(math.atan2(r_hole - r_can, IR_RECESS)) >= 45.0,
    }

    # Lubang dinding belakang tidak boleh tertutup PCB Orange Pi.
    px0, px1 = PI_CX - PI_BOARD_W / 2.0, PI_CX + PI_BOARD_W / 2.0
    py0, py1 = PI_CY - PI_BOARD_H / 2.0, PI_CY + PI_BOARD_H / 2.0

    def free_of_board(cx, cy, dia):
        r = dia / 2.0
        return (cx + r < px0) or (cx - r > px1) or (cy + r < py0) or (cy - r > py1)

    out["back_wall"] = {
        "pi_board_rect": [px0, py0, px1, py1],
        "gland_ok": free_of_board(*GLAND_XY, GLAND_D),
        "switch_ok": free_of_board(*SWITCH_XY, SWITCH_D),
    }

    out["enclosure"] = {
        "depth_total_mm": DEPTH_TOTAL,
        "inner_w": BODY_INNER_W,
        "inner_h": BODY_INNER_H,
        "inner_d": BODY_D - WALL_T,
        "pi_fits": (PI_BOARD_W < BODY_INNER_W - 10) and (PI_BOARD_H < BODY_INNER_H - 10),
        "lcd_fits": (SCREEN_CUT_W < FRONT_W - 20) and (SCREEN_CUT_H < FRONT_H - 20),
    }
    return out


PARTS_2D = [
    # (nama, lebar, tinggi, keterangan)
    ("01_front_bezel", FRONT_W, FRONT_H, "Plat muka - semua cutout"),
    ("02_back_panel", FRONT_W, FRONT_H, "Plat belakang (versi laser cut)"),
    ("03_side_panel", BODY_D, BODY_H, "Dinding samping kiri/kanan x2"),
    ("04_top_bottom", BODY_D, BODY_INNER_W, "Dinding atas/bawah x2"),
    ("05_brackets", 200.0, 200.0, "Bracket kamera, IR, standoff, sudut"),
]


if __name__ == "__main__":
    import json
    print(json.dumps(clearances(), indent=2, ensure_ascii=False))
