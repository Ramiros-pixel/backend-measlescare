#!/usr/bin/env python3
"""Helper changetracks: buat track (before/after/diff/PROMPT.md) untuk berkas yang berubah.

Pemakaian:
  python3 changetracks/tools/track.py --file app/routers/auth.py \
      --prompt "tambah endpoint X" --summary "tambah-endpoint-x" \
      --reason "..." [--related a.py,b.py] [--before-from-baseline] [--dry-run]

Tanpa --dry-run, berkas `before` diambil dari baseline bila tersedia dan
--before-from-baseline dipakai; jika tidak, before = isi berkas saat ini
(pakai ini SETELAH perubahan hanya bila --after disediakan).
"""
import argparse, datetime, difflib, hashlib, json, os, re, sys

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CT = os.path.join(BASE, "changetracks")
BLF = os.path.join(CT, "_baseline", "files")
MANIFEST = os.path.join(CT, "MANIFEST.json")


def flat(rel):
    return rel.replace("\\", "/").replace("/", "__")


def slug(s, maxlen=48):
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s.lower()).strip("-")
    return s[:maxlen].rstrip("-") or "perubahan"


def next_num(folder):
    if not os.path.isdir(folder):
        return 1
    nums = [int(d[:3]) for d in os.listdir(folder) if len(d) > 3 and d[:3].isdigit()]
    return (max(nums) + 1) if nums else 1


def make_track(rel, prompt, summary, reason, related=None, before=None, after=None, date=None):
    rel = rel.replace("\\", "/")
    folder = os.path.join(CT, flat(rel))
    os.makedirs(folder, exist_ok=True)
    n = next_num(folder)
    d = date or datetime.date.today().isoformat()
    tdir = os.path.join(folder, "%03d_%s_%s" % (n, d, slug(summary)))
    os.makedirs(tdir, exist_ok=True)

    live = os.path.join(BASE, rel)
    ext = os.path.splitext(rel)[1] or ".txt"
    if after is None and os.path.exists(live):
        after = open(live, "rb").read()

    def w(name, data):
        if data is None:
            return False
        open(os.path.join(tdir, name), "wb").write(data)
        return True

    if not w("before" + ext, before):
        open(os.path.join(tdir, "before.MISSING"), "w").write("Berkas belum ada sebelum perubahan ini.\n")
    if not w("after" + ext, after):
        open(os.path.join(tdir, "after.DELETED"), "w").write("Berkas dihapus pada perubahan ini.\n")

    bl = (before or b"").decode("utf-8", "replace").splitlines(keepends=True)
    al = (after or b"").decode("utf-8", "replace").splitlines(keepends=True)
    diff = "".join(difflib.unified_diff(bl, al, fromfile="a/" + rel, tofile="b/" + rel, n=3))
    open(os.path.join(tdir, "diff.patch"), "w").write(diff or "(tidak ada perbedaan isi)\n")

    open(os.path.join(tdir, "PROMPT.md"), "w").write(
        "# Track %03d — `%s`\n\n" % (n, rel)
        + "- **Waktu:** %s\n" % datetime.datetime.now().astimezone().isoformat(timespec="seconds")
        + "- **Berkas:** `%s`\n" % rel
        + "- **Ringkasan:** %s\n" % summary
        + "- **Status sebelum:** %s\n" % ("ada" if before is not None else "BELUM ADA")
        + "- **Status sesudah:** %s\n" % ("ada" if after is not None else "DIHAPUS")
        + "- **Ukuran:** %d -> %d byte\n" % (len(before or b""), len(after or b""))
        + "- **SHA256 sesudah:** %s\n\n" % (hashlib.sha256(after).hexdigest() if after else "-")
        + "## Prompt asli\n\n> %s\n\n" % prompt
        + "## Alasan / konteks\n\n%s\n\n" % reason
        + "## Berkas lain yang ikut berubah pada prompt ini\n\n"
        + ("\n".join("- `%s`" % r for r in (related or [])) or "- (tidak ada)")
        + "\n\n## Cara memverifikasi\n\n```bash\ndiff -u before%s after%s    # atau: cat diff.patch\n```\n" % (ext, ext)
    )
    return tdir


def log_track(rel, tdir, summary, prompt):
    m = json.load(open(MANIFEST)) if os.path.exists(MANIFEST) else {"tracks": []}
    m.setdefault("tracks", [])
    m["tracks"].append({
        "file": rel,
        "folder": os.path.relpath(tdir, CT),
        "summary": summary,
        "prompt": prompt,
        "at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
    })
    m["updated_at"] = m["tracks"][-1]["at"]
    json.dump(m, open(MANIFEST, "w"), indent=2, ensure_ascii=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--summary", required=True)
    ap.add_argument("--reason", default="")
    ap.add_argument("--related", default="")
    ap.add_argument("--before-from-baseline", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    rel = a.file.replace("\\", "/")
    before = None
    if a.before_from_baseline:
        bp = os.path.join(BLF, flat(rel))
        if os.path.exists(bp):
            before = open(bp, "rb").read()
        else:
            print("PERINGATAN: baseline untuk %s tidak ada -> before=MISSING" % rel, file=sys.stderr)

    if a.dry_run:
        print("[dry-run] akan membuat track untuk %s (summary=%s, before=%s)"
              % (rel, a.summary, "baseline" if before is not None else "tidak ada"))
        return 0

    tdir = make_track(rel, a.prompt, a.summary, a.reason,
                      related=[r for r in a.related.split(",") if r], before=before)
    log_track(rel, tdir, a.summary, a.prompt)
    print(os.path.relpath(tdir, BASE))
    return 0


if __name__ == "__main__":
    sys.exit(main())
