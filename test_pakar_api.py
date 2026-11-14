
import json
import urllib.request
import urllib.error
import getpass
import sys

BASE_URL = "http://127.0.0.1:8000/api"


# FUNGSI REQUEST API

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
            error_body = e.read().decode("utf-8")
            print("Detail:", error_body)
        except Exception:
            pass

        return None

    except urllib.error.URLError as e:
        print("\nKoneksi API gagal:", e.reason)
        return None

    except Exception as e:
        print("\nTerjadi kesalahan:", str(e))
        return None


# 1. LOGIN

print("   MEASLESCARE - SISTEM PAKAR")

print("\nLOGIN")

nik = input("NIK: ").strip()
password = getpass.getpass("Password: ")

login = request_api(
    method="POST",
    endpoint="/auth/login",
    data={
        "NIK": nik,
        "password": password
    }
)

if not login:
    print("\nLogin gagal!")
    sys.exit(1)

token = login.get("access_token")

if not token:
    print("\nAccess token tidak ditemukan!")
    sys.exit(1)

print("\nLogin berhasil!")


# 2. AMBIL MASTER GEJALA

print("\nMASTER GEJALA")

master = request_api(
    method="GET",
    endpoint="/pakar/master-gejala",
    token=token
)

if not master:
    print("Gagal mengambil master gejala.")
    sys.exit(1)

print(json.dumps(
    master,
    indent=4,
    ensure_ascii=False
))


# 3. BUAT PEMERIKSAAN PASIEN

print("\nBUAT PEMERIKSAAN")

pemeriksaan = request_api(
    method="POST",
    endpoint="/gejala",
    data={
        "Batuk": "kering",
        "Suhu": 38.5
    },
    token=token
)

if not pemeriksaan:
    print("Gagal membuat pemeriksaan.")
    sys.exit(1)

id_gejala = pemeriksaan.get("id_gejala")

if not id_gejala:
    print("ID gejala tidak ditemukan dalam response.")
    print(json.dumps(pemeriksaan, indent=4))
    sys.exit(1)

print("Pemeriksaan berhasil dibuat!")
print("ID Gejala:", id_gejala)


# 4. INPUT JAWABAN KUESIONER

print("\nJAWABAN KUESIONER")

jawaban = [
    {
        "kode_gejala": "DEMAM",
        "nilai": 1
    },
    {
        "kode_gejala": "RUAM",
        "nilai": 1
    },
    {
        "kode_gejala": "RUAM_MENYELURUH",
        "nilai": 1
    },
    {
        "kode_gejala": "BATUK",
        "nilai": 1
    },
    {
        "kode_gejala": "PILEK",
        "nilai": 0
    },
    {
        "kode_gejala": "MATA_MERAH",
        "nilai": 0
    },
    {
        "kode_gejala": "SESAK",
        "nilai": 0
    },
    {
        "kode_gejala": "KEJANG",
        "nilai": 0
    },
    {
        "kode_gejala": "PENURUNAN_KESADARAN",
        "nilai": 0
    }
]

for item in jawaban:
    status = "YA" if item["nilai"] == 1 else "TIDAK"

    print(
        f'{item["kode_gejala"]:25} : {status}'
    )


# 5. EVALUASI SISTEM PAKAR

print("\nEVALUASI SISTEM PAKAR")

payload = {
    "id_gejala": id_gejala,
    "jawaban": jawaban
}

hasil = request_api(
    method="POST",
    endpoint="/pakar/evaluasi",
    data=payload,
    token=token
)

if not hasil:
    print("\nEvaluasi sistem pakar gagal.")
    sys.exit(1)

print("\nEvaluasi berhasil!")

print("\nHASIL INFERENSI")

print(json.dumps(
    hasil,
    indent=4,
    ensure_ascii=False
))


# 6. AMBIL HASIL YANG TERSIMPAN

print("\nVERIFIKASI HASIL")

hasil_database = request_api(
    method="GET",
    endpoint=f"/pakar/hasil/{id_gejala}",
    token=token
)

if hasil_database:

    print("\nHasil berhasil diambil dari database!")

    print(json.dumps(
        hasil_database,
        indent=4,
        ensure_ascii=False
    ))

else:
    print("\nGagal mengambil hasil dari database.")


# 7. SELESAI

print("PENGUJIAN SISTEM PAKAR SELESAI")

print("ID Pemeriksaan :", id_gejala)
print("Status Login   : Berhasil")
print("Status Master  : Berhasil")
print("Status Evaluasi:", "Berhasil" if hasil else "Gagal")
print("Status Hasil   :", "Berhasil" if hasil_database else "Gagal")
