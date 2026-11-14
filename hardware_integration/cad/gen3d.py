#!/usr/bin/env python3
"""Generator berkas 3D (STL) untuk enclosure MeaslesWatch AI.

Jalankan:  python3 cad/gen3d.py
Hasil    :  cad/out/stl/*.stl

Membutuhkan: trimesh + manifold3d (lihat requirements-cad.txt).
Tidak butuh OpenSCAD/binari CAD lain.

Cara pakai di Tinkercad: New 3D Design -> Import -> pilih file .stl.
Untuk mencetak 3D: buka STL di slicer apa pun (Cura/PrusaSlicer/Bambu).
"""

import os
import sys
import json
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import params as P
import trimesh

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "stl")
os.makedirs(OUT, exist_ok=True)

_SECTION = 96
_M3, _M25, _M2 = P.SCREW_M3_CLEAR, P.SCREW_M25_CLEAR, P.SCREW_M2_CLEAR


# --------------------------------------------------------------- primitif
def box(x0, y0, z0, x1, y1, z1):
    """Kotak dari dua sudut (mm)."""
    return trimesh.creation.box(
        extents=[abs(x1 - x0), abs(y1 - y0), abs(z1 - z0)],
        transform=trimesh.transformations.translation_matrix(
            [(x0 + x1) / 2.0, (y0 + y1) / 2.0, (z0 + z1) / 2.0]))


def cyl(cx, cy, z0, z1, d, sections=_SECTION):
    """Silinder tegak lurus bidang XY (sumbu Z) dari z0 ke z1."""
    h = abs(z1 - z0)
    m = trimesh.creation.cylinder(radius=d / 2.0, height=h, sections=sections)
    m.apply_translation([cx, cy, (z0 + z1) / 2.0])
    return m


def frustum(cx, cy, z0, z1, d0, d1, sections=_SECTION):
    """Kerucut terpancung: diameter d0 di z0, diameter d1 di z1 (sumbu Z)."""
    a = np.linspace(0, 2 * np.pi, sections, endpoint=False)
    r0, r1 = d0 / 2.0, d1 / 2.0
    bot = np.column_stack([cx + r0 * np.cos(a), cy + r0 * np.sin(a), np.full(sections, z0)])
    top = np.column_stack([cx + r1 * np.cos(a), cy + r1 * np.sin(a), np.full(sections, z1)])
    verts = np.vstack([bot, top, [[cx, cy, z0]], [[cx, cy, z1]]])
    cb, ct = 2 * sections, 2 * sections + 1
    faces = []
    for i in range(sections):
        j = (i + 1) % sections
        faces.append([i, j, sections + j])
        faces.append([i, sections + j, sections + i])
        faces.append([cb, j, i])
        faces.append([ct, sections + i, sections + j])
    m = trimesh.Trimesh(vertices=verts, faces=np.array(faces), process=True)
    m.fix_normals()
    return m


def slot(cx, cy, z0, z1, length, width, vertical=True):
    """Slot/stadium tembus (untuk ventilasi & cable tie)."""
    if vertical:
        body = box(cx - width / 2, cy - length / 2 + width / 2, z0,
                   cx + width / 2, cy + length / 2 - width / 2, z1)
        c1 = cyl(cx, cy + length / 2 - width / 2, z0, z1, width)
        c2 = cyl(cx, cy - length / 2 + width / 2, z0, z1, width)
    else:
        body = box(cx - length / 2 + width / 2, cy - width / 2, z0,
                   cx + length / 2 - width / 2, cy + width / 2, z1)
        c1 = cyl(cx + length / 2 - width / 2, cy, z0, z1, width)
        c2 = cyl(cx - length / 2 + width / 2, cy, z0, z1, width)
    return trimesh.boolean.union([body, c1, c2], engine="manifold")


