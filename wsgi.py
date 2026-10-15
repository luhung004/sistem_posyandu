# -*- coding: utf-8 -*-
"""
Titik masuk WSGI untuk server produksi.

Dipakai oleh gunicorn (Linux/PaaS) dan waitress (Windows):

    gunicorn --bind 0.0.0.0:$PORT wsgi:application
    waitress-serve --port=$PORT wsgi:application

Blok inisialisasi di bawah sengaja ada di sini, bukan di app.py.  Inisialisasi
dulu hanya berjalan di "__main__", yang tidak pernah dieksekusi saat modul
diimpor oleh server WSGI - akibatnya basis data tidak pernah dibuat dan
setiap halaman menampilkan galat.
"""
import os

import db
from app import app as application  # noqa: E402,F401  - "application" adalah nama gunicarn

if not db.tabel_ada():
    # Berjalan sekali per worker saat start.  Aman diulang: schema.sql memakai
    # CREATE TABLE IF NOT EXISTS, dan seed.py memeriksa jumlah baris sebelum
    # mengisi, jadi worker yang mulai bersamaan tidak menghasilkan data ganda.
    db.init_db(seed=os.environ.get("EPOSYANDU_SEED") == "1")