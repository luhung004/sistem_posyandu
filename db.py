"""
Lapisan akses basis data (SQLite) untuk Sistem Informasi E-Posyandu.

Semua akses basis data melewati modul ini agar koneksi, transaksi, dan
inisialisasi skema terkelola di satu tempat.
"""
import os
import sqlite3

from flask import g, has_app_context

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "eposyandu.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "schema.sql")

# Koneksi cadangan untuk pemakaian di luar konteks aplikasi Flask
# (mis. skrip seed.py atau laporan yang dijalankan dari terminal).
_standalone = None


def _connect():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_db():
    """
    Koneksi basis data untuk konteks yang sedang berjalan.

    Di dalam permintaan Flask, koneksi disimpan pada objek ``g`` sehingga
    ditutup otomatis di akhir permintaan. Di luar konteks aplikasi (skrip
    terminal), dipakai satu koneksi bersama.
    """
    global _standalone
    if not has_app_context():
        if _standalone is None:
            _standalone = _connect()
        return _standalone

    if "db" not in g:
        g.db = _connect()
    return g.db


def close_db(exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def query(sql, params=(), one=False):
    cur = get_db().execute(sql, params)
    rows = cur.fetchall()
    cur.close()
    if one:
        return rows[0] if rows else None
    return rows


def execute(sql, params=()):
    db = get_db()
    cur = db.execute(sql, params)
    db.commit()
    lastrow = cur.lastrowid
    cur.close()
    return lastrow


def tabel_ada(nama="users"):
    """
    True bila basis data sudah berisi tabel yang diminta.

    Memeriksa isi skema, bukan keberadaan berkas.  SQLite membuat berkas
    kosong begitu connect() dipanggil, jadi os.path.exists() akan selalu
    bernilai benar begitu permintaan pertama menyentuh basis data - padahal
    tabelnya belum ada sama sekali.
    """
    if not os.path.exists(DB_PATH):
        return False
    try:
        conn = _connect()
    except sqlite3.Error:
        return False
    try:
        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (nama,)).fetchone()
        return row is not None
    finally:
        conn.close()


def init_db(seed=False):
    """Buat tabel dari schema.sql. Aman dijalankan berulang."""
    with open(SCHEMA_PATH, "r", encoding="utf-8") as fh:
        script = fh.read()
    conn = _connect()
    try:
        conn.executescript(script)
        conn.commit()
    finally:
        conn.close()
    if seed:
        import seed
        seed.seed_database()
