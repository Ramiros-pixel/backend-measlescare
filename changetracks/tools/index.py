#!/usr/bin/env python3
"""Bangun ulang changetracks/INDEX.md dari struktur folder track."""
import datetime, json, os

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CT = os.path.join(BASE, "changetracks")

rows = []
for entry in sorted(os.listdir(CT)):
    fdir = os.path.join(CT, entry)
    if not os.path.isdir(fdir) or entry.startswith("_") or entry == "tools":
        continue
    rel = entry.replace("__", "/")
    for td in sorted(os.listdir(fdir)):
        tdir = os.path.join(fdir, td)
        if not os.path.isdir(tdir):
            continue
        num, date, slug = (td.split("_", 2) + ["", "", ""])[:3]
        pf = os.path.join(tdir, "PROMPT.md")
        summary, prompt = slug, ""
        if os.path.exists(pf):
            for line in open(pf, encoding="utf-8"):
                if line.startswith("> ") and not prompt:
                    prompt = line[2:].strip()
                if line.startswith("- **Ringkasan:**"):
                    summary = line.split("**Ringkasan:**")[1].strip()
        rows.append((rel, num, date, summary, prompt[:90], os.path.join(entry, td)))

out = [
    "# Index perubahan — changetracks",
    "",
    "Dibangun otomatis oleh `tools/index.py`. Jangan sunting manual.",
    "",
    "Total track: **%d** pada **%d** berkas · diperbarui %s"
    % (len(rows), len({r[0] for r in rows}), datetime.datetime.now().astimezone().isoformat(timespec="seconds")),
    "",
]
if rows:
    out += ["| Berkas | # | Tanggal | Ringkasan | Folder |",
            "| :--- | :--- | :--- | :--- | :--- |"]
    for rel, num, date, summary, prompt, folder in rows:
        out.append("| `%s` | %s | %s | %s | `%s` |" % (rel, num, date, summary, folder))
else:
    out.append("_Belum ada track._")
out += ["", "## Isi tiap folder track", "",
        "- `before.<ext>` / `before.MISSING` — isi sebelum perubahan",
        "- `after.<ext>` / `after.DELETED` — isi sesudah perubahan",
        "- `diff.patch` — unified diff before -> after",
        "- `PROMPT.md` — prompt asli, alasan, berkas terkait", ""]
open(os.path.join(CT, "INDEX.md"), "w", encoding="utf-8").write("\n".join(out))
print("INDEX.md: %d track" % len(rows))
