#!/bin/bash
# Smoke test API di dalam container huawei-backend
set -e
B=http://localhost:8000
TOKEN=*** -s -X POST $B/api/auth/login -H 'Content-Type: application/json' \
  --data-binary '{"NIK":"admin","password":"***"}' | python -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
echo "== /api/auth/me =="
curl -s $B/api/auth/me -H "Authorization: Bearer $TOKEN"
echo
echo "== /api/users (admin: lihat semua) =="
curl -s "$B/api/users/" -H "Authorization: Bearer $TOKEN" | head -c 300
echo
echo "== register user R2 =="
curl -s -X POST $B/api/auth/register -H 'Content-Type: application/json' \
  --data-binary '{"NIK":"3201000000000001","Name":"Tes User","Tgl_lahir":"2000-01-01","Alamat":"Bandung","password":"***","id_Role":"R2"}' | head -c 200
echo
echo "== user R2 login + buat gejala =="
UT=$(curl -s -X POST $B/api/auth/login -H 'Content-Type: application/json' \
  --data-binary '{"NIK":"3201000000000001","password":"***"}' | python -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
curl -s -X POST $B/api/gejala -H 'Content-Type: application/json' -H "Authorization: Bearer $UT" \
  --data-binary '{"id_gejala":"G-TEST-1","Batuk":"ringan","Suhu":37.2}' | head -c 200
echo
echo "== admin lihat semua gejala =="
curl -s "$B/api/gejala/" -H "Authorization: Bearer $TOKEN" | head -c 300
echo
