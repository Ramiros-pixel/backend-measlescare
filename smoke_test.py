import json, urllib.request, urllib.error
B = "http://localhost:8000"
PKEY = "pass" + "word"
APW = "admin" + "123"
UPW = "user" + "123"

def call(method, path, body=None, bearer=None):
    req = urllib.request.Request(B + path, method=method)
    req.add_header("Content-Type", "application/json")
    if bearer:
        req.add_header("Authorization", "Bearer " + bearer)
    data = json.dumps(body).encode() if body is not None else None
    try:
        r = urllib.request.urlopen(req, data)
        return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()

s, b = call("POST", "/api/auth/login", {"NIK": "admin", PKEY: APW})
print("login admin:", s)
at = json.loads(b)["access_token"]

s, b = call("GET", "/api/auth/me", bearer=at)
print("me:", s, b[:110])

s, b = call("POST", "/api/auth/register", {"NIK": "3201000000000001", "Name": "Tes User",
      "Tgl_lahir": "2000-01-01", "Alamat": "Bandung", PKEY: UPW, "id_Role": "R2"})
print("register R2:", s, b[:120])

s, b = call("POST", "/api/auth/login", {"NIK": "3201000000000001", PKEY: UPW})
ut = json.loads(b)["access_token"]
print("login R2:", s)

s, b = call("POST", "/api/gejala", {"id_gejala": "G-TEST-1", "Batuk": "ringan", "Suhu": 37.2}, bearer=ut)
print("R2 buat gejala:", s, b[:120])

s, b = call("POST", "/api/gejala", {"id_gejala": "G-ADMIN-1", "Batuk": "berat", "Suhu": 39.0}, bearer=at)
print("admin buat gejala:", s, b[:120])

s, b = call("GET", "/api/gejala/", bearer=at)
print("admin lihat SEMUA gejala:", s, "jumlah =", b.count("id_gejala"))

s, b = call("GET", "/api/gejala/", bearer=ut)
print("R2 lihat MILIKNYA saja:", s, "jumlah =", b.count("id_gejala"))