def rounded_panel(x0, y0, z0, x1, y1, z1, r):
    """Plat sudut bulat (dibuat dari box dikurangi 4 silinder sudut)."""
    b = box(x0, y0, z0, x1, y1, z1)
    cut = []
    for (cx, cy) in [(x0 + r, y0 + r), (x1 - r, y0 + r), (x1 - r, y1 - r), (x0 + r, y1 - r)]:
        c = trimesh.creation.box(extents=[2 * r, 2 * r, abs(z1 - z0) + 4])
        c.apply_translation([cx - r, cy - r, (z0 + z1) / 2.0])
        cut.append(c)
    return b.difference(trimesh.boolean.union(cut, engine="manifold"), engine="manifold")


def diff(base, cuts):
    cuts = [c for c in cuts if c is not None and len(c.faces)]
    if not cuts:
        return base
    merged = trimesh.boolean.union(cuts, engine="manifold")
    return base.difference(merged, engine="manifold")


def add(base, parts):
    return trimesh.boolean.union([base] + parts, engine="manifold")


def save(mesh, name, note=""):
    mesh = mesh.copy()
    mesh.merge_vertices()
    ok = mesh.nondegenerate_faces()
    if not ok.all():
        mesh.update_faces(ok)
    mesh.remove_unreferenced_vertices()
    p = os.path.join(OUT, name)
    mesh.export(p)
    b = mesh.bounds
    info = {
        "file": name,
        "mm": [round(float(b[1][i] - b[0][i]), 2) for i in range(3)],
        "volume_cm3": round(float(mesh.volume) / 1000.0, 2),
        "watertight": bool(mesh.is_watertight),
        "note": note,
    }
    print(f"  {name:34s} {info['mm'][0]:7.2f} x {info['mm'][1]:7.2f} x "
          f"{info['mm'][2]:6.2f} mm  {info['volume_cm3']:7.2f} cm3  "
          f"watertight={info['watertight']}")
    return info


# =====================================================================
# 1. PLAT MUKA (front bezel)
# =====================================================================
def build_front_bezel():
    z0, z1 = -P.PANEL_T, 0.0
    base = rounded_panel(0, 0, z0, P.FRONT_W, P.FRONT_H, z1, 8.0)
    zc0, zc1 = z0 - 1, z1 + 1
    cuts = [
        # layar (tembus)
        trimesh.creation.box(extents=[P.SCREEN_CUT_W, P.SCREEN_CUT_H, 20],
                             transform=trimesh.transformations.translation_matrix(
                                 [P.SCREEN_CX, P.SCREEN_CY, -P.PANEL_T / 2])),
        # kamera: lubang tembus + chamfer menghadap ke dalam
        cyl(P.CAM_CX, P.CAM_CY, zc0, zc1, P.CAM_HOLE_D),
        frustum(P.CAM_CX, P.CAM_CY, -P.PANEL_T, -0.001,
                P.CAM_CHAMFER_D, P.CAM_HOLE_D),
        # sensor IR (tembus)
        cyl(P.IR_CX, P.IR_CY, zc0, zc1, P.IR_HOLE_D),
        # tombol & LED
        cyl(P.BTN_XY[0], P.BTN_XY[1], zc0, zc1, P.BTN_HOLE_D),
        cyl(P.LED_PWR_XY[0], P.LED_PWR_XY[1], zc0, zc1, P.LED_HOLE_D),
        cyl(P.LED_ACT_XY[0], P.LED_ACT_XY[1], zc0, zc1, P.LED_HOLE_D),
    ]
    for x in P.MIC_HOLES_X:
        cuts.append(cyl(x, P.MIC_HOLES_Y, zc0, zc1, P.MIC_HOLE_D))
    for (x, y) in P.FRONT_SCREWS:
        cuts.append(cyl(x, y, zc0, zc1, _M3))
    # sambungan post layar (M3) di sudut cutout
    off = 6.0
    for (sx, sy) in [(P.SCREEN_CUT_X0 - off, P.SCREEN_CUT_Y0 - off),
                     (P.SCREEN_CUT_X1 + off, P.SCREEN_CUT_Y0 - off),
                     (P.SCREEN_CUT_X0 - off, P.SCREEN_CUT_Y1 + off),
                     (P.SCREEN_CUT_X1 + off, P.SCREEN_CUT_Y1 + off)]:
        cuts.append(cyl(sx, sy, zc0, zc1, _M3))
    return diff(base, cuts)


# =====================================================================
# 2. BODI / TRAY (buka di sisi muka)
# =====================================================================
def build_body_tray():
    z0, z1 = 0.0, P.DEPTH_BODY
    base = rounded_panel(0, 0, z0, P.BODY_W, P.BODY_H, z1, 8.0)
    cavity = box(P.WALL_T, P.WALL_T, z0 - 1,
                 P.BODY_W - P.WALL_T, P.BODY_H - P.WALL_T, z1 - P.WALL_T + 1)
    tray = diff(base, [cavity])

    # lubang tembus di dinding belakang (z ~ z1-WALL_T..z1)
    bz0, bz1 = z1 - P.WALL_T - 1, z1 + 1
    holes = [
        cyl(P.GLAND_XY[0], P.GLAND_XY[1], bz0, bz1, P.GLAND_D),
        cyl(P.SWITCH_XY[0], P.SWITCH_XY[1], bz0, bz1, P.SWITCH_D),
    ]
    # ventilasi dinding belakang (slot tegak, di atas panel layar)
    for r in range(P.VENT_BACK_ROWS):
        for c in range(P.VENT_BACK_COLS):
            x = P.VENT_BACK_X0 + c * P.VENT_BACK_XPITCH
            y = P.VENT_BACK_Y0 + r * P.VENT_BACK_YPITCH
            holes.append(slot(x, y, bz0, bz1, P.VENT_BACK_LEN, P.VENT_BACK_W, vertical=True))
    # slot cable tie (horizontal)
    for (x, y) in P.TIETIE_XY:
        holes.append(slot(x, y, bz0, bz1, P.TIETIE_SLOT_H, P.TIETIE_SLOT_W, vertical=False))
    # baut plat belakang
    for (x, y) in P.FRONT_SCREWS:
        holes.append(cyl(x, y, bz0, bz1, _M3))
    # ventilasi MENEMBUS dinding samping kiri & kanan (bidang Y-Z)
    zv0 = P.VENT_Z_START
    zv1 = P.VENT_Z_START + P.VENT_SLOT_Z
    for i in range(P.VENT_COUNT):
        cy = P.VENT_Y_START + i * P.VENT_Y_PITCH
        y0, y1 = cy - P.VENT_SLOT_Y / 2.0, cy + P.VENT_SLOT_Y / 2.0
        holes.append(box(-1.0, y0, zv0, P.WALL_T + 1.0, y1, zv1))                 # kiri
        holes.append(box(P.BODY_W - P.WALL_T - 1.0, y0, zv0, P.BODY_W + 1.0, y1, zv1))  # kanan
    tray = diff(tray, holes)

    # boss baut Orange Pi 4 Pro (lubang OVAL -> toleran terhadap jarak sebenarnya)
    bosses = []
    pi_x = P.CAM_CX - P.PI_SPACING_X / 2.0
    pi_y = P.PI_CY - P.PI_SPACING_Y / 2.0
    for (bx, by) in [(pi_x, pi_y), (pi_x + P.PI_SPACING_X, pi_y),
                     (pi_x, pi_y + P.PI_SPACING_Y), (pi_x + P.PI_SPACING_X, pi_y + P.PI_SPACING_Y)]:
        bosses.append(cyl(bx, by, z1 - P.WALL_T - P.PI_BOSS_H, z1 - P.WALL_T + 0.1, 9.0))
    bosses = trimesh.boolean.union(bosses, engine="manifold")
    boss_holes = [slot(bx, by, z1 - P.WALL_T - P.PI_BOSS_H - 1, z1 - P.WALL_T + 1,
                       _M3 * 2 + P.PI_SLOT_LEN, _M3, vertical=True)
                  for (bx, by) in [(pi_x, pi_y), (pi_x + P.PI_SPACING_X, pi_y),
                                   (pi_x, pi_y + P.PI_SPACING_Y),
                                   (pi_x + P.PI_SPACING_X, pi_y + P.PI_SPACING_Y)]]
    try:
        bosses = diff(bosses, boss_holes)
        tray = add(tray, [bosses])
    except Exception as e:                    # boss gagal -> bodi tetap dipakai
        print(f"  (peringatan) boss Orange Pi dilewati: {e}")
    return tray


