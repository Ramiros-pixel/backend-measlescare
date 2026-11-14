#!/usr/bin/env python3
"""Verifikasi hasil desain MeaslesWatch AI (ukur ulang, jangan percaya gambar).

Jalankan: python3 cad/verify.py      (butuh trimesh + scipy + networkx)

Yang diperiksa:
  1. Tiap STL: dimensi bounding box + watertight (syarat bisa dicetak/diimpor).
  2. Tembus/tidaknya tiap lubang plat muka -> diuji dengan sinar (ray casting):
       - sinar tepat di tengah lubang HARUS lolos (tidak memotong material)
       - sinar di titik material HARUS memotong (kontrol positif)
  3. Kedalaman rongga bodi + lebar dinding.
  4. Jarak antar lubang (kamera vs IR) vs perhitungan vignetting.

Keluar dengan kode 1 bila ada satu saja FAIL.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import params as P
import numpy as np
import trimesh

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "stl")
TOL = 0.6

fails = []


def check(name, ok, detail=""):
    print(f"  [{'PASS' if ok else 'FAIL'}] {name:46s} {detail}")
    if not ok:
        fails.append(name)
    return ok


def load(name):
    m = trimesh.load(os.path.join(OUT, name))
    if isinstance(m, trimesh.Scene):
        m = trimesh.util.concatenate(list(m.geometry.values()))
    return m


def through(mesh, x, y, z_hi=1.0, z_lo=-400.0):
    """True bila kolom (x,y) TIDAK terkena material antara z_lo..z_hi (=lubang tembus)."""
    origins = np.array([[x, y, z_hi]])
    dirs = np.array([[0.0, 0.0, -1.0]])
    locs, idx_ray, idx_tri = mesh.ray.intersects_location(
        ray_origins=origins, ray_directions=dirs, multiple_hits=True)
    return len(locs) == 0, len(locs)


def main():
    print("== 1. Berkas STL: dimensi & watertight ==")
    expect = {
        "01_front_bezel.stl": (P.FRONT_W, P.FRONT_H, P.PANEL_T),
        "02_body_tray.stl": (P.BODY_W, P.BODY_H, P.DEPTH_BODY),
        "03_back_panel.stl": (P.FRONT_W, P.FRONT_H, P.PANEL_T),
        "10_bracket_camera.stl": (P.CAM_BRACKET_W, P.CAM_BRACKET_H, P.CAM_BRACKET_T),
        "11_bracket_ir.stl": (P.IR_BRACKET_W, P.IR_BRACKET_H, P.IR_BRACKET_T),
        "15_foot.stl": (P.FOOT_W, P.FOOT_D, P.FOOT_T),
        "16_boss_tripod.stl": (24.0, 24.0, 12.0),
    }
    for f in sorted(os.listdir(OUT)):
        if not f.endswith(".stl"):
            continue
        m = load(f)
        b = m.bounds
        dim = [b[1][i] - b[0][i] for i in range(3)]
        check(f"{f} watertight", bool(m.is_watertight),
              f"{dim[0]:.2f} x {dim[1]:.2f} x {dim[2]:.2f} mm")
        if f in expect:
            ex = expect[f]
            ok = all(abs(dim[i] - ex[i]) <= 0.05 for i in range(3))
            check(f"{f} dimensi = params", ok,
                  f"ukur {'x'.join(f'{d:.2f}' for d in dim)} vs "
                  f"target {'x'.join(f'{d:.2f}' for d in ex)}")

    bez = load("01_front_bezel.stl")
    tray = load("02_body_tray.stl")

    print("\n== 2. Lubang plat muka tembus (uji sinar dari dalam ke luar) ==")
    holes = [
        ("kamera", P.CAM_CX, P.CAM_CY, True),
        ("sensor IR", P.IR_CX, P.IR_CY, True),
        ("tombol daya", P.BTN_XY[0], P.BTN_XY[1], True),
        ("LED daya", P.LED_PWR_XY[0], P.LED_PWR_XY[1], True),
        ("LED status", P.LED_ACT_XY[0], P.LED_ACT_XY[1], True),
        ("mikrofon kiri", P.MIC_HOLES_X[0], P.MIC_HOLES_Y, True),
        ("mikrofon tengah", P.MIC_HOLES_X[1], P.MIC_HOLES_Y, True),
        ("mikrofon kanan", P.MIC_HOLES_X[2], P.MIC_HOLES_Y, True),
        ("baut M3 kiri-bawah", 8.0, 8.0, True),
        ("pos post layar kiri-bawah",
         P.SCREEN_CX - P.SCREEN_CUT_W / 2 - 6, P.SCREEN_CY - P.SCREEN_CUT_H / 2 - 6, True),
    ]
    for nm, x, y, want_hole in holes:
        free, n = through(bez, x, y)
        check(f"lubang {nm}", free == want_hole, f"sinar memotong {n} permukaan (ingin lolos)")

    print("\n== 3. Kontrol negatif: titik material HARUS terhalang ==")
    # CATATAN: titik harus benar-benar di area material - bukan di dalam cutout
    # layar (30.9..189.1 x 73.0..163.0) dan bukan di lubang post M3
    # (24.89/195.11 x 67.04/168.96).
    solid_pts = [
        ("margin kiri", 15.0, 118.0),               # di luar cutout layar, kiri
        ("margin kanan", 205.0, 118.0),             # di luar cutout layar, kanan
        ("bawah layar", 110.0, 55.0),               # antara cutout (Y0=73) & baris tombol
        ("antara layar & IR", 110.0, 180.0),        # antara cutout (Y1=163) & lubang IR (Y 197..213)
    ]
    for nm, x, y in solid_pts:
        free, n = through(bez, x, y)
        check(f"material {nm}", not free, f"sinar memotong {n} permukaan (ingin terhalang)")

    print("\n== 4. Cutout layar: sudut dalam cutout harus tembus ==")
    for nm, x, y in [
        ("layar kiri-bawah", P.SCREEN_CX - P.SCREEN_CUT_W / 2 + 4, P.SCREEN_CY - P.SCREEN_CUT_H / 2 + 4),
        ("layar kanan-atas", P.SCREEN_CX + P.SCREEN_CUT_W / 2 - 4, P.SCREEN_CY + P.SCREEN_CUT_H / 2 - 4),
        ("layar tengah", P.SCREEN_CX, P.SCREEN_CY),
    ]:
        free, n = through(bez, x, y)
        check(f"cutout {nm}", free, f"sinar memotong {n} permukaan (ingin lolos)")

    print("\n== 5. Bodi: kedalaman & rongga ==")
    b = tray.bounds
    check("kedalaman bodi", abs((b[1][2] - b[0][2]) - P.DEPTH_BODY) <= 0.05,
          f"{b[1][2] - b[0][2]:.2f} mm (target {P.DEPTH_BODY})")
    free_center, n = through(tray, P.BODY_W / 2, P.BODY_H / 2, z_hi=2.0, z_lo=-1.0)
    check("rongga dalam bodi (dari depan terbuka)", free_center,
          f"sinar memotong {n} permukaan (ingin lolos)")
    free_wall, n = through(tray, P.BODY_W / 2, P.BODY_H / 2, z_hi=P.DEPTH_BODY + 5,
                           z_lo=P.DEPTH_BODY - P.WALL_T / 2)
    check("dinding belakang ada", not free_wall, f"sinar memotong {n} permukaan")

    print("\n== 5b. Dinding belakang vs PCB Orange Pi ==")
    bw = P.clearances()["back_wall"]
    check("lubang glad tidak tertutup PCB Pi", bw["gland_ok"],
          f"PCB di x {bw['pi_board_rect'][0]:.0f}..{bw['pi_board_rect'][2]:.0f}, "
          f"y {bw['pi_board_rect'][1]:.0f}..{bw['pi_board_rect'][3]:.0f}")
    check("lubang saklar tidak tertutup PCB Pi", bw["switch_ok"],
          f"glad di {P.GLAND_XY}, saklar di {P.SWITCH_XY}")

    print("\n== 6. Vignetting (geometri optik) ==")
    import math
    cl = P.clearances()
    cam, ir = cl["camera"], cl["ir"]
    check("bukaan kamera >= FOV 45 deg", cam["ok"],
          f"half-angle = {cam['allowable_half_deg']:.1f} deg "
          f"(butuh >= {cam['fov_half_deg']:.0f} deg)")
    check("bukaan sensor IR >= FOV 45 deg", ir["ok"],
          f"half-angle = {ir['allowable_half_deg']:.1f} deg "
          f"(butuh >= {ir['fov_half_deg']:.0f} deg)")
    encl = cl["enclosure"]
    check("Orange Pi muat di rongga", encl["pi_fits"],
          f"rongga {encl['inner_w']:.0f} x {encl['inner_h']:.0f} x {encl['inner_d']:.0f} mm")
    check("layar muat di plat muka", encl["lcd_fits"],
          f"cutout {P.SCREEN_CUT_W:.1f} x {P.SCREEN_CUT_H:.1f} mm")
    d = math.hypot(P.CAM_CX - P.IR_CX, P.CAM_CY - P.IR_CY)
    need = (P.CAM_HOLE_D + P.IR_HOLE_D) / 2.0 + 4.0
    check("jarak kamera<->IR (perlu >=)", d + 0.001 >= need,
          f"{d:.1f} mm (min {need:.1f} mm agar dinding >=4 mm)")

    print("\n" + ("=== SEMUA PASS ===" if not fails else f"=== {len(fails)} FAIL: {fails} ==="))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
