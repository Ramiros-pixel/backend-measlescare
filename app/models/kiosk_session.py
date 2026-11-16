"""Kompatibilitas import model kiosk.

Model KioskDevice dan KioskSession didefinisikan satu kali di gejala.py
agar SQLAlchemy tidak mendaftarkan dua class untuk tabel yang sama.
"""
from app.models.gejala import KioskDevice, KioskSession

__all__ = ["KioskDevice", "KioskSession"]
