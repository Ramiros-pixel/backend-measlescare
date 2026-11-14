// =====================================================================
//  MeaslesWatch AI - BODI / TRAY (buka di sisi muka)
//  Skrip CAD parametrik (OpenSCAD / Tinkercad Codeblocks mode Code).
//
//  Satuan : mm.  Origin: sudut kiri-bawah, Y ke atas, Z ke belakang
//  Plat muka dipasang di z = 0 (menutup rongga).
// =====================================================================

include <01_front_bezel.scad>;   // ambil FRONT_W, FRONT_H, CAM_CX, dst.
                                 // (bagian render 3D di file itu boleh diabaikan)

BODY_W = FRONT_W;               // 220
BODY_H = FRONT_H;               // 300
BODY_D = 54.0;                  // kedalaman dinding samping
WALL_T = 4.0;
CORNER_R = 8.0;

// ------------------------------------------------------- Orange Pi 4 Pro 89 x 56
PI_BOARD_W = 89.0;
PI_BOARD_H = 56.0;
PI_HOLE_INSET = 3.5;
PI_SPACING_X = PI_BOARD_W - 2*PI_HOLE_INSET;   // 82
PI_SPACING_Y = PI_BOARD_H - 2*PI_HOLE_INSET;   // 49
PI_BOSS_H = 8.0;
PI_BOSS_OD = 9.0;
PI_CX = 110.0;
PI_CY = 60.0;
PI_SLOT = 4.0;                  // slot 4 mm -> toleran terhadap jarak sebenarnya

// ------------------------------------------------------- belakang
GLAND_XY = [110.0, 60.0];
GLAND_D  = 20.0;
SWITCH_XY = [110.0, 200.0];
SWITCH_D  = 13.0;

// ------------------------------------------------------- ventilasi samping
VENT_X_FROM_EDGE = 27.0;
VENT_Y_START = 60.0;
VENT_Y_PITCH = 14.0;
VENT_COUNT   = 6;
VENT_W = 4.0;
VENT_H = 30.0;

// ------------------------------------------------------- cable tie
TIETIE_XY = [[60, 20], [160, 20], [60, 280], [160, 280]];
TIETIE_W  = 4.0;
TIETIE_H  = 8.0;

M3_CLEAR = 3.4;
$fn = 96;

module rrect(w, h, r) {
  translate([r, r]) offset(r = r) square([w - 2*r, h - 2*r]);
}

module tray_2d() {
  difference() {
    rrect(BODY_W, BODY_H, CORNER_R);                       // luar
    translate([WALL_T, WALL_T]) rrect(BODY_W - 2*WALL_T, BODY_H - 2*WALL_T, CORNER_R);
  }
}

module body_tray() {
  difference() {
    union() {
      // dinding (cincin)
      linear_extrude(height = BODY_D) tray_2d();
      // plat belakang
      translate([0, 0, BODY_D - WALL_T]) linear_extrude(height = WALL_T) rrect(BODY_W, BODY_H, CORNER_R);
      // boss Orange Pi
      translate([PI_CX - PI_SPACING_X/2, PI_CY - PI_SPACING_Y/2, BODY_D - WALL_T - PI_BOSS_H])
        cylinder(d = PI_BOSS_OD, h = PI_BOSS_H + 0.1);
      translate([PI_CX + PI_SPACING_X/2, PI_CY - PI_SPACING_Y/2, BODY_D - WALL_T - PI_BOSS_H])
        cylinder(d = PI_BOSS_OD, h = PI_BOSS_H + 0.1);
      translate([PI_CX - PI_SPACING_X/2, PI_CY + PI_SPACING_Y/2, BODY_D - WALL_T - PI_BOSS_H])
        cylinder(d = PI_BOSS_OD, h = PI_BOSS_H + 0.1);
      translate([PI_CX + PI_SPACING_X/2, PI_CY + PI_SPACING_Y/2, BODY_D - WALL_T - PI_BOSS_H])
        cylinder(d = PI_BOSS_OD, h = PI_BOSS_H + 0.1);
    }

    // ---- rongga dalam
    translate([WALL_T, WALL_T, -1])
      linear_extrude(height = BODY_D - WALL_T + 1)
        rrect(BODY_W - 2*WALL_T, BODY_H - 2*WALL_T, CORNER_R);

    // ---- lubang dinding belakang
    translate([GLAND_XY[0], GLAND_XY[1], BODY_D - WALL_T - 1])
      cylinder(d = GLAND_D, h = WALL_T + 2);
    translate([SWITCH_XY[0], SWITCH_XY[1], BODY_D - WALL_T - 1])
      cylinder(d = SWITCH_D, h = WALL_T + 2);
    for (r = [0 : 1], c = [0 : 6])
      translate([50 + c*20, 262 + r*22, BODY_D - WALL_T - 1]) hull() {
        translate([0, -8, 0]) cylinder(d = 4, h = WALL_T + 2);
        translate([0,  8, 0]) cylinder(d = 4, h = WALL_T + 2);
      }
    for (p = [[30,30], [190,30], [30,130], [190,130]])
      translate([p[0], p[1], BODY_D - WALL_T - 1]) hull() {
        translate([-2, 0, 0]) cylinder(d = 4, h = WALL_T + 2);
        translate([ 2, 0, 0]) cylinder(d = 4, h = WALL_T + 2);
      }
    for (s = SCREWS)
      translate([s[0], s[1], BODY_D - WALL_T - 1]) cylinder(d = M3_CLEAR, h = WALL_T + 2);

    // ---- ventilasi dinding samping kiri & kanan
    for (i = [0 : VENT_COUNT - 1], x = [WALL_T + VENT_X_FROM_EDGE,
                                        BODY_W - WALL_T - VENT_X_FROM_EDGE])
      translate([x, VENT_Y_START + i*VENT_Y_PITCH, -1]) hull() {
        translate([0, -(VENT_H/2 - VENT_W/2), 0]) cylinder(d = VENT_W, h = BODY_D + 2);
        translate([0,  (VENT_H/2 - VENT_W/2), 0]) cylinder(d = VENT_W, h = BODY_D + 2);
      }

    // ---- slot cable tie di plat belakang
    for (p = TIETIE_XY)
      translate([p[0], p[1], BODY_D - WALL_T - 1]) hull() {
        translate([-(TIETIE_H/2 - TIETIE_W/2), 0, 0]) cylinder(d = TIETIE_W, h = WALL_T + 2);
        translate([ (TIETIE_H/2 - TIETIE_W/2), 0, 0]) cylinder(d = TIETIE_W, h = WALL_T + 2);
      }

    // ---- lubang baut boss Orange Pi (slot vertikal, M3)
    for (bp = [[PI_CX - PI_SPACING_X/2, PI_CY - PI_SPACING_Y/2],
               [PI_CX + PI_SPACING_X/2, PI_CY - PI_SPACING_Y/2],
               [PI_CX - PI_SPACING_X/2, PI_CY + PI_SPACING_Y/2],
               [PI_CX + PI_SPACING_X/2, PI_CY + PI_SPACING_Y/2]])
      translate([bp[0], bp[1], BODY_D - WALL_T - PI_BOSS_H - 1]) hull() {
        translate([0, -(M3_CLEAR/2 + PI_SLOT/2 - M3_CLEAR/2), 0])
          cylinder(d = M3_CLEAR, h = PI_BOSS_H + 2);
        translate([0,  (M3_CLEAR/2 + PI_SLOT/2 - M3_CLEAR/2), 0])
          cylinder(d = M3_CLEAR, h = PI_BOSS_H + 2);
      }
  }
}

body_tray();
