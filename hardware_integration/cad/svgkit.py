"""Pembangun path SVG/DXF 2D (satuan mm) tanpa dependensi eksternal.

Menghasilkan SATU path gabungan dengan fill-rule="evenodd" sehingga lubang
benar-benar berlubang saat diimpor ke Tinkercad (Impor > pilih SVG > Extrude).
"""

import math

# ------------------------------------------------------------------ primitif
def rect_path(x, y, w, h):
    """Persegi, arah searah jarum jam."""
    return (f"M {x:.4f} {y:.4f} L {x + w:.4f} {y:.4f} "
            f"L {x + w:.4f} {y + h:.4f} L {x:.4f} {y + h:.4f} Z")


def circle_path(cx, cy, d, seg=64):
    """Lingkaran sebagai kubik Bezier (4 segmen, presisi tinggi)."""
    r = d / 2.0
    k = 0.5522847498307936 * r
    cx, cy = float(cx), float(cy)
    return (
        f"M {cx:.4f} {cy - r:.4f} "
        f"C {cx + k:.4f} {cy - r:.4f} {cx + r:.4f} {cy - k:.4f} {cx + r:.4f} {cy:.4f} "
        f"C {cx + r:.4f} {cy + k:.4f} {cx + k:.4f} {cy + r:.4f} {cx:.4f} {cy + r:.4f} "
        f"C {cx - k:.4f} {cy + r:.4f} {cx - r:.4f} {cy + k:.4f} {cx - r:.4f} {cy:.4f} "
        f"C {cx - r:.4f} {cy - k:.4f} {cx - k:.4f} {cy - r:.4f} {cx:.4f} {cy - r:.4f} Z"
    )


def rounded_rect_path(x, y, w, h, r):
    """Persegi sudut bulat."""
    r = min(r, w / 2, h / 2)
    k = 0.5522847498307936 * r
    x1, y1 = x + w, y + h
    return (
        f"M {x + r:.4f} {y:.4f} "
        f"L {x1 - r:.4f} {y:.4f} "
        f"C {x1 - r + k:.4f} {y:.4f} {x1:.4f} {y + r - k:.4f} {x1:.4f} {y + r:.4f} "
        f"L {x1:.4f} {y1 - r:.4f} "
        f"C {x1:.4f} {y1 - r + k:.4f} {x1 - r + k:.4f} {y1:.4f} {x1 - r:.4f} {y1:.4f} "
        f"L {x + r:.4f} {y1:.4f} "
        f"C {x + r - k:.4f} {y1:.4f} {x:.4f} {y1 - r + k:.4f} {x:.4f} {y1 - r:.4f} "
        f"L {x:.4f} {y + r:.4f} "
        f"C {x:.4f} {y + r - k:.4f} {x + r - k:.4f} {y:.4f} {x + r:.4f} {y:.4f} Z"
    )


def slot_path(cx, cy, length, width, vertical=True):
    """Slot (oblong) = persegi panjang + 2 setengah lingkaran (stadium)."""
    r = width / 2.0
    if vertical:
        x0, x1 = cx - r, cx + r
        y0, y1 = cy - length / 2.0 + r, cy + length / 2.0 - r
        return (rect_path(x0, y0, width, y1 - y0)
                + " " + circle_path(cx, cy + length / 2.0 - r, width)
                + " " + circle_path(cx, cy - length / 2.0 + r, width))
    else:
        y0, y1 = cy - r, cy + r
        x0, x1 = cx - length / 2.0 + r, cx + length / 2.0 - r
        return (rect_path(x0, y0, x1 - x0, width)
                + " " + circle_path(cx + length / 2.0 - r, cy, width)
                + " " + circle_path(cx - length / 2.0 + r, cy, width))


# ------------------------------------------------------------------ dokumen
def write_svg(path, width, height, shape_paths, title="", note=""):
    """Tulis SVG 1:1 mm. shape_paths = daftar d (subpath) SOLID.

    Subpath pertama idealnya outline utama; subpath berikutnya yang berada
    di dalam akan otomatis jadi LUBANG karena fill-rule evenodd.
    """
    d = " ".join(shape_paths)
    meta = ""
    if title:
        meta += f"  <!-- {title} -->\n"
    if note:
        meta += f"  <!-- catatan: {note} -->\n"
    svg = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" version="1.1"\n'
        f'     width="{width}mm" height="{height}mm"\n'
        f'     viewBox="0 0 {width} {height}">\n'
        f'{meta}'
        '  <g id="board" fill="black" stroke="none">\n'
        f'    <path fill-rule="evenodd" d="{d}"/>\n'
        '  </g>\n'
        '</svg>\n'
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)
    return path


def write_annotated_svg(path, width, height, items):
    """SVG beranotasi (garis ukur + label) - untuk dokumentasi.

    items = list of dict:
      {"type":"outline","x","y","w","h"}
      {"type":"cut","x","y","w","h"} / {"type":"hole","cx","cy","d"}
      {"type":"dim_h","x0","x1","y","label"}
      {"type":"dim_v","y0","y1","x","label"}
      {"type":"note","x","y","text"}
      {"type":"line","x0","y0","x1","y1","dash"}
    """
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           f'<svg xmlns="http://www.w3.org/2000/svg" version="1.1" '
           f'width="{width}mm" height="{height}mm" viewBox="0 0 {width} {height}">',
           '<style>text{font-family:DejaVu Sans,Helvetica,Arial,sans-serif;}</style>',
           '<rect x="0" y="0" width="{w}" height="{h}" fill="white"/>'.format(w=width, h=height)]

    solid, cuts, anno = [], [], []
    for it in items:
        t = it["type"]
        if t in ("outline", "cut", "hole"):
            if t == "outline":
                solid.append(rect_path(it["x"], it["y"], it["w"], it["h"]))
            elif t == "cut":
                cuts.append(rect_path(it["x"], it["y"], it["w"], it["h"]))
            else:
                cuts.append(circle_path(it["cx"], it["cy"], it["d"]))
        elif t == "dim_h":
            y = it["y"]
            x0, x1 = it["x0"], it["x1"]
            anno.append(f'<line x1="{x0}" y1="{y}" x2="{x1}" y2="{y}" stroke="#c00" '
                        f'stroke-width="0.3" marker-start="url(#a)" marker-end="url(#a)"/>')
            anno.append(f'<text x="{(x0 + x1) / 2:.2f}" y="{y - 1.5}" font-size="4.2" '
                        f'fill="#c00" text-anchor="middle">{it["label"]}</text>')
        elif t == "dim_v":
            x = it["x"]
            y0, y1 = it["y0"], it["y1"]
            anno.append(f'<line x1="{x}" y1="{y0}" x2="{x}" y2="{y1}" stroke="#c00" '
                        f'stroke-width="0.3" marker-start="url(#a)" marker-end="url(#a)"/>')
            anno.append(f'<text x="{x + 1.6:.2f}" y="{(y0 + y1) / 2:.2f}" font-size="4.2" '
                        f'fill="#c00" text-anchor="start">{it["label"]}</text>')
        elif t == "line":
            dash = ' stroke-dasharray="3 2"' if it.get("dash") else ""
            anno.append(f'<line x1="{it["x0"]}" y1="{it["y0"]}" x2="{it["x1"]}" '
                        f'y2="{it["y1"]}" stroke="#08c" stroke-width="0.25"{dash}/>')
        elif t == "note":
            anno.append(f'<text x="{it["x"]}" y="{it["y"]}" font-size="5.5" fill="#036">'
                        f'{it["text"]}</text>')

    out.append('<defs><marker id="a" markerWidth="6" markerHeight="6" refX="3" refY="3" '
               'orient="auto"><path d="M0,3 L6,0 L6,6 z" fill="#c00"/></marker></defs>')
    if solid:
        out.append('<path fill="#d9e8f5" stroke="#456" stroke-width="0.5" '
                   f'd="{" ".join(solid)}"/>')
    if cuts:
        out.append('<path fill="white" stroke="#c00" stroke-width="0.5" '
                   f'd="{" ".join(cuts)}"/>')
    out.extend(anno)
    out.append('</svg>')
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    return path


def write_dxf(path, layers):
    """DXF minimal (R12) tanpa dependensi - untuk laser cut.

    layers = {"CUT": [("line",x0,y0,x1,y1), ("circle",cx,cy,r)], ...}
    """
    ents = []
    for lname, items in layers.items():
        for it in items:
            if it[0] == "line":
                _, x0, y0, x1, y1 = it
                ents.append(f"0\nLINE\n8\n{lname}\n10\n{x0:.4f}\n20\n{y0:.4f}\n"
                            f"30\n0.0\n11\n{x1:.4f}\n21\n{y1:.4f}\n31\n0.0\n")
            elif it[0] == "circle":
                _, cx, cy, r = it
                ents.append(f"0\nCIRCLE\n8\n{lname}\n10\n{cx:.4f}\n20\n{cy:.4f}\n"
                            f"30\n0.0\n40\n{r:.4f}\n")
            elif it[0] == "arc":
                _, cx, cy, r, a0, a1 = it
                ents.append(f"0\nARC\n8\n{lname}\n10\n{cx:.4f}\n20\n{cy:.4f}\n"
                            f"30\n0.0\n40\n{r:.4f}\n50\n{a0:.4f}\n51\n{a1:.4f}\n")
    header = "0\nSECTION\n2\nHEADER\n0\nENDSEC\n"
    body = "0\nSECTION\n2\nENTITIES\n" + "".join(ents) + "0\nENDSEC\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write(header + body + "0\nEOF\n")
    return path


def rounded_rect_entities(x, y, w, h, r, segs=16):
    """Kembalikan entitas (line/arc) untuk persegi sudut bulat - untuk DXF."""
    r = min(r, w / 2, h / 2)
    out = [
        ("line", x + r, y, x + w - r, y),
        ("arc", x + w - r, y + r, r, 270, 360),
        ("line", x + w, y + r, x + w, y + h - r),
        ("arc", x + w - r, y + h - r, r, 0, 90),
        ("line", x + w - r, y + h, x + r, y + h),
        ("arc", x + r, y + h - r, r, 90, 180),
        ("line", x, y + h - r, x, y + r),
        ("arc", x + r, y + r, r, 180, 270),
    ]
    return out


def circle_entities(cx, cy, d):
    return [("circle", cx, cy, d / 2.0)]


def rect_entities(x, y, w, h):
    return [
        ("line", x, y, x + w, y),
        ("line", x + w, y, x + w, y + h),
        ("line", x + w, y + h, x, y + h),
        ("line", x, y + h, x, y),
    ]


def slot_entities(cx, cy, length, width, vertical=True):
    r = width / 2.0
    if vertical:
        return [
            ("line", cx - r, cy - length / 2 + r, cx - r, cy + length / 2 - r),
            ("arc", cx, cy + length / 2 - r, r, 0, 180),
            ("line", cx + r, cy + length / 2 - r, cx + r, cy - length / 2 + r),
            ("arc", cx, cy - length / 2 + r, r, 180, 360),
        ]
    return [
        ("line", cx - length / 2 + r, cy - r, cx + length / 2 - r, cy - r),
        ("arc", cx + length / 2 - r, cy, r, 270, 360),
        ("line", cx + length / 2 - r, cy + r, cx - length / 2 + r, cy + r),
        ("arc", cx - length / 2 + r, cy, r, 90, 180),
    ]
