
import json
import urllib.request
import urllib.error
import getpass
import sys


# ==========================================================
# KONFIGURASI
# ==========================================================

BASE_URL = "http://127.0.0.1:8000/api"

REQUIRED_FACTS = [
    "DEMAM",
    "RUAM",
    "RUAM_MENYELURUH",
    "BATUK",
    "PILEK",
    "MATA_MERAH",
    "SESAK",
    "KEJANG",
    "PENURUNAN_KESADARAN"
]


# ==========================================================
# HTTP REQUEST
# ==========================================================

def request_api(method, endpoint, data=None, token=None):

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    if token:
        headers["Authorization"] = f"Bearer {token}"

    body = None

    if data is not None:
        body = json.dumps(data).encode("utf-8")

    req = urllib.request.Request(
        url=f"{BASE_URL}{endpoint}",
        data=body,
        headers=headers,
        method=method
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:

            response_body = response.read().decode("utf-8")

            if not response_body:
                return {}

            return json.loads(response_body)

    except urllib.error.HTTPError as e:

        print(f"\nHTTP ERROR: {e.code}")

        try:
            print(e.read().decode("utf-8"))
        except Exception:
            pass

        return None

    except urllib.error.URLError as e:

        print("\nKoneksi API gagal:", e.reason)
        return None

    except Exception as e:

        print("\nTerjadi kesalahan:", str(e))
        return None


# ==========================================================
# DATA TEST CASE
# ==========================================================

SCENARIOS = [

    {
        "id": "TC01",
        "nama": "Clinical + Suspected Pattern - Batuk",

        "jawaban": {
            "DEMAM": 1,
            "RUAM": 1,
            "RUAM_MENYELURUH": 1,
            "BATUK": 1,
            "PILEK": 0,
            "MATA_MERAH": 0,
            "SESAK": 0,
            "KEJANG": 0,
            "PENURUNAN_KESADARAN": 0
        },

        "expected_main": "S003",
        "expected_safety": "S014",
        "expected_alert": False
    },

    {
        "id": "TC02",
        "nama": "Clinical + Suspected Pattern - Pilek",

        "jawaban": {
            "DEMAM": 1,
            "RUAM": 1,
            "RUAM_MENYELURUH": 1,
            "BATUK": 0,
            "PILEK": 1,
            "MATA_MERAH": 0,
            "SESAK": 0,
            "KEJANG": 0,
            "PENURUNAN_KESADARAN": 0
        },

        "expected_main": "S004",
        "expected_safety": "S014",
        "expected_alert": False
    },

    {
        "id": "TC03",
        "nama": "Clinical Pattern - Batuk",

        "jawaban": {
            "DEMAM": 1,
            "RUAM": 1,
            "RUAM_MENYELURUH": 0,
            "BATUK": 1,
            "PILEK": 0,
            "MATA_MERAH": 0,
            "SESAK": 0,
            "KEJANG": 0,
            "PENURUNAN_KESADARAN": 0
        },

        "expected_main": "S007",
        "expected_safety": "S014",
        "expected_alert": False
    },

    {
        "id": "TC04",
        "nama": "Clinical Pattern Tidak Terpenuhi",

        "jawaban": {
            "DEMAM": 1,
            "RUAM": 1,
            "RUAM_MENYELURUH": 0,
            "BATUK": 0,
            "PILEK": 0,
            "MATA_MERAH": 0,
            "SESAK": 0,
            "KEJANG": 0,
            "PENURUNAN_KESADARAN": 0
        },

        "expected_main": "S010",
        "expected_safety": "S014",
        "expected_alert": False
    },

    {
        "id": "TC05",
        "nama": "Safety Alert - Sesak Napas",

        "jawaban": {
            "DEMAM": 1,
            "RUAM": 1,
            "RUAM_MENYELURUH": 1,
            "BATUK": 1,
            "PILEK": 0,
            "MATA_MERAH": 0,
            "SESAK": 1,
            "KEJANG": 0,
            "PENURUNAN_KESADARAN": 0
        },

        "expected_main": "S003",
        "expected_safety": "S011",
        "expected_alert": True
    },

    {
        "id": "TC06",
        "nama": "Safety Alert - Kejang",

        "jawaban": {
            "DEMAM": 1,
            "RUAM": 1,
            "RUAM_MENYELURUH": 1,
            "BATUK": 1,
            "PILEK": 0,
            "MATA_MERAH": 0,
            "SESAK": 0,
            "KEJANG": 1,
            "PENURUNAN_KESADARAN": 0
        },

        "expected_main": "S003",
        "expected_safety": "S012",
        "expected_alert": True
    },

    {
        "id": "TC07",
        "nama": "Safety Alert - Penurunan Kesadaran",

        "jawaban": {
            "DEMAM": 1,
            "RUAM": 1,
            "RUAM_MENYELURUH": 1,
            "BATUK": 1,
            "PILEK": 0,
            "MATA_MERAH": 0,
            "SESAK": 0,
            "KEJANG": 0,
            "PENURUNAN_KESADARAN": 1
        },

        "expected_main": "S003",
        "expected_safety": "S013",
        "expected_alert": True
    }
]


# ==========================================================
# LOGIN
# ==========================================================

def login():

    print("\n==========================================")
    print("       MEASLESCARE - SCENARIO TEST")
    print("==========================================")

    print("\n========== LOGIN ==========")

    nik = input("NIK: ").strip()
    password = getpass.getpass("Password: ")

    result = request_api(
        "POST",
        "/auth/login",
        {
            "NIK": nik,
            "password": password
        }
    )

    if not result:
        print("Login gagal!")
        sys.exit(1)

    token = result.get("access_token")

    if not token:
        print("Access token tidak ditemukan!")
        sys.exit(1)

    print("Login berhasil!")

    return token


# ==========================================================
# VALIDASI MASTER GEJALA
# ==========================================================

def validate_master(token):

    print("\n========== VALIDASI MASTER GEJALA ==========")

    result = request_api(
        "GET",
        "/pakar/master-gejala",
        token=token
    )

    if not result:
        print("Gagal mengambil master gejala.")
        sys.exit(1)

    available_codes = {
        item["kode_gejala"]
        for item in result.get("data", [])
    }

    missing = set(REQUIRED_FACTS) - available_codes

    if missing:
        print("Kode gejala tidak tersedia:", sorted(missing))
        sys.exit(1)

    print("Total master gejala:", result.get("total"))
    print("Semua 9 fakta wajib tersedia.")
    print("Validasi master berhasil!")


# ==========================================================
# BUAT PEMERIKSAAN PASIEN
# ==========================================================

def create_examination(token):

    result = request_api(
        "POST",
        "/gejala",
        {
            "Batuk": "kering",
            "Suhu": 38.5
        },
        token=token
    )

    if not result:
        return None

    return result.get("id_gejala")


# ==========================================================
# MENJALANKAN SATU TEST CASE
# ==========================================================

def run_scenario(scenario, token):

    print("\n")
    print("=" * 65)
    print(f"{scenario['id']} - {scenario['nama']}")
    print("=" * 65)

    # ------------------------------------------
    # 1. BUAT PEMERIKSAAN
    # ------------------------------------------

    id_gejala = create_examination(token)

    if not id_gejala:
        print("[FAIL] Gagal membuat pemeriksaan.")
        return {
            "id": scenario["id"],
            "status": "FAIL",
            "reason": "Pemeriksaan gagal dibuat"
        }

    print("ID Pemeriksaan:", id_gejala)

    # ------------------------------------------
    # 2. SIAPKAN JAWABAN
    # ------------------------------------------

    jawaban = [
        {
            "kode_gejala": kode,
            "nilai": nilai
        }
        for kode, nilai in scenario["jawaban"].items()
    ]

    for item in jawaban:

        status = "YA" if item["nilai"] == 1 else "TIDAK"

        print(
            f"{item['kode_gejala']:25} : {status}"
        )

    # ------------------------------------------
    # 3. EVALUASI
    # ------------------------------------------

    print("\nMenjalankan inferensi...")

    result = request_api(
        "POST",
        "/pakar/evaluasi",
        {
            "id_gejala": id_gejala,
            "jawaban": jawaban
        },
        token=token
    )

    if not result:

        print("[FAIL] Evaluasi gagal.")

        return {
            "id": scenario["id"],
            "status": "FAIL",
            "reason": "Evaluasi gagal"
        }

    data = result.get("data", {})

    decision = data.get("decision_tree", {})
    forward = data.get("forward_chaining", {})

    # ------------------------------------------
    # 4. AMBIL HASIL AKTUAL
    # ------------------------------------------

    actual_main = decision.get("main_leaf")
    actual_safety = decision.get("safety_leaf")
    actual_alert = data.get("safety_alert")

    actual_category = forward.get("kategori")

    print("\n========== HASIL AKTUAL ==========")

    print("Main Leaf      :", actual_main)
    print("Safety Leaf    :", actual_safety)
    print("Safety Alert   :", actual_alert)
    print("FC Category    :", actual_category)

    print(
        "Aturan Aktif   :",
        ", ".join(forward.get("aturan_aktif", []))
    )

    # ------------------------------------------
    # 5. BANDINGKAN EXPECTED VS ACTUAL
    # ------------------------------------------

    checks = {

        "Main Leaf": (
            actual_main == scenario["expected_main"]
        ),

        "Safety Leaf": (
            actual_safety == scenario["expected_safety"]
        ),

        "Safety Alert": (
            actual_alert == scenario["expected_alert"]
        )
    }

    print("\n========== VALIDASI ==========")

    for name, passed in checks.items():

        status = "PASS" if passed else "FAIL"

        print(f"{name:20}: {status}")

    # ------------------------------------------
    # 6. VERIFIKASI DATABASE
    # ------------------------------------------

    print("\nMemeriksa hasil database...")

    saved = request_api(
        "GET",
        f"/pakar/hasil/{id_gejala}",
        token=token
    )

    database_ok = False

    if saved:

        saved_data = saved.get("data", {})

        database_ok = (
            saved_data.get("id_gejala") == id_gejala
            and saved_data.get("hasil") is not None
        )

    print(
        "Database          :",
        "PASS" if database_ok else "FAIL"
    )

    # ------------------------------------------
    # 7. STATUS TEST CASE
    # ------------------------------------------

    passed = all(checks.values()) and database_ok

    print("\n------------------------------------------")
    print(
        f"RESULT {scenario['id']}:",
        "PASS" if passed else "FAIL"
    )
    print("------------------------------------------")

    return {
        "id": scenario["id"],
        "nama": scenario["nama"],
        "id_gejala": id_gejala,
        "expected_main": scenario["expected_main"],
        "actual_main": actual_main,
        "expected_safety": scenario["expected_safety"],
        "actual_safety": actual_safety,
        "expected_alert": scenario["expected_alert"],
        "actual_alert": actual_alert,
        "database": database_ok,
        "status": "PASS" if passed else "FAIL"
    }


# ==========================================================
# MAIN PROGRAM
# ==========================================================

def main():

    token = login()

    validate_master(token)

    print("\n==========================================")
    print("          MULAI SCENARIO TEST")
    print("==========================================")

    results = []

    for scenario in SCENARIOS:

        result = run_scenario(
            scenario,
            token
        )

        results.append(result)

    # ------------------------------------------
    # SUMMARY
    # ------------------------------------------

    print("\n\n")
    print("=" * 70)
    print("             FINAL TEST SUMMARY")
    print("=" * 70)

    print(
        f"{'TEST':<10}"
        f"{'EXPECTED':<15}"
        f"{'ACTUAL':<15}"
        f"{'SAFETY':<12}"
        f"{'STATUS':<10}"
    )

    print("-" * 70)

    for item in results:

        if "actual_main" not in item:
            print(
                f"{item['id']:<10}"
                f"{'-':<15}"
                f"{'-':<15}"
                f"{'-':<12}"
                f"{item['status']:<10}"
            )
            continue

        expected = item["expected_main"]
        actual = item["actual_main"]
        safety = item["actual_safety"]

        print(
            f"{item['id']:<10}"
            f"{expected:<15}"
            f"{str(actual):<15}"
            f"{str(safety):<12}"
            f"{item['status']:<10}"
        )

    print("-" * 70)

    total = len(results)

    passed = sum(
        1 for item in results
        if item["status"] == "PASS"
    )

    failed = total - passed

    print("\nTOTAL TEST CASE :", total)
    print("PASS            :", passed)
    print("FAIL            :", failed)

    accuracy = (passed / total) * 100

    print(f"PASS RATE       : {accuracy:.2f}%")

    print("\n==========================================")

    if failed == 0:
        print("ALL SCENARIO TESTS PASSED!")
    else:
        print("SOME SCENARIO TESTS FAILED.")

    print("==========================================")

    # Simpan laporan JSON
    with open(
        "scenario_test_results.json",
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            {
                "total": total,
                "passed": passed,
                "failed": failed,
                "pass_rate": accuracy,
                "results": results
            },
            file,
            indent=4,
            ensure_ascii=False
        )

    print("\nLaporan tersimpan:")
    print("scenario_test_results.json")


if __name__ == "__main__":
    main()
