# 05 — Urutan rakit, baut, dan jalur kabel

## Bahan yang perlu disiapkan

| Item | Qty | Catatan |
|---|---|---|
| Baut M3 × 16 countersunk | 6 | plat muka ↔ bodi |
| Baut M3 × 8 | ± 20 | bracket, boss, dinding |
| Baut M3 × 6 | 8 | modul LCD ke standoff |
| Standoff M3 (female-female) 16 mm | 4 | landasan LCD |
| Baut self-tapping M2,5 × 6 | 4 | PCB Orange Pi ke boss oval |
| Baut M2,5 × 6 | 4 | PCB kamera / IR ke bracket |
| Grommet / gland PG-9 | 1 | lubang kabel Ø20 |
| Cable tie 2,5 × 100 mm | 6 | slot 4 × 8 mm |
| Kaki karet Ø10 | 4 | alas |

## Urutan rakit (jangan dibalik)

1. **Keringkan dulu (dry fit).** Cetak/potong semua part, lalu tumpuk tanpa
   baut. Pastikan modul layar masuk cutout tanpa dipaksa.
2. **Bracket kamera & IR.** Pasang bracket ke **plat muka** dari sisi dalam
   (baut M3 × 6). Bracket kamera punya 2 set lubang — pilih yang cocok dengan
   jarak lubang PCB modul Anda (30 mm atau 24 mm).
3. **Modul layar.** Kencangkan standoff 16 mm ke plat muka di 4 titik sudut
   cutout, lalu pasang modul layar dari **dalam**. Standoff menahan board
   layar, kaca tetap duduk di bibir cutout.
4. **Bodi (tray): boss Orange Pi.** Boss 8 mm + lubang oval ada di dinding
   belakang. Pasang PCB Orange Pi, kencangkan **jangan terlalu keras** — PCB
   bisa retak. Kalau jarak lubang board Anda meleset, geser saja di dalam slot
   oval (toleransi ± 2 mm).
5. **Bodi: ventilasi & cable tie.** Rakit dinding samping dan atas/bawah ke
   plat belakang pakai siku sudut 30 × 30.
6. **Kabel.** Rute kabel lewat slot cable tie:
   - HDMI + USB touch layar → ke board
   - USB kamera → board
   - I²C sensor IR (SDA/SCL/3V3/GND) → header GPIO board
   - USB-C daya → keluar lewat **gland Ø20** di belakang (bawah)
   - Pastikan kabel **tidak menekan** PCB dan **tidak** di jalur vent
7. **Tutup & kunci.** Pasang plat muka ke bodi dengan 6 baut M3 × 16.
   Kencangkan berselang-seling (atas-bawah, kiri-kanan) supaya tidak miring.
8. **Uji sebelum dipakai.** Colok daya, pastikan:
   - layar menyala & sentuh berfungsi
   - kamera terdeteksi (cek endpoint `GET /camera/status` di backend)
   - sensor IR terbaca (cek `GET /sensor/ir`)
   - suhu CPU stabil di bawah ambang

## Torsi & kekencangan

| Baut | Torsi aman |
|---|---|
| M3 ke plastik FDM | 0,2–0,3 N·m (kencangkan dengan ujung jari + seperempat putaran) |
| M3 ke mur/heat-insert | 0,5 N·m |
| M2,5 ke PCB | 0,15 N·m — sampai terasa "berhenti", jangan dikencangkan lagi |

## Perawatan

- **Bersihkan kaca layar & lensa** dengan kain mikrofiber; jangan alkohol
  keras pada akrilik.
- **Ventilasi**: tiup debu dari slot samping tiap beberapa bulan. Slot atas
  dibuat lebar (30 mm) supaya bisa disapu kuas kecil.
- **Sensor IR**: permukaan can TO-39 harus bebas lemak. Bersihkan dengan
  cotton bud + alkohol isopropil, lalu keringkan.
- Kalau ruangan berdebu dan unit dipakai terus-menerus, tambahkan filter
  kasa nyamuk tipis di sisi dalam slot ventilasi (tidak perlu desain baru —
  cukup dijepit dengan cable tie).
