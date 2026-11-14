#!/usr/bin/env python3
"""Generator berkas 2D (SVG 1:1 mm + DXF) untuk enclosure MeaslesWatch AI.

Jalankan:  python3 cad/gen2d.py
Hasil    :  cad/out/*.svg  dan  cad/out/*.dxf

Cara pakai di Tinkercad (tanpa plugin apa pun):
  1. New 3D Design  ->  Import  ->  pilih file .svg
  2. Tinkercad menanyakan ketebalan -> pilih "Extrude" (ketebalan bebas)
  3. Karena SVG ini memakai fill-rule evenodd, semua lubang otomatis bolong.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import params as P
from svgkit import (rect_path, circle_path, rounded_rect_path, slot_path,
                    write_svg, write_annotated_svg, write_dxf,
                    rect_entities, circle_entities, slot_entities,
                    rounded_rect_entities)

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT, exist_ok=True)
M3, M25, M2 = P.SCREW_M3_CLEAR, P.SCREW_M25_CLEAR, P.SCREW_M2_CLEAR


# =====================================================================
# 1. PLAT MUKA (front bezel)
# =====================================================================
def front_bezel_paths():
    """Kembalikan (subpath_solid, subpath_lubang, daftar_cutout_untuk_dxf)."""
    solid = [rounded_rect_path(0, 0, P.FRONT_W, P.FRONT_H, 8.0)]
    holes = [
        ("layar_7in", rounded_rect_path(P.SCREEN_CUT_X0, P.SCREEN_CUT_Y0,
                                        P.SCREEN_CUT_W, P.SCREEN_CUT_H, 2.0)),
        ("kamera", circle_path(P.CAM_CX, P.CAM_CY, P.CAM_HOLE_D)),
        ("sensor_IR", circle_path(P.IR_CX, P.IR_CY, P.IR_HOLE_D)),
        ("tombol_power", circle_path(*P.BTN_XY, P.BTN_HOLE_D)),
        ("led_daya", circle_path(*P.LED_PWR_XY, P.LED_HOLE_D)),
        ("led_aktif", circle_path(*P.LED_ACT_XY, P.LED_HOLE_D)),
    ]
    for i, x in enumerate(P.MIC_HOLES_X, 1):
        holes.append((f"mic_{i}", circle_path(x, P.MIC_HOLES_Y, P.MIC_HOLE_D)))
    for i, (x, y) in enumerate(P.FRONT_SCREWS, 1):
        holes.append((f"baut_M3_{i}", circle_path(x, y, M3)))
    return solid, holes


def gen_front_bezel():
    solid, holes = front_bezel_paths()
    paths = solid + [h[1] for h in holes]

    # 1a. SVG part murni 1:1 (untuk impor Tinkercad)
    write_svg(os.path.join(OUT, "01_front_bezel_1to1.svg"), P.FRONT_W, P.FRONT_H,
              paths, title="MeaslesWatch AI - plat muka 220x300 mm",
              note="fill-rule evenodd: semua subpath di dalam outline = lubang")

    # 1b. SVG murni untuk LASER CUT (outline cukup, tanpa baut sudut? tetap disertakan)
    write_svg(os.path.join(OUT, "01_front_bezel_lasercut.svg"), P.FRONT_W, P.FRONT_H,
              paths, title="plat muka - laser cut",
              note="1 unit = 1 mm, skala cetak 1:1")

    # 1c. Lembar A3 beranotasi (untuk dibaca manusia / dicetak & ditempel)
    W, H = 420.0, 297.0
    dx, dy = 100.0, -0.0
    s = ['<?xml version="1.0" encoding="UTF-8"?>',
         f'<svg xmlns="http://www.w3.org/2000/svg" version="1.1" '
         f'width="{W}mm" height="{H}mm" viewBox="0 0 {W} {H}">',
         '<style>text{font-family:DejaVu Sans,Helvetica,Arial,sans-serif;}</style>',
         f'<rect x="0" y="0" width="{W}" height="{H}" fill="white"/>',
         '<defs><marker id="arw" markerWidth="6" markerHeight="6" refX="3" refY="3" '
         'orient="auto"><path d="M0,3 L6,0 L6,6 z" fill="#c00"/></marker></defs>',
         f'<g transform="translate({dx},{dy})">',
         '<path fill="#d9e8f5" stroke="#456" stroke-width="0.6" '
         f'd="{solid[0]}"/>',
         '<path fill="white" stroke="#c00" stroke-width="0.6" '
         f'd="{" ".join(h[1] for h in holes)}"/>']
    # garis tengah
    for (cx, cy, label) in [(P.CAM_CX, P.CAM_CY, "kamera"), (P.IR_CX, P.IR_CY, "IR")]:
        s.append(f'<line x1="{cx}" y1="0" x2="{cx}" y2="{P.FRONT_H}" stroke="#08c" '
                 f'stroke-width="0.2" stroke-dasharray="4 2"/>')
        s.append(f'<line x1="0" y1="{cy}" x2="{P.FRONT_W}" y2="{cy}" stroke="#08c" '
                 f'stroke-width="0.2" stroke-dasharray="4 2"/>')
    # garis ukur
    s.append(f'<line x1="0" y1="312" x2="{P.FRONT_W}" y2="312" stroke="#c00" '
             f'stroke-width="0.3" marker-start="url(#arw)" marker-end="url(#arw)"/>')
    s.append(f'<text x="{P.FRONT_W/2}" y="318" font-size="5" fill="#c00" '
             f'text-anchor="middle">220.0</text>')
    s.append(f'<line x1="-12" y1="0" x2="-12" y2="{P.FRONT_H}" stroke="#c00" '
             f'stroke-width="0.3" marker-start="url(#arw)" marker-end="url(#arw)"/>')
    s.append(f'<text x="-15" y="{P.FRONT_H/2}" font-size="5" fill="#c00" '
             f'text-anchor="middle" transform="rotate(-90 -15 {P.FRONT_H/2})">300.0</text>')
    # label komponen
    labels = [
        (P.SCREEN_CX, P.SCREEN_CY, 'LAYAR 7in — cutout 158.2 x 89.9 (active 154.21 x 85.92 + overlap 2)'),
        (P.CAM_CX, P.CAM_CY - 3, 'KAMERA Hog 22.0 (chamfer 27 belakang)'),
        (P.IR_CX, P.IR_CY - 2, 'IR MLX90614 Hog 14.0'),
        (P.MIC_HOLES_X[1], P.MIC_HOLES_Y + 4, 'mic 3x Hog 2.5'),
        (P.BTN_XY[0], P.BTN_XY[1] - 8, 'tombol Hog 12'),
        (P.LED_PWR_XY[0] - 6, P.LED_PWR_XY[1] - 7, 'LED 2x Hog 5'),
        (P.FRONT_W / 2, 8, '6x baut M3 sudut (Hog 3.4, inset 8 mm)'),
    ]
    for (x, y, t) in labels:
        s.append(f'<text x="{x}" y="{y}" font-size="4.4" fill="#036" '
                 f'text-anchor="middle">{t}</text>')
    s.append('</g>')
    s.append(f'<text x="14" y="16" font-size="7" fill="#000">'
             f'MeaslesWatch AI — PLAT MUKA (front bezel) 220 x 300 x {P.PANEL_T} mm</text>')
    s.append(f'<text x="14" y="26" font-size="5" fill="#333">'
             f'Skala 1:1 mm · akrilik/plywood 6 mm atau 3D print · lubang = potong tembus</text>')
    s.append('<text x="14" y="284" font-size="4.6" fill="#036">'
             'Verifikasi: modul layar 164.9 x 106.96 · kamera PCB 38x38 (lens M12) · '
             'MLX90614 GY-906 PCB 17x11, can TO-39 OD 9.1</text>')
    s.append('</svg>')
    with open(os.path.join(OUT, "01_front_bezel_A3_dimensi.svg"), "w",
              encoding="utf-8") as f:
        f.write("\n".join(s))

    # 1d. DXF (untuk laser cut / CNC)
    layers = {"CUT_OUTER": rounded_rect_entities(0, 0, P.FRONT_W, P.FRONT_H, 8.0),
              "CUT_INNER": (rect_entities(P.SCREEN_CUT_X0, P.SCREEN_CUT_Y0,
                                          P.SCREEN_CUT_W, P.SCREEN_CUT_H)
                            + circle_entities(P.CAM_CX, P.CAM_CY, P.CAM_HOLE_D)
                            + circle_entities(P.IR_CX, P.IR_CY, P.IR_HOLE_D)
                            + circle_entities(*P.BTN_XY, P.BTN_HOLE_D)
                            + circle_entities(*P.LED_PWR_XY, P.LED_HOLE_D)
                            + circle_entities(*P.LED_ACT_XY, P.LED_HOLE_D)
                            + [e for x in P.MIC_HOLES_X
                               for e in circle_entities(x, P.MIC_HOLES_Y, P.MIC_HOLE_D)]
                            + [e for (x, y) in P.FRONT_SCREWS
                               for e in circle_entities(x, y, M3)]),
              }
    write_dxf(os.path.join(OUT, "01_front_bezel.dxf"), layers)
    return paths


# =====================================================================
# 2. DINDING SAMPING (kiri/kanan) - profil dilihat dari samping
# =====================================================================
def gen_side_panel():
    W, H = P.BODY_D, P.BODY_H      # 54 x 300
    solid = [rounded_rect_path(0, 0, W, H, 4.0)]
    holes = []
    # ventilasi: 6 slot (VENT_SLOT_Y x VENT_SLOT_Z) - sumbu X = kedalaman (Z 3D),
    # sumbu Y = ketinggian (Y 3D). Selaras dengan gen3d.py.
    x_c = W - P.VENT_Z_START - 0.5 * P.VENT_SLOT_Z
    for i in range(P.VENT_COUNT):
        cy = P.VENT_Y_START + i * P.VENT_Y_PITCH
        holes.append(slot_path(x_c, cy, P.VENT_SLOT_Z, P.VENT_SLOT_Y, vertical=False))
    # baut sambung dinding samping
    for (x, y) in [(W - 8, 8), (8, 8), (W - 8, H - 8), (8, H - 8)]:
        holes.append(circle_path(x, y, M3))
    write_svg(os.path.join(OUT, "03_side_panel_left_1to1.svg"), W, H, solid + holes,
              title="dinding samping kiri/kanan 54 x 300 mm",
              note="x=0 sisi BELAKANG, x=54 sisi DEPAN (menempel plat muka)")
    write_dxf(os.path.join(OUT, "03_side_panel.dxf"),
              {"CUT_OUTER": rounded_rect_entities(0, 0, W, H, 4.0),
               "CUT_INNER": ([e for i in range(P.VENT_COUNT)
                              for e in slot_entities(x_c, P.VENT_Y_START + i * P.VENT_Y_PITCH,
                                                     P.VENT_SLOT_Z, P.VENT_SLOT_Y, False)]
                             + [e for (x, y) in [(W - 8, 8), (8, 8), (W - 8, H - 8), (8, H - 8)]
                                for e in circle_entities(x, y, M3)])})
    return W, H


# =====================================================================
# 3. PLAT BELAKANG (versi laser cut / akrilik)
# =====================================================================
def gen_back_panel():
    W, H = P.FRONT_W, P.FRONT_H
    solid = [rounded_rect_path(0, 0, W, H, 8.0)]
    holes = []
    for i, (x, y) in enumerate(P.FRONT_SCREWS, 1):
        holes.append(circle_path(x, y, M3))
    holes.append(circle_path(*P.GLAND_XY, P.GLAND_D))
    holes.append(circle_path(*P.SWITCH_XY, P.SWITCH_D))
    # ventilasi keluar (grid atas)
    for r in range(2):
        for c in range(7):
            holes.append(slot_path(50 + c * 20, 262 + r * 22, 20, 4, vertical=True))
    # lubang kabel tie untuk merapikan kabel (RAB no.13)
    for (x, y) in [(30, 30), (190, 30), (30, 130), (190, 130)]:
        holes.append(slot_path(x, y, 8, 4, vertical=False))
    write_svg(os.path.join(OUT, "02_back_panel_1to1.svg"), W, H, solid + holes,
              title="plat belakang 220x300 - gland kabel + saklar + ventilasi",
              note="Hog gland 20 mm (kiri bawah), saklar KCD1 13 mm, vent 14 slot")
    write_dxf(os.path.join(OUT, "02_back_panel.dxf"),
              {"CUT_OUTER": rounded_rect_entities(0, 0, W, H, 8.0),
               "CUT_INNER": ([e for (x, y) in P.FRONT_SCREWS for e in circle_entities(x, y, M3)]
                             + circle_entities(*P.GLAND_XY, P.GLAND_D)
                             + circle_entities(*P.SWITCH_XY, P.SWITCH_D)
                             + [e for r in range(2) for c in range(7)
                                for e in slot_entities(50 + c * 20, 262 + r * 22, 20, 4, True)]
                             + [e for (x, y) in [(30, 30), (190, 30), (30, 130), (190, 130)]
                                for e in slot_entities(x, y, 8, 4, False)])})
    return W, H


# =====================================================================
# 4. DINDING ATAS & BAWAH
# =====================================================================
def gen_top_bottom():
    W, H = P.BODY_INNER_W, P.BODY_D      # 212 x 54
    solid = [rounded_rect_path(0, 0, W, H, 4.0)]
    holes = []
    for (x, y) in [(8, P.BODY_D - 8), (W - 8, P.BODY_D - 8), (8, 8), (W - 8, 8)]:
        holes.append(circle_path(x, y, M3))
    for (gx, gy) in P.TIETIE_XY:
        holes.append(slot_path(gx, gy, P.TIETIE_SLOT_H, P.TIETIE_SLOT_W, vertical=True))
    write_svg(os.path.join(OUT, "04_top_bottom_1to1.svg"), W, H, solid + holes,
              title="dinding atas & bawah 212 x 54 mm (x2)",
              note="y=0 sisi BELAKANG, y=54 sisi DEPAN")
    write_dxf(os.path.join(OUT, "04_top_bottom.dxf"),
              {"CUT_OUTER": rounded_rect_entities(0, 0, W, H, 4.0),
               "CUT_INNER": ([e for (x, y) in [(8, P.BODY_D - 8), (W - 8, P.BODY_D - 8),
                                               (8, 8), (W - 8, 8)]
                              for e in circle_entities(x, y, M3)]
                             + [e for (gx, gy) in P.TIETIE_XY
                                for e in slot_entities(gx, gy, P.TIETIE_SLOT_H,
                                                       P.TIETIE_SLOT_W, True)])})
    return W, H


# =====================================================================
# 5. LEMBAR BRACKET & STANDOFF (1 lembark 3D print)
# =====================================================================
def gen_bracket_sheet():
    W, H = 220.0, 200.0
    solid, holes, labels = [], [], []
    y_off = 0.0

    # --- 5a. Bracket kamera 46x46
    bx, by = 10.0, 10.0
    solid.append(rounded_rect_path(bx, by, P.CAM_BRACKET_W, P.CAM_BRACKET_H, 4.0))
    holes.append(circle_path(bx + P.CAM_BRACKET_W / 2, by + P.CAM_BRACKET_H / 2,
                             P.CAM_BRACKET_HOLE_D))
    for (dx, dy) in [(15, 0), (-15, 0), (0, 15), (0, -15)]:
        holes.append(circle_path(bx + P.CAM_BRACKET_W / 2 + dx,
                                 by + P.CAM_BRACKET_H / 2 + dy, M25))
    labels.append((bx + P.CAM_BRACKET_W / 2, by + P.CAM_BRACKET_H + 6,
                   "bracket kamera 46x46, H16 + 4x M2.5 (spacing 30)"))
    labels.append((bx + P.CAM_BRACKET_W / 2, by + P.CAM_BRACKET_H + 11,
                   "kamera cadangan: tambah lubang spacing 24 utk PCB 32x32"))

    # --- 5b. Bracket sensor IR 26x20
    ix, iy = 70.0, 10.0
    solid.append(rounded_rect_path(ix, iy, P.IR_BRACKET_W, P.IR_BRACKET_H, 3.0))
    holes.append(circle_path(ix + P.IR_BRACKET_W / 2, iy + P.IR_BRACKET_H / 2,
                             P.IR_HOLE_D))
    for (dx, dy) in [(7.6, 4.6), (-7.6, 4.6), (7.6, -4.6), (-7.6, -4.6)]:
        holes.append(circle_path(ix + P.IR_BRACKET_W / 2 + dx,
                                 iy + P.IR_BRACKET_H / 2 + dy, M2))
    labels.append((ix + P.IR_BRACKET_W / 2, iy + P.IR_BRACKET_H + 6,
                   "bracket IR 26x20, H14 + 4x M2"))
    labels.append((ix + P.IR_BRACKET_W / 2, iy + P.IR_BRACKET_H + 11,
                   "pocket PCB GY-906 17.6 x 11.6 x 3"))

    # --- 5c. Standoff/ring layar (2 posisi)
    sx, sy = 110.0, 55.0
    solid.append(circle_path(sx, sy, P.LCD_STANDOFF_OD + 8))
    holes.append(circle_path(sx, sy, M3))
    labels.append((sx, sy + 14, "standoff layar OD8 H16 (x4)"))
    txx, txy = 150.0, 60.0
    solid.append(circle_path(txx, txy, 24.0))
    holes.append(circle_path(txx, txy, P.TRIPOD_INSERT_D))
    labels.append((txx, txy + 18, "boss mur 1/4in-20 (tripod) H12"))

    # --- 5d. Bracket siku sudut 30x30 (x4)
    for k, (cx, cy) in enumerate([(180.0, 15.0), (180.0, 60.0),
                                  (180.0, 105.0), (180.0, 150.0)]):
        solid.append(rounded_rect_path(cx, cy, P.CORNER_BRACKET_W,
                                       P.CORNER_BRACKET_H, 3.0))
        for (dx, dy) in [(6, 6), (24, 6), (6, 24), (24, 24)]:
            holes.append(circle_path(cx + dx, cy + dy, M3))
        labels.append((cx + 15, cy + 34, f"siku {k+1}"))

    # --- 5e. Kaki karet 60x40 (x2)
    for k, (cx, cy) in enumerate([(15.0, 120.0), (95.0, 120.0)]):
        solid.append(rounded_rect_path(cx, cy, P.FOOT_W, P.FOOT_D, 5.0))
        for (dx, dy) in [(8, 8), (52, 8), (8, 32), (52, 32)]:
            holes.append(circle_path(cx + dx, cy + dy, M3))
        labels.append((cx + 30, cy + 46, f"kaki {k+1} 60x40"))

    write_svg(os.path.join(OUT, "05_brackets_1to1.svg"), W, H, solid + holes,
              title="lembar bracket & standoff (3D print, bukan laser cut)",
              note="potong semua bentuk lalu cetak terpisah; tebal 4 mm")
    write_annotated_svg(os.path.join(OUT, "05_brackets_A3_label.svg"), W, H, [
        {"type": "outline", "x": 10, "y": 10, "w": 200, "h": 180}] + [
        {"type": "note", "x": x, "y": y, "text": t} for (x, y, t) in labels])
    return W, H


# =====================================================================
# VERIFIKASI
# =====================================================================
def verify():
    from params import clearances
    c = clearances()
    ok = True
    lines = ["=== VERIFIKASI GEOMETRI ==="]
    for key, d in c.items():
        if key == "enclosure":
            lines.append(f"[enclosure] kedalaman total {d['depth_total_mm']:.1f} mm, "
                         f"ruang dalam {d['inner_w']:.1f} x {d['inner_h']:.1f} x "
                         f"{d['inner_d']:.1f} mm")
            lines.append(f"  Orange Pi 4 Pro masuk  : {d['pi_fits']}")
            lines.append(f"  Layar 7in masuk plat   : {d['lcd_fits']}")
            ok &= d["pi_fits"] and d["lcd_fits"]
        elif key == "back_wall":
            lines.append(f"[back_wall] PCB Orange Pi di "
                         f"{[round(v, 1) for v in d['pi_board_rect']]}")
            lines.append(f"  lubang glad bebas PCB  : {d['gland_ok']}")
            lines.append(f"  saklar bebas PCB       : {d['switch_ok']}")
            ok &= d["gland_ok"] and d["switch_ok"]
        else:
            lines.append(f"[{key}] half-angle harus >= {d['fov_half_deg']:.0f} deg -> "
                         f"didapat {d['allowable_half_deg']:.1f} deg : {'OK' if d['ok'] else 'GAGAL'}")
            ok &= d["ok"]
    # cek cutout layar tidak menabrak lubang lain
    others = [("kamera", P.CAM_CX, P.CAM_CY, P.CAM_HOLE_D),
              ("IR", P.IR_CX, P.IR_CY, P.IR_HOLE_D),
              ("mic", P.MIC_HOLES_X[0], P.MIC_HOLES_Y, P.MIC_HOLE_D),
              ("tombol", P.BTN_XY[0], P.BTN_XY[1], P.BTN_HOLE_D)]
    import math
    for name, x, y, d in others:
        r = d / 2.0
        near_x = min(max(x, P.SCREEN_CUT_X0), P.SCREEN_CUT_X1)
        near_y = min(max(y, P.SCREEN_CUT_Y0), P.SCREEN_CUT_Y1)
        dist = math.hypot(x - near_x, y - near_y)
        good = dist >= r + 3.0
        lines.append(f"[jarak] {name} ke cutout layar = {dist:.1f} mm "
                     f"(butuh >= {r + 3:.1f}) : {'OK' if good else 'TERLALU DEKAT'}")
        ok &= good
    lines.append(f"=== HASIL: {'SEMUA OK' if ok else 'ADA MASALAH'} ===")
    print("\n".join(lines))
    return ok


def main():
    gen_front_bezel()
    gen_back_panel()
    gen_side_panel()
    gen_top_bottom()
    gen_bracket_sheet()
    print("SVG/DXF selesai ->", OUT)
    ok = verify()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