# =====================================================================
# 3. PLAT BELAKANG (versi terpisah - bila memakai akrilik/plywood)
# =====================================================================
def build_back_panel():
    z0, z1 = P.DEPTH_BODY, P.DEPTH_BODY + P.PANEL_T
    base = rounded_panel(0, 0, z0, P.FRONT_W, P.FRONT_H, z1, 8.0)
    cuts = [cyl(P.GLAND_XY[0], P.GLAND_XY[1], z0 - 1, z1 + 1, P.GLAND_D),
            cyl(P.SWITCH_XY[0], P.SWITCH_XY[1], z0 - 1, z1 + 1, P.SWITCH_D)]
    for r in range(P.VENT_BACK_ROWS):
        for c in range(P.VENT_BACK_COLS):
            cuts.append(slot(P.VENT_BACK_X0 + c * P.VENT_BACK_XPITCH,
                             P.VENT_BACK_Y0 + r * P.VENT_BACK_YPITCH,
                             z0 - 1, z1 + 1, P.VENT_BACK_LEN, P.VENT_BACK_W, True))
    for (x, y) in P.TIETIE_XY:
        cuts.append(slot(x, y, z0 - 1, z1 + 1, P.TIETIE_SLOT_H, P.TIETIE_SLOT_W, False))
    for (x, y) in P.FRONT_SCREWS:
        cuts.append(cyl(x, y, z0 - 1, z1 + 1, _M3))
    return diff(base, cuts)


# =====================================================================
# 4. BRACKET
# =====================================================================
def build_bracket_camera():
    t = P.CAM_BRACKET_T
    base = rounded_panel(0, 0, 0, P.CAM_BRACKET_W, P.CAM_BRACKET_H, t, 4.0)
    cuts = [cyl(P.CAM_BRACKET_W / 2, P.CAM_BRACKET_H / 2, -1, t + 1, P.CAM_BRACKET_HOLE_D)]
    cx, cy = P.CAM_BRACKET_W / 2, P.CAM_BRACKET_H / 2
    for (dx, dy) in [(15, 0), (-15, 0), (0, 15), (0, -15)]:
        cuts.append(cyl(cx + dx, cy + dy, -1, t + 1, _M25))
    for (dx, dy) in [(12, 0), (-12, 0), (0, 12), (0, -12)]:   # varian PCB 32x32
        cuts.append(cyl(cx + dx, cy + dy, -1, t + 1, _M25))
    return diff(base, cuts)


def build_bracket_ir():
    t = P.IR_BRACKET_T
    base = rounded_panel(0, 0, 0, P.IR_BRACKET_W, P.IR_BRACKET_H, t, 3.0)
    cx, cy = P.IR_BRACKET_W / 2, P.IR_BRACKET_H / 2
    cuts = [cyl(cx, cy, -1, t + 1, P.IR_HOLE_D)]
    # pocket PCB GY-906 (17 x 11 x 3) di sisi belakang
    cuts.append(box(cx - P.IR_POCKET_W / 2, cy - P.IR_POCKET_H / 2, -1,
                    cx + P.IR_POCKET_W / 2, cy + P.IR_POCKET_H / 2, t - 3.0 + 0.001))
    for (dx, dy) in [(7.6, 4.6), (-7.6, 4.6), (7.6, -4.6), (-7.6, -4.6)]:
        cuts.append(cyl(cx + dx, cy + dy, -1, t + 1, _M2))
    return diff(base, cuts)


def build_standoff_lcd(h=16.0):
    base = cyl(0, 0, 0, h, P.LCD_STANDOFF_OD + 8.0)
    return diff(base, [cyl(0, 0, -1, h + 1, _M3)])


