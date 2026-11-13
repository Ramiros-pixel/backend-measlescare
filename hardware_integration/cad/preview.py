#!/usr/bin/env python3
"""Render preview PNG (tampak depan + isometrik) dari hasil desain.

Jalankan: python3 cad/preview.py
Hasil    : cad/out/preview_front.png, cad/out/preview_iso.png

Tampak depan digambar dari params.py (bukan dari gambar jadi) supaya angka
yang tampil selalu sama dengan angka yang dipakai generator.
Isometrik dibuat dari STL rakitan (proyeksi + painter's algorithm).
"""
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import params as P  # noqa: E402

OUT = os.path.join(HERE, "out")
SC = 2.0                     # piksel per mm pada tampak depan
PAD = 46


def mm2px(x, y):
    """(x, y) mm dari sudut kiri-bawah -> piksel gambar (Y dibalik)."""
    return (PAD + x * SC, PAD + (P.FRONT_H - y) * SC)


def front():
    W = int(P.FRONT_W * SC) + 2 * PAD
    H = int(P.FRONT_H * SC) + 2 * PAD
    im = Image.new("RGB", (W, H), (246, 247, 250))
    d = ImageDraw.Draw(im)

    # plat muka
    d.rectangle([mm2px(0, P.FRONT_H), mm2px(P.FRONT_W, 0)],
                fill=(214, 220, 232), outline=(90, 100, 120), width=2)

    # cutout layar (kaca besar -> area aktif lebih gelap)
    d.rectangle([mm2px(P.SCREEN_CUT_X0, P.SCREEN_CUT_Y1),
                 mm2px(P.SCREEN_CUT_X1, P.SCREEN_CUT_Y0)],
                fill=(28, 32, 42), outline=(60, 70, 90), width=2)
    act = [(P.SCREEN_CUT_X0 + P.LCD_BEZEL_OVERLAP + k * (P.LCD_ACTIVE_W / 6.0),
            P.SCREEN_CUT_Y0 + P.LCD_BEZEL_OVERLAP) for k in range(7)]
    d.text(mm2px(P.SCREEN_CX - 22, P.SCREEN_CY + 2), 'LAYAR 7" 1024x600',
           fill=(200, 210, 225))

    def circ(x, y, dia, fill, outline=None, label=None, lab_dy=0.0):
        cx, cy = mm2px(x, y)
        r = dia / 2.0 * SC
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill,
                  outline=outline or (70, 80, 100), width=2)
        if label:
            d.text((cx + r + 4, cy + lab_dy), label, fill=(40, 46, 60))

    # kamera + chamfer
    circ(P.CAM_CX, P.CAM_CY, P.CAM_CHAMFER_D, None, (140, 120, 90))
    circ(P.CAM_CX, P.CAM_CY, P.CAM_HOLE_D, (20, 24, 34),
         label=f"kamera O{P.CAM_HOLE_D:.0f} + chamfer {P.CAM_CHAMFER_D:.0f}", lab_dy=-8)
    circ(P.IR_CX, P.IR_CY, P.IR_HOLE_D, (60, 30, 30),
         label=f"IR MLX90614 O{P.IR_HOLE_D:.0f}", lab_dy=-8)
    for i, mx in enumerate(P.MIC_HOLES_X):
        circ(mx, P.MIC_HOLES_Y, P.MIC_HOLE_D, (30, 40, 50),
             label="mic O2.5 (3x)" if i == 0 else None, lab_dy=-14)
    circ(P.LED_PWR_XY[0], P.LED_PWR_XY[1], P.LED_HOLE_D, (60, 120, 60))
    circ(P.LED_ACT_XY[0], P.LED_ACT_XY[1], P.LED_HOLE_D, (30, 90, 150))
    d.text(mm2px(P.LED_PWR_XY[0] - 4, 20), "LED daya", fill=(40, 46, 60))
    d.text(mm2px(P.LED_ACT_XY[0] + 6, 20), "LED aktivitas", fill=(40, 46, 60))
    circ(P.BTN_XY[0], P.BTN_XY[1], P.BTN_HOLE_D, (150, 150, 160),
         label=f"tombol O{P.BTN_HOLE_D:.0f} (opsi)", lab_dy=-8)
    for i, (sx, sy) in enumerate(P.FRONT_SCREWS):
        circ(sx, sy, P.SCREW_M3_CLEAR, (250, 250, 252),
             label="6x baut M3 O3.4" if i == 0 else None, lab_dy=-8)

    d.text((8, 6), f"TAMPAK DEPAN (1:{1/SC:.1f} skala gambar) - "
                   f"{P.FRONT_W:.0f} x {P.FRONT_H:.0f} x {P.PANEL_T:.0f} mm",
           fill=(20, 24, 32))
    d.text((8, 22), "satuan mm | origin (0,0) = sudut kiri-bawah",
           fill=(90, 96, 110))
    im.save(os.path.join(OUT, "preview_front.png"))
    return os.path.join(OUT, "preview_front.png")


def iso(stl_name="00_assembly_front_body.stl", out="preview_iso.png",
        size=(460, 460)):
    import numpy as np
    import trimesh

    m = trimesh.load(os.path.join(OUT, "stl", stl_name), force="mesh")
    v = np.asarray(m.vertices, dtype=float)
    f = np.asarray(m.faces)
    # ke tengah
    v = v - (v.max(0) + v.min(0)) / 2.0
    # rotasi isometrik
    a, b = np.radians(-35.0), np.radians(28.0)
    Rz = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
    Rx = np.array([[1, 0, 0], [0, np.cos(b), -np.sin(b)], [0, np.sin(b), np.cos(b)]])
    p = v @ (Rx @ Rz).T
    xy = p[:, :2]
    lo, hi = xy.min(0), xy.max(0)
    span = (hi - lo).max()
    s = (size[0] - 40) / span
    px = (xy[:, 0] - lo[0]) * s + 20
    py = (hi[1] - xy[:, 1]) * s + 20

    # cahaya
    n = np.asarray(m.face_normals)
    L = np.array([0.35, 0.5, -0.79])
    L = L / np.linalg.norm(L)
    sh = np.clip(n @ L, 0, 1)
    base = np.array([150, 170, 205])
    cols = (base[None, :] * (0.45 + 0.55 * sh[:, None])).astype(int)

    depth = p[:, 2]
    order = np.argsort(depth[f].mean(1))
    im = Image.new("RGB", size, (246, 247, 250))
    d = ImageDraw.Draw(im)
    for i in order:
        tri = f[i]
        pts = [(float(px[k]), float(py[k])) for k in tri]
        d.polygon(pts, fill=tuple(cols[i]), outline=(70, 80, 100))
    d.text((8, 6), f"ISOMETRIK - {stl_name}", fill=(20, 24, 32))
    im.save(os.path.join(OUT, out))
    return os.path.join(OUT, out)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    print("tulis:", front())
    print("tulis:", iso())
    print("tulis:", iso("01_front_bezel.stl", "preview_bezel_iso.png"))
    print("tulis:", iso("02_body_tray.stl", "preview_body_iso.png"))
