// =====================================================================
//  MeaslesWatch AI - PLAT MUKA (front bezel)
//  Skrip CAD parametrik - bisa dibuka di OpenSCAD ATAU ditempel ke
//  Tinkercad Codeblocks (mode "Code" -> JavaScript, lihat documentation.md).
//
//  Satuan : mm
//  Origin : sudut kiri-bawah plat muka, Y ke atas, Z ke belakang
//
//  Angka di sini IDENTIK dengan cad/params.py. Kalau mengubah salah satu,
//  ubah keduanya (atau jalankan: python3 cad/gen2d.py untuk cek konsistensi).
// =====================================================================

// ------------------------------------------------------- bahan & ketebalan
PANEL_T = 6.0;      // tebal plat (akrilik/plywood/3D print)

// ------------------------------------------------------- plat muka
FRONT_W = 220.0;
FRONT_H = 300.0;
CORNER_R = 8.0;

// ------------------------------------------------------- layar 7" IPS 1024x600
LCD_ACTIVE_W = 154.2144;    // active area [datasheet]
LCD_ACTIVE_H = 85.92;
LCD_OVERLAP  = 2.0;         // tumpuan plat menutupi tepi kaca
SCREEN_CUT_W = LCD_ACTIVE_W + 2*LCD_OVERLAP;   // 158.2144
SCREEN_CUT_H = LCD_ACTIVE_H + 2*LCD_OVERLAP;   //  89.92
SCREEN_CX = 110.0;
SCREEN_CY = 118.0;

// ------------------------------------------------------- kamera IMX415 (PCB 38x38, lens M12)
CAM_CX = 110.0;
CAM_CY = 246.0;
CAM_HOLE_D    = 24.0;   // wajib >=24 utk FOV 90 deg tanpa vignetting
CAM_CHAMFER_D = 30.0;   // chamfer 45 deg di sisi dalam

// ------------------------------------------------------- sensor IR MLX90614 (can TO-39 OD 9.1)
IR_CX = 110.0;
IR_CY = 205.0;
IR_HOLE_D = 16.0;       // wajib >=16 (14 mm -> vignetting 31.5 deg < 45 deg)

// ------------------------------------------------------- mikrofon (pada modul kamera)
MIC_X = [96.0, 110.0, 124.0];
MIC_Y = 222.0;
MIC_D = 2.5;

// ------------------------------------------------------- tombol & LED
LED_PWR = [85.0, 34.0];
LED_ACT = [105.0, 34.0];
LED_D   = 5.0;
BTN     = [160.0, 34.0];
BTN_D   = 12.0;

// ------------------------------------------------------- baut plat muka
M3_CLEAR = 3.4;
INSET    = 8.0;
SCREWS = [
  [INSET,            INSET],
  [FRONT_W - INSET,  INSET],
  [INSET,            FRONT_H - INSET],
  [FRONT_W - INSET,  FRONT_H - INSET],
  [INSET,            FRONT_H/2],
  [FRONT_W - INSET,  FRONT_H/2]
];

// post sambungan layar (di sudut cutout)
POST_OFF = 6.0;

$fn = 96;

// ------------------------------------------------------- modul
module rrect(w, h, r) {
  translate([r, r]) offset(r = r) square([w - 2*r, h - 2*r]);
}

module hole_cyl(cx, cy, d) {
  translate([cx, cy, -1]) cylinder(d = d, h = PANEL_T + 2);
}

module front_bezel_2d() {
  difference() {
    rrect(FRONT_W, FRONT_H, CORNER_R);

    // layar
    translate([SCREEN_CX - SCREEN_CUT_W/2, SCREEN_CY - SCREEN_CUT_H/2])
      rrect(SCREEN_CUT_W, SCREEN_CUT_H, 2.0);

    // kamera, sensor IR, tombol, LED, mikrofon, baut
    translate([CAM_CX, CAM_CY]) circle(d = CAM_HOLE_D);
    translate([IR_CX,  IR_CY])  circle(d = IR_HOLE_D);
    translate([BTN[0], BTN[1]])       circle(d = BTN_D);
    translate([LED_PWR[0], LED_PWR[1]]) circle(d = LED_D);
    translate([LED_ACT[0], LED_ACT[1]]) circle(d = LED_D);
    for (x = MIC_X) translate([x, MIC_Y]) circle(d = MIC_D);
    for (s = SCREWS) translate(s) circle(d = M3_CLEAR);

    // 4 lubang post layar
    for (p = [[SCREEN_CX - SCREEN_CUT_W/2 - POST_OFF, SCREEN_CY - SCREEN_CUT_H/2 - POST_OFF],
              [SCREEN_CX + SCREEN_CUT_W/2 + POST_OFF, SCREEN_CY - SCREEN_CUT_H/2 - POST_OFF],
              [SCREEN_CX - SCREEN_CUT_W/2 - POST_OFF, SCREEN_CY + SCREEN_CUT_H/2 + POST_OFF],
              [SCREEN_CX + SCREEN_CUT_W/2 + POST_OFF, SCREEN_CY + SCREEN_CUT_H/2 + POST_OFF]])
      translate(p) circle(d = M3_CLEAR);
  }
}

// ------------------------------------------------------- render 3D
module front_bezel_3d() {
  difference() {
    linear_extrude(height = PANEL_T) front_bezel_2d();
    // chamfer 45 deg untuk kamera, dibuka dari sisi belakang
    translate([CAM_CX, CAM_CY, -1])
      cylinder(d1 = CAM_CHAMFER_D, d2 = CAM_HOLE_D, h = PANEL_T + 1);
  }
}

front_bezel_3d();

// ------------------------------------------------------- lembar 2D (ganti komentar)
// front_bezel_2d();