def build_standoff_ir(h=14.0):
    base = cyl(0, 0, 0, h, P.LCD_STANDOFF_OD + 6.0)
    return diff(base, [cyl(0, 0, -1, h + 1, _M25)])


def build_corner_bracket():
    t = P.CORNER_BRACKET_T
    a = box(0, 0, 0, P.CORNER_BRACKET_W, t, P.CORNER_BRACKET_H)
    b = box(0, 0, 0, t, P.CORNER_BRACKET_W, P.CORNER_BRACKET_H)
    base = add(a, [b])
    cuts = []
    for (x, y, z) in [(6, 6, 6), (24, 6, 6), (6, 24, 6), (24, 24, 6),
                      (6, 6, 24), (24, 6, 24)]:
        if y < t:                      # lubang di flens horizontal -> sumbu Z
            c = cyl(x, y, -1, t + 1, _M3)
        else:                          # lubang di flens vertikal -> sumbu Y
            c = trimesh.creation.cylinder(radius=_M3 / 2, height=t + 2, sections=_SECTION)
            c.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
            c.apply_translation([x, t / 2, z])
        cuts.append(c)
    return diff(base, cuts)


def build_foot():
    t = P.FOOT_T
    base = rounded_panel(0, 0, 0, P.FOOT_W, P.FOOT_D, t, 6.0)
    cuts = []
    for (dx, dy) in [(8, 8), (52, 8), (8, 32), (52, 32)]:
        cuts.append(cyl(dx, dy, -1, t + 1, _M3))
    # reses karet anti-slip (opsional)
    cuts.append(box(8, 8, -0.001, P.FOOT_W - 8, P.FOOT_D - 8, 1.5))
    return diff(base, cuts)


def build_boss_tripod():
    base = cyl(0, 0, 0, 12.0, 24.0)
    return diff(base, [cyl(0, 0, 2.0, 12.0 + 1, P.TRIPOD_INSERT_D)])


# =====================================================================
# ASSEMBLY (semua part pada posisinya)
# =====================================================================
def build_assembly(bezel, tray):
    parts = [bezel, tray]
    return trimesh.boolean.union(parts, engine="manifold")


def main():
    print("Membangun STL (engine=manifold)...")
    manifest = []

    bezel = build_front_bezel()
    manifest.append(save(bezel, "01_front_bezel.stl",
                         "plat muka, semua cutout tembus + chamfer kamera"))

    tray = build_body_tray()
    manifest.append(save(tray, "02_body_tray.stl",
                         "bodi buka muka + boss Orange Pi + ventilasi"))

    back = build_back_panel()
    manifest.append(save(back, "03_back_panel.stl",
                         "plat belakang terpisah (akrilik/plywood)"))

    manifest.append(save(build_bracket_camera(), "10_bracket_camera.stl",
                         "bracket modul kamera 46x46, lubang M12 OD16"))
    manifest.append(save(build_bracket_ir(), "11_bracket_ir.stl",
                         "bracket GY-906, pocket PCB 17.6x11.6x3"))
    manifest.append(save(build_standoff_lcd(), "12_standoff_lcd_h16.stl", "x4"))
    manifest.append(save(build_standoff_ir(), "13_standoff_ir_h14.stl", "x4"))
    manifest.append(save(build_corner_bracket(), "14_corner_bracket.stl",
                         "siku penyambung 30x30, x4"))
    manifest.append(save(build_foot(), "15_foot.stl", "kaki 60x40, x2"))
    manifest.append(save(build_boss_tripod(), "16_boss_tripod.stl",
                         "boss mur 1/4in-20 (mounting tripod)"))

    asm = build_assembly(bezel, tray)
    manifest.append(save(asm, "00_assembly_front_body.stl",
                         "tampilan rakitan: plat muka + bodi"))

    with open(os.path.join(OUT, "MANIFEST_stl.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"\n{len(manifest)} STL ditulis ke {OUT}")
    bad = [m for m in manifest if not m["watertight"]]
    print(f"watertight: {len(manifest) - len(bad)}/{len(manifest)}")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
