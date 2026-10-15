"""
Sistem Informasi E-Posyandu Terintegrasi
Pemantauan dan Prediksi Dini Stunting
Posyandu Lestari 12, Merden, Rawawungu, Kecamatan Purwanegara, Kabupaten Banjarnegara

Aplikasi web berbasis Flask.  Jalankan dengan:  python app.py
"""
import csv
import io
import os
from datetime import date, datetime, timedelta
from functools import wraps

from flask import (Flask, Response, flash, g, jsonify, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

import db
import growth

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("EPOSYANDU_SECRET", "eposyandu-lestari-12-banjarnegara"),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    JSON_AS_ASCII=False,
)

app.teardown_appcontext(db.close_db)

IDENTITAS = {
    "nama": "Posyandu Lestari 12",
    "wilayah": "Rawawungu, Merden",
    "kecamatan": "Kecamatan Purwanegara",
    "kabupaten": "Kabupaten Banjarnegara",
    "provinsi": "Jawa Tengah",
    "puskesmas": "Puskesmas Purwanegara",
}


# ===========================================================================
# Autentikasi dan hak akses
# ===========================================================================
def current_user():
    if "user_id" not in session:
        return None
    if getattr(g, "_user", None) is None:
        g._user = db.query(
            "SELECT * FROM users WHERE id = ? AND aktif = 1",
            (session["user_id"],), one=True)
    return g._user


def login_required(view):
    @wraps(view)
    def wrapper(*a, **kw):
        if current_user() is None:
            session.clear()
            return redirect(url_for("login", next=request.path))
        return view(*a, **kw)
    return wrapper


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapper(*a, **kw):
            user = current_user()
            if user is None:
                return redirect(url_for("login"))
            if user["role"] not in roles:
                flash("Anda tidak memiliki hak akses untuk halaman tersebut.", "error")
                return redirect(url_for("dashboard"))
            return view(*a, **kw)
        return wrapper
    return decorator


@app.context_processor
def inject_globals():
    return {
        "user": current_user(),
        "identitas": IDENTITAS,
        "hari_ini": date.today(),
        "app_name": "E-Posyandu Lestari 12",
        "umur_terakhir_balita": lambda b: growth.age_text(
            (date.today() - growth.parse_date(b["birth_date"])).days
            if b["birth_date"] else None),
        "status_lencana": _status_lencana,
        "growth_label": _growth_label,
        "ukur_terakhir": ukur_terakhir,
    }


def _growth_label(indicator, z):
    """Label status gizi untuk sebuah Z-Score pada indikator tertentu."""
    return growth.classify(indicator, z)["label"]


def _status_lencana(z, turun=None):
    """Kelas lencana berdasarkan Z-Score TB/U."""
    if z is None:
        return "netral"
    if z < -3:
        return "bahaya"
    if z < -2:
        return "bahaya"
    if z < -1.5:
        return "waspada"
    return "normal"


# ===========================================================================
# Filter tampilan
# ===========================================================================
@app.template_filter("tgl_id")
def tgl_id(value, panjang="panjang"):
    """Format tanggal Indonesia: 9 Oktober 2026 / 09-10-2026."""
    d = growth.parse_date(value)
    if d is None:
        return "-"
    BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
             "Agustus", "September", "Oktober", "November", "Desember"]
    if panjang == "pendek":
        return f"{d.day:02d}-{d.month:02d}-{d.year}"
    return f"{d.day} {BULAN[d.month - 1]} {d.year}"


@app.template_filter("zscore")
def zscore_fmt(value):
    if value is None:
        return "-"
    return f"{value:+.2f} SD"


@app.template_filter("umur")
def umur_fmt(days):
    return growth.age_text(days)


@app.template_filter("angka")
def angka_fmt(value, desimal=1):
    if value is None or value == "":
        return "-"
    try:
        return f"{float(value):.{desimal}f}".replace(".", ",")
    except (TypeError, ValueError):
        return value


# ===========================================================================
# Sumber data bersama
# ===========================================================================
def ambil_balita(balita_id):
    return db.query("SELECT * FROM balita WHERE id = ?", (balita_id,), one=True)


def riwayat_ukur(balita_id, batas=None):
    sql = ("SELECT * FROM pengukuran WHERE balita_id = ? ORDER BY tanggal DESC")
    rows = db.query(sql, (balita_id,))
    return rows[:batas] if batas else rows


def ukur_terakhir(balita_id):
    return db.query(
        "SELECT * FROM pengukuran WHERE balita_id = ? ORDER BY tanggal DESC LIMIT 1",
        (balita_id,), one=True)


def nilai_terakhir(balita):
    """Dict berisi ukuran terakhir seorang balita (untuk tabel ringkas)."""
    u = ukur_terakhir(balita["id"])
    return {"ukur": u, "umur_hari": u["umur_hari"] if u else None}


def riwayat_tren(balita_id):
    """Riwayat Z-Score TB/U terurut lama -> baru, untuk analisis tren."""
    return [{"measured_date": r["tanggal"], "z": r["z_lhfa"]}
            for r in reversed(db.query(
                "SELECT tanggal, z_lhfa FROM pengukuran WHERE balita_id = ? "
                "ORDER BY tanggal", (balita_id,)))]


def peringatan_dari_data(z_lhfa, z_wfa, z_wfh, hist):
    """
    Susun daftar peringatan dini langsung dari Z-Score yang tersimpan,
    tanpa menghitung ulang, agar halaman daftar tetap ringan.

    Aturan (sesuai ambang batas WHO / Kemenkes RI):
      TB/U < -2 SD            -> terdeteksi stunting
      -2 SD <= TB/U < -1,5 SD -> berisiko stunting
      tren Z TB/U turun       -> waspada penurunan
      BB/U atau BB/TB < -2 SD -> gizi kurang (faktor risiko)
    """
    flags = []

    if z_lhfa is not None:
        if z_lhfa < -2:
            flags.append({
                "kode": "stunting", "level": "bahaya",
                "label": "Terdeteksi stunting",
                "pesan": f"TB/U {z_lhfa:+.2f} SD (di bawah −2 SD). Rujuk ke puskesmas "
                         "untuk pemeriksaan dan intervensi gizi.",
            })
        elif z_lhfa < -1.5:
            flags.append({
                "kode": "risiko_stunting", "level": "waspada",
                "label": "Berisiko stunting",
                "pesan": f"TB/U {z_lhfa:+.2f} SD (mendekati −2 SD). Beri PMT, pantau "
                         "tiap bulan, dan edukasi gizi ibu.",
            })
        else:
            flags.append({
                "kode": "normal", "level": "normal",
                "label": "Pertumbuhan tinggi badan normal",
                "pesan": f"TB/U {z_lhfa:+.2f} SD. Pertahankan pemberian ASI/MP-ASI "
                         "bergizi dan pemantauan rutin.",
            })

    tren = growth.trend_from_history(hist, "lhfa")
    if tren["arah"] == "menurun":
        flags.append({
            "kode": "tren_menurun", "level": "bahaya",
            "label": "Tren tinggi badan menurun",
            "pesan": f"Z-Score TB/U turun {abs(tren['delta_total']):.2f} SD dalam "
                     f"{tren['rentang_hari']} hari. Waspadai risiko stunting.",
        })
    elif tren["arah"] == "menurun_ringan":
        flags.append({
            "kode": "tren_menurun_ringan", "level": "waspada",
            "label": "Tren tinggi badan cenderung menurun",
            "pesan": f"Z-Score TB/U turun {abs(tren['delta_total']):.2f} SD. "
                     "Perlu pemantauan lebih ketat.",
        })

    for z, kode, label, pesan in (
        (z_wfa, "wfa_kurang", "Berat badan menurut umur kurang",
         "BB/U {z} SD. Berat badan di bawah standar untuk umurnya."),
        (z_wfh, "wfh_kurang", "Berat badan menurut tinggi badan kurang",
         "BB/TB {z} SD. Proporsi berat terhadap tinggi badan di bawah standar."),
    ):
        if z is not None and z < -2:
            flags.append({
                "kode": kode, "level": "bahaya" if z < -3 else "waspada",
                "label": label, "pesan": pesan.replace("{z}", f"{z:+.2f}"),
            })

    return flags, tren


def ringkas_balita(balita):
    """
    Ringkasan status terkini + peringatan dini untuk satu balita.
    Dipakai pada halaman daftar, dasbor, dan prediksi.
    """
    u = ukur_terakhir(balita["id"])
    umur_hari = (date.today() - growth.parse_date(balita["birth_date"])).days
    info = {
        "balita": balita,
        "ukur": u,
        "umur_hari": umur_hari,
        "umur_teks": growth.age_text(umur_hari),
        "umur_bulan": max(umur_hari, 0) // 30,
        "z_lhfa": u["z_lhfa"] if u else None,
        "z_wfa": u["z_wfa"] if u else None,
        "z_wfh": u["z_wfh"] if u else None,
    }
    if u and u["z_lhfa"] is not None:
        st = growth.classify("lhfa", u["z_lhfa"])
        info["stunting"] = {"z": u["z_lhfa"], **st,
                            "stunted": st["code"] in ("pendek", "sangat_pendek")}
    else:
        info["stunting"] = {"z": None, "code": "tidak_diketahui",
                            "label": "Belum ada data", "level": "netral",
                            "stunted": None}

    # tren dari riwayat TB/U
    hist = riwayat_tren(balita["id"])
    info["tren"] = growth.trend_from_history(hist, "lhfa")
    info["_hist"] = hist
    return info


# ===========================================================================
# Masuk / keluar
# ===========================================================================
@app.route("/")
def index():
    if current_user():
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user():
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        user = db.query("SELECT * FROM users WHERE username = ?", (username,), one=True)

        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Nama pengguna atau kata sandi salah.", "error")
        elif not user["aktif"]:
            flash("Akun ini sedang tidak aktif. Hubungi administrator.", "error")
        else:
            session.clear()
            session["user_id"] = user["id"]
            session["nama"] = user["nama"]
            session["role"] = user["role"]
            tujuan = request.args.get("next")
            if tujuan and tujuan.startswith("/"):
                session["setelah_splash"] = tujuan
            return redirect(url_for("splash"))

    return render_template("login.html")


@app.route("/splash")
@login_required
def splash():
    """Layar pembuka setelah berhasil masuk."""
    tujuan = session.pop("setelah_splash", None) or url_for("dashboard")
    return render_template("splash.html", tujuan=tujuan)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ===========================================================================
# Dasbor
# ===========================================================================
@app.route("/dashboard")
@login_required
def dashboard():
    total = db.query("SELECT COUNT(*) n FROM balita WHERE aktif = 1", one=True)["n"]

    per_status = {}
    for r in db.query("SELECT status_stunting, COUNT(*) n FROM pengukuran "
                      "GROUP BY status_stunting"):
        per_status[r["status_stunting"]] = r["n"]

    # status terkini tiap balita
    terkini = db.query(
        """SELECT b.id, b.nama, b.sex, b.birth_date, p.z_lhfa, p.z_wfa, p.tanggal
           FROM balita b
           LEFT JOIN pengukuran p ON p.id = (
                SELECT id FROM pengukuran WHERE balita_id = b.id
                ORDER BY tanggal DESC LIMIT 1)
           WHERE b.aktif = 1""")

    n_normal = sum(1 for r in terkini if r["z_lhfa"] is not None and r["z_lhfa"] >= -2)
    n_pendek = sum(1 for r in terkini if r["z_lhfa"] is not None and -3 <= r["z_lhfa"] < -2)
    n_sangat = sum(1 for r in terkini if r["z_lhfa"] is not None and r["z_lhfa"] < -3)
    n_belum = sum(1 for r in terkini if r["z_lhfa"] is None)

    # balita perlu perhatian (stunting / berisiko), diurutkan paling berisiko
    waspada = []
    for r in terkini:
        if r["z_lhfa"] is None:
            continue
        if r["z_lhfa"] < -1.5:
            waspada.append(r)
    waspada.sort(key=lambda r: r["z_lhfa"])

    # penimbangan bulan ini
    awal_bulan = date.today().replace(day=1).isoformat()
    bulan_ini = db.query(
        "SELECT COUNT(DISTINCT balita_id) n FROM pengukuran WHERE tanggal >= ?",
        (awal_bulan,), one=True)["n"]

    # sebaran umur
    umur_kelompok = {"0-11 bulan": 0, "12-23 bulan": 0, "24-35 bulan": 0,
                     "36-47 bulan": 0, "48-59 bulan": 0}
    for r in terkini:
        h = (date.today() - growth.parse_date(r["birth_date"])).days
        b = h // 30
        if b < 12:
            umur_kelompok["0-11 bulan"] += 1
        elif b < 24:
            umur_kelompok["12-23 bulan"] += 1
        elif b < 36:
            umur_kelompok["24-35 bulan"] += 1
        elif b < 48:
            umur_kelompok["36-47 bulan"] += 1
        else:
            umur_kelompok["48-59 bulan"] += 1

    # tren penimbangan 6 bulan terakhir
    tren_bulanan = []
    for i in range(5, -1, -1):
        d = date.today().replace(day=1)
        y, m = d.year, d.month - i
        while m <= 0:
            m += 12
            y -= 1
        ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
        n = db.query(
            "SELECT COUNT(*) n FROM pengukuran WHERE tanggal >= ? AND tanggal < ?",
            (date(y, m, 1).isoformat(), date(ny, nm, 1).isoformat()), one=True)["n"]
        tren_bulanan.append({"label": f"{growth.parse_date(date(y, m, 1)).strftime('%b')}",
                             "bulan": m, "tahun": y, "jumlah": n})

    return render_template(
        "dashboard.html",
        total_balita=total,
        n_normal=n_normal, n_pendek=n_pendek, n_sangat=n_sangat, n_belum=n_belum,
        persen_stunting=round((n_pendek + n_sangat) / total * 100, 1) if total else 0,
        bulan_ini=bulan_ini, waspada=waspada[:6], umur_kelompok=umur_kelompok,
        tren_bulanan=tren_bulanan,
    )


# ===========================================================================
# Data balita
# ===========================================================================
@app.route("/balita")
@login_required
def balita_list():
    cari = (request.args.get("q") or "").strip()
    status = request.args.get("status") or ""

    sql = "SELECT * FROM balita WHERE aktif = 1"
    params = []
    if cari:
        sql += " AND (nama LIKE ? OR nama_ibu LIKE ? OR nama_ayah LIKE ?)"
        params += [f"%{cari}%"] * 3
    sql += " ORDER BY nama"

    daftar = [ringkas_balita(b) for b in db.query(sql, params)]

    if status == "stunting":
        daftar = [d for d in daftar if d["stunting"]["stunted"]]
    elif status == "risiko":
        daftar = [d for d in daftar if d["z_lhfa"] is not None and -2 <= d["z_lhfa"] < -1.5]
    elif status == "normal":
        daftar = [d for d in daftar if d["z_lhfa"] is not None and d["z_lhfa"] >= -1.5]
    elif status == "belum":
        daftar = [d for d in daftar if d["z_lhfa"] is None]

    return render_template("balita_list.html", daftar=daftar, cari=cari, status=status)


@app.route("/balita/tambah", methods=["GET", "POST"])
@login_required
def balita_tambah():
    if request.method == "POST":
        f = request.form
        nama = (f.get("nama") or "").strip()
        if not nama:
            flash("Nama balita wajib diisi.", "error")
            return render_template("balita_form.html", data=f, mode="tambah")

        balita_id = db.execute(
            """INSERT INTO balita
               (nik, no_kk, nama, sex, birth_date, nama_ibu, nama_ayah, no_hp,
                alamat, rt, rw, bb_lahir, pb_lahir, asi_eksklusif,
                berat_ibu_hamil, tinggi_ibu, catatan)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (f.get("nik"), f.get("no_kk"), nama, f.get("sex"),
             f.get("birth_date"), f.get("nama_ibu"), f.get("nama_ayah"),
             f.get("no_hp"), f.get("alamat"), f.get("rt"), f.get("rw"),
             f.get("bb_lahir") or None, f.get("pb_lahir") or None,
             1 if f.get("asi_eksklusif") == "1" else (0 if f.get("asi_eksklusif") == "0" else None),
             f.get("berat_ibu_hamil") or None, f.get("tinggi_ibu") or None,
             f.get("catatan")))
        flash(f"Data balita {nama} berhasil disimpan.", "sukses")
        return redirect(url_for("balita_detail", balita_id=balita_id))

    return render_template("balita_form.html", data={}, mode="tambah")


@app.route("/balita/<int:balita_id>")
@login_required
def balita_detail(balita_id):
    balita = ambil_balita(balita_id)
    if balita is None:
        flash("Data balita tidak ditemukan.", "error")
        return redirect(url_for("balita_list"))

    riwayat = riwayat_ukur(balita_id)
    info = ringkas_balita(balita)
    tl = db.query(
        "SELECT * FROM tindak_lanjut WHERE balita_id = ? ORDER BY tanggal DESC",
        (balita_id,))

    return render_template("balita_detail.html", b=balita, riwayat=riwayat,
                           info=info, tindak_lanjut=tl)


@app.route("/balita/<int:balita_id>/edit", methods=["GET", "POST"])
@login_required
def balita_edit(balita_id):
    balita = ambil_balita(balita_id)
    if balita is None:
        flash("Data balita tidak ditemukan.", "error")
        return redirect(url_for("balita_list"))

    if request.method == "POST":
        f = request.form
        db.execute(
            """UPDATE balita SET nik=?, no_kk=?, nama=?, sex=?, birth_date=?,
               nama_ibu=?, nama_ayah=?, no_hp=?, alamat=?, rt=?, rw=?,
               bb_lahir=?, pb_lahir=?, asi_eksklusif=?, berat_ibu_hamil=?,
               tinggi_ibu=?, catatan=? WHERE id=?""",
            (f.get("nik"), f.get("no_kk"), (f.get("nama") or "").strip(), f.get("sex"),
             f.get("birth_date"), f.get("nama_ibu"), f.get("nama_ayah"), f.get("no_hp"),
             f.get("alamat"), f.get("rt"), f.get("rw"),
             f.get("bb_lahir") or None, f.get("pb_lahir") or None,
             1 if f.get("asi_eksklusif") == "1" else (0 if f.get("asi_eksklusif") == "0" else None),
             f.get("berat_ibu_hamil") or None, f.get("tinggi_ibu") or None,
             f.get("catatan"), balita_id))
        flash("Perubahan data balita berhasil disimpan.", "sukses")
        return redirect(url_for("balita_detail", balita_id=balita_id))

    return render_template("balita_form.html", data=balita, mode="edit", b=balita)


@app.route("/balita/<int:balita_id>/hapus", methods=["POST"])
@role_required("admin")
def balita_hapus(balita_id):
    balita = ambil_balita(balita_id)
    if balita:
        db.execute("DELETE FROM balita WHERE id = ?", (balita_id,))
        flash(f"Data balita {balita['nama']} beserta riwayatnya telah dihapus.", "sukses")
    return redirect(url_for("balita_list"))


# ===========================================================================
# Penimbangan / pengukuran
# ===========================================================================
@app.route("/balita/<int:balita_id>/ukur", methods=["GET", "POST"])
@login_required
def pengukuran_tambah(balita_id):
    balita = ambil_balita(balita_id)
    if balita is None:
        flash("Data balita tidak ditemukan.", "error")
        return redirect(url_for("balita_list"))

    if request.method == "POST":
        f = request.form
        tanggal = f.get("tanggal") or date.today().isoformat()
        try:
            berat = float(f.get("berat")) if f.get("berat") else None
            tinggi = float(f.get("tinggi")) if f.get("tinggi") else None
            lk = float(f.get("lingkar_kepala")) if f.get("lingkar_kepala") else None
            lila = float(f.get("lingkar_lengan")) if f.get("lingkar_lengan") else None
        except ValueError:
            flash("Berat, tinggi, dan lingkar harus berupa angka.", "error")
            return render_template("pengukuran_form.html", b=balita, data=f)

        if berat is None or tinggi is None:
            flash("Berat badan dan panjang/tinggi badan wajib diisi.", "error")
            return render_template("pengukuran_form.html", b=balita, data=f)

        cara = f.get("cara_ukur") or "berbaring"

        # --- hitung Z-Score WHO ---
        hasil = growth.assess(
            sex=balita["sex"], birth_date=balita["birth_date"], measured_date=tanggal,
            weight=berat, height=tinggi, head_circumference=lk,
            measured_lying=(cara == "berbaring"))

        r = hasil["results"]
        ind_wfh = "wfl" if "wfl" in r else ("wfh" if "wfh" in r else None)

        try:
            db.execute(
                """INSERT INTO pengukuran
                   (balita_id, tanggal, umur_hari, berat, tinggi, lingkar_kepala,
                    lingkar_lengan, cara_ukur, z_wfa, z_lhfa, z_wfh, z_hcfa,
                    indikator_wfh, status_gizi, status_stunting, catatan, dicatat_oleh)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (balita_id, tanggal, hasil["age_days"], berat, tinggi, lk, lila, cara,
                 r["wfa"]["z"] if "wfa" in r else None,
                 r["lhfa"]["z"] if "lhfa" in r else None,
                 r[ind_wfh]["z"] if ind_wfh else None,
                 r["hcfa"]["z"] if "hcfa" in r else None,
                 ind_wfh,
                 r["wfa"]["status"]["label"] if "wfa" in r else None,
                 r["lhfa"]["status"]["code"] if "lhfa" in r else None,
                 f.get("catatan"), current_user()["id"]))
            flash("Hasil penimbangan berhasil disimpan dan Z-Score berhasil dihitung.",
                  "sukses")
            for w in hasil["warnings"]:
                flash(w, "peringatan")
            return redirect(url_for("balita_detail", balita_id=balita_id))
        except Exception as exc:  # umumnya pelanggaran UNIQUE (balita, tanggal)
            if "UNIQUE" in str(exc):
                flash("Sudah ada data penimbangan pada tanggal tersebut. "
                      "Hapus atau ubah data yang lama terlebih dahulu.", "error")
            else:
                flash(f"Gagal menyimpan data: {exc}", "error")
            return render_template("pengukuran_form.html", b=balita, data=f)

    return render_template("pengukuran_form.html", b=balita,
                           data={"tanggal": date.today().isoformat()})


@app.route("/pengukuran")
@login_required
def pengukuran_list():
    awal = request.args.get("dari") or date.today().replace(day=1).isoformat()
    akhir = request.args.get("sampai") or date.today().isoformat()
    rows = db.query(
        """SELECT p.*, b.nama, b.sex, b.birth_date FROM pengukuran p
           JOIN balita b ON b.id = p.balita_id
           WHERE p.tanggal BETWEEN ? AND ? ORDER BY p.tanggal DESC, b.nama""",
        (awal, akhir))
    return render_template("pengukuran_list.html", rows=rows, awal=awal, akhir=akhir)


@app.route("/pengukuran/<int:ukur_id>/hapus", methods=["POST"])
@login_required
def pengukuran_hapus(ukur_id):
    row = db.query("SELECT * FROM pengukuran WHERE id = ?", (ukur_id,), one=True)
    if row:
        db.execute("DELETE FROM pengukuran WHERE id = ?", (ukur_id,))
        flash("Data penimbangan telah dihapus.", "sukses")
        return redirect(url_for("balita_detail", balita_id=row["balita_id"]))
    return redirect(url_for("pengukuran_list"))


# ===========================================================================
# Prediksi dini stunting (berbasis Z-Score WHO)
# ===========================================================================
@app.route("/prediksi")
@login_required
def prediksi_list():
    tingkat = request.args.get("tingkat") or ""
    daftar = [ringkas_balita(b) for b in db.query(
        "SELECT * FROM balita WHERE aktif = 1 ORDER BY nama")]

    # lengkapi dengan peringatan dini
    urut = {"bahaya": 3, "waspada": 2, "normal": 1, "netral": 0}
    for d in daftar:
        d["peringatan"], d["tren"] = peringatan_dari_data(
            d["z_lhfa"], d["z_wfa"], d["z_wfh"], d["_hist"])
        d["risiko"] = max((urut.get(f["level"], 0) for f in d["peringatan"]), default=0)

    if tingkat == "bahaya":
        daftar = [d for d in daftar if d["risiko"] == 3]
    elif tingkat == "waspada":
        daftar = [d for d in daftar if d["risiko"] == 2]
    elif tingkat == "aman":
        daftar = [d for d in daftar if d["risiko"] <= 1]

    daftar.sort(key=lambda d: (-d["risiko"], d["z_lhfa"] if d["z_lhfa"] is not None else 0))

    ringkas = {
        "bahaya": sum(1 for d in daftar if d["risiko"] == 3),
        "waspada": sum(1 for d in daftar if d["risiko"] == 2),
        "aman": sum(1 for d in daftar if d["risiko"] <= 1),
        "total": len(daftar),
    }
    return render_template("prediksi_list.html", daftar=daftar, tingkat=tingkat,
                           ringkas=ringkas)


@app.route("/balita/<int:balita_id>/prediksi")
@login_required
def prediksi_detail(balita_id):
    balita = ambil_balita(balita_id)
    if balita is None:
        flash("Data balita tidak ditemukan.", "error")
        return redirect(url_for("prediksi_list"))

    riwayat = riwayat_ukur(balita_id)
    if not riwayat:
        flash("Balita ini belum memiliki data penimbangan, prediksi belum dapat dihitung.",
              "peringatan")
        return redirect(url_for("balita_detail", balita_id=balita_id))

    terbaru = riwayat[0]
    hist = [{"measured_date": r["tanggal"], "z": r["z_lhfa"]} for r in reversed(riwayat)]

    # penilaian ulang lengkap dari data terakhir memakai mesin Z-Score WHO
    hasil = growth.assess(
        sex=balita["sex"], birth_date=balita["birth_date"],
        measured_date=terbaru["tanggal"], weight=terbaru["berat"],
        height=terbaru["tinggi"], head_circumference=terbaru["lingkar_kepala"],
        measured_lying=(terbaru["cara_ukur"] == "berbaring"))
    growth.early_warning(hasil, hist)

    return render_template("prediksi_detail.html", b=balita, hasil=hasil,
                           riwayat=riwayat, terbaru=terbaru,
                           info=ringkas_balita(balita))


# ===========================================================================
# Grafik pertumbuhan / KMS digital
# ===========================================================================
@app.route("/balita/<int:balita_id>/kms")
@login_required
def kms(balita_id):
    balita = ambil_balita(balita_id)
    if balita is None:
        flash("Data balita tidak ditemukan.", "error")
        return redirect(url_for("balita_list"))
    return render_template("kms.html", b=balita, riwayat=riwayat_ukur(balita_id),
                           info=ringkas_balita(balita))


@app.route("/api/balita/<int:balita_id>/grafik")
@login_required
def api_grafik(balita_id):
    """Data JSON untuk grafik KMS: titik anak + kurva rujukan WHO."""
    balita = ambil_balita(balita_id)
    if balita is None:
        return jsonify({"error": "Balita tidak ditemukan"}), 404

    indikator = request.args.get("indikator", "lhfa")
    if indikator not in growth.INDICATORS:
        return jsonify({"error": "Indikator tidak dikenal"}), 400

    sex = balita["sex"]
    axis = growth.INDICATORS[indikator]["axis"]
    riwayat = list(reversed(riwayat_ukur(balita_id)))

    titik = []
    for r in riwayat:
        if axis == "day":
            x, nilai = r["umur_hari"], r["berat"] if indikator == "wfa" else (
                r["tinggi"] if indikator == "lhfa" else r["lingkar_kepala"])
        else:
            x, nilai = r["tinggi"], r["berat"]
        if x is None or nilai is None:
            continue
        z = growth.zscore(nilai, indikator, sex, x)
        titik.append({
            "x": x, "y": nilai, "z": round(z, 2) if z is not None else None,
            "tanggal": r["tanggal"],
            "label": growth.age_text(r["umur_hari"]) if axis == "day" else f"{x} cm",
        })

    # rentang sumbu-X
    if axis == "day":
        x_min, x_max = 0, growth.MAX_AGE_DAYS
    else:
        x_min, x_max = (45, 110) if indikator == "wfl" else (65, 120)

    kurva = growth.reference_curve(indikator, sex, x_min, x_max,
                                   z_lines=(-3, -2, -1, 0, 1, 2, 3))

    return jsonify({
        "indikator": indikator,
        "label": growth.INDICATORS[indikator]["label"],
        "short": growth.INDICATORS[indikator]["short"],
        "unit": growth.INDICATORS[indikator]["unit"],
        "axis": axis,
        "titik": titik,
        "kurva": {str(k): v for k, v in kurva.items()},
    })


# ===========================================================================
# Tindak lanjut
# ===========================================================================
@app.route("/balita/<int:balita_id>/tindak-lanjut", methods=["POST"])
@login_required
def tindak_lanjut_tambah(balita_id):
    balita = ambil_balita(balita_id)
    if balita is None:
        flash("Data balita tidak ditemukan.", "error")
        return redirect(url_for("balita_list"))

    f = request.form
    if not (f.get("jenis") or "").strip():
        flash("Jenis tindak lanjut wajib dipilih.", "error")
        return redirect(url_for("balita_detail", balita_id=balita_id))

    terakhir = ukur_terakhir(balita_id)
    db.execute(
        """INSERT INTO tindak_lanjut
           (balita_id, pengukuran_id, tanggal, jenis, keterangan, petugas, dicatat_oleh)
           VALUES (?,?,?,?,?,?,?)""",
        (balita_id, terakhir["id"] if terakhir else None,
         f.get("tanggal") or date.today().isoformat(),
         f.get("jenis"), f.get("keterangan"),
         f.get("petugas") or current_user()["nama"], current_user()["id"]))
    flash("Catatan tindak lanjut berhasil disimpan.", "sukses")
    return redirect(url_for("balita_detail", balita_id=balita_id))


# ===========================================================================
# Laporan
# ===========================================================================
def laporan_data(dari, sampai):
    """Data laporan status gizi per balita pada periode tertentu."""
    rows = db.query(
        """SELECT b.id, b.nama, b.sex, b.birth_date, b.nama_ibu,
                  p.tanggal, p.umur_hari, p.berat, p.tinggi, p.lingkar_kepala,
                  p.z_wfa, p.z_lhfa, p.z_wfh, p.status_gizi, p.status_stunting
           FROM balita b
           JOIN pengukuran p ON p.id = (
                SELECT id FROM pengukuran WHERE balita_id = b.id
                  AND tanggal BETWEEN ? AND ?
                ORDER BY tanggal DESC LIMIT 1)
           WHERE b.aktif = 1
           ORDER BY b.nama""", (dari, sampai))

    hasil = []
    for r in rows:
        item = dict(r)
        item["umur_kini"] = (date.today() - growth.parse_date(r["birth_date"])).days
        item["stunting"] = growth.classify("lhfa", r["z_lhfa"])
        item["gizi"] = growth.classify("wfa", r["z_wfa"])
        item["wfh"] = growth.classify("wfh", r["z_wfh"])
        hasil.append(item)

    rekap = {
        "total": len(hasil),
        "normal": sum(1 for x in hasil if x["z_lhfa"] is not None and x["z_lhfa"] >= -2),
        "pendek": sum(1 for x in hasil if x["z_lhfa"] is not None and -3 <= x["z_lhfa"] < -2),
        "sangat_pendek": sum(1 for x in hasil if x["z_lhfa"] is not None and x["z_lhfa"] < -3),
        "belum_ukur": sum(1 for x in hasil if x["z_lhfa"] is None),
        "gizi_kurang": sum(1 for x in hasil if x["z_wfa"] is not None and x["z_wfa"] < -2),
    }
    rekap["stunting"] = rekap["pendek"] + rekap["sangat_pendek"]
    rekap["persen_stunting"] = (round(rekap["stunting"] / rekap["total"] * 100, 1)
                                if rekap["total"] else 0)
    return hasil, rekap


@app.route("/laporan")
@login_required
def laporan():
    dari = request.args.get("dari") or date(date.today().year, 1, 1).isoformat()
    sampai = request.args.get("sampai") or date.today().isoformat()
    hasil, rekap = laporan_data(dari, sampai)
    return render_template("laporan.html", hasil=hasil, rekap=rekap,
                           dari=dari, sampai=sampai)


@app.route("/laporan/cetak")
@login_required
def laporan_cetak():
    dari = request.args.get("dari") or date(date.today().year, 1, 1).isoformat()
    sampai = request.args.get("sampai") or date.today().isoformat()
    hasil, rekap = laporan_data(dari, sampai)
    return render_template("laporan_cetak.html", hasil=hasil, rekap=rekap,
                           dari=dari, sampai=sampai)


@app.route("/laporan/export.csv")
@login_required
def laporan_export():
    dari = request.args.get("dari") or date(date.today().year, 1, 1).isoformat()
    sampai = request.args.get("sampai") or date.today().isoformat()
    hasil, _ = laporan_data(dari, sampai)

    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";", lineterminator="\r\n")
    w.writerow(["No", "Nama Balita", "L/P", "Tanggal Lahir", "Umur",
                "Nama Ibu", "Tanggal Ukur", "Berat (kg)", "Tinggi (cm)",
                "LK (cm)", "Z BB/U", "Z TB/U", "Z BB/TB",
                "Status Gizi (BB/U)", "Status Stunting (TB/U)"])
    for i, x in enumerate(hasil, 1):
        w.writerow([
            i, x["nama"], "L" if x["sex"] == "M" else "P",
            tgl_id(x["birth_date"], "pendek"), growth.age_text(x["umur_kini"]),
            x["nama_ibu"] or "-", tgl_id(x["tanggal"], "pendek"),
            angka_fmt(x["berat"], 2), angka_fmt(x["tinggi"], 1),
            angka_fmt(x["lingkar_kepala"], 1),
            angka_fmt(x["z_wfa"], 2), angka_fmt(x["z_lhfa"], 2), angka_fmt(x["z_wfh"], 2),
            x["status_gizi"] or "-", x["stunting"]["label"],
        ])

    nama = f"laporan-posyandu-{dari}-sd-{sampai}.csv"
    return Response(
        "﻿" + buf.getvalue(),  # BOM agar Excel membaca UTF-8 dengan benar
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nama}"'})


# ===========================================================================
# Manajemen pengguna (khusus administrator)
# ===========================================================================
@app.route("/pengguna")
@role_required("admin")
def pengguna_list():
    rows = db.query("SELECT * FROM users ORDER BY role, nama")
    return render_template("pengguna_list.html", rows=rows)


@app.route("/pengguna/tambah", methods=["GET", "POST"])
@role_required("admin")
def pengguna_tambah():
    if request.method == "POST":
        f = request.form
        username = (f.get("username") or "").strip()
        password = f.get("password") or ""
        if not username or not password:
            flash("Nama pengguna dan kata sandi wajib diisi.", "error")
            return render_template("pengguna_form.html", data=f, mode="tambah")
        if db.query("SELECT id FROM users WHERE username = ?", (username,), one=True):
            flash("Nama pengguna tersebut sudah dipakai.", "error")
            return render_template("pengguna_form.html", data=f, mode="tambah")
        db.execute(
            "INSERT INTO users (username, password_hash, nama, jabatan, role) "
            "VALUES (?,?,?,?,?)",
            (username, generate_password_hash(password), (f.get("nama") or "").strip(),
             f.get("jabatan"), f.get("role") or "kader"))
        flash(f"Akun {username} berhasil dibuat.", "sukses")
        return redirect(url_for("pengguna_list"))
    return render_template("pengguna_form.html", data={}, mode="tambah")


@app.route("/pengguna/<int:user_id>/edit", methods=["GET", "POST"])
@role_required("admin")
def pengguna_edit(user_id):
    row = db.query("SELECT * FROM users WHERE id = ?", (user_id,), one=True)
    if row is None:
        flash("Akun tidak ditemukan.", "error")
        return redirect(url_for("pengguna_list"))

    if request.method == "POST":
        f = request.form
        db.execute("UPDATE users SET nama=?, jabatan=?, role=?, aktif=? WHERE id=?",
                   ((f.get("nama") or "").strip(), f.get("jabatan"),
                    f.get("role") or "kader", 1 if f.get("aktif") else 0, user_id))
        baru = f.get("password")
        if baru:
            db.execute("UPDATE users SET password_hash = ? WHERE id = ?",
                       (generate_password_hash(baru), user_id))
            flash("Data akun dan kata sandi berhasil diperbarui.", "sukses")
        else:
            flash("Data akun berhasil diperbarui.", "sukses")
        return redirect(url_for("pengguna_list"))

    return render_template("pengguna_form.html", data=row, mode="edit")


@app.route("/pengguna/<int:user_id>/hapus", methods=["POST"])
@role_required("admin")
def pengguna_hapus(user_id):
    if user_id == current_user()["id"]:
        flash("Anda tidak dapat menghapus akun yang sedang digunakan.", "error")
        return redirect(url_for("pengguna_list"))
    row = db.query("SELECT * FROM users WHERE id = ?", (user_id,), one=True)
    if row:
        db.execute("DELETE FROM users WHERE id = ?", (user_id,))
        flash(f"Akun {row['username']} telah dihapus.", "sukses")
    return redirect(url_for("pengguna_list"))


@app.route("/pengaturan", methods=["GET", "POST"])
@role_required("admin")
def pengaturan():
    if request.method == "POST":
        for k, v in request.form.items():
            if k in ("nama_posyandu", "desa", "kecamatan", "kabupaten",
                     "provinsi", "wilayah", "puskesmas", "nama_ketua"):
                db.execute("INSERT OR REPLACE INTO pengaturan (kunci, nilai) "
                           "VALUES (?, ?)", (k, v))
        flash("Pengaturan berhasil disimpan.", "sukses")
        return redirect(url_for("pengaturan"))

    rows = db.query("SELECT kunci, nilai FROM pengaturan")
    data = {r["kunci"]: r["nilai"] for r in rows}
    return render_template("pengaturan.html", data=data)


# ===========================================================================
# Penanganan galat
# ===========================================================================
@app.errorhandler(404)
def tidak_ditemukan(e):
    return render_template("error.html", kode=404,
                           pesan="Halaman yang Anda cari tidak ditemukan."), 404


@app.errorhandler(500)
def galat_server(e):
    return render_template("error.html", kode=500,
                           pesan="Terjadi gangguan pada sistem."), 500


# ===========================================================================
if __name__ == "__main__":
    if not os.path.exists(db.DB_PATH):
        print("Basis data belum ada. Membuat tabel dan data awal...")
        db.init_db(seed=True)
    print("=" * 64)
    print("  Sistem Informasi E-Posyandu Terintegrasi")
    print("  Posyandu Lestari 12 - Merden, Purwanegara, Banjarnegara")
    print("=" * 64)
    print("  Buka di peramban:  http://127.0.0.1:5000")
    print("  Akun contoh:       admin/admin123  |  kader/kader123  |  bidan/bidan123")
    print("=" * 64)
    app.run(debug=True, host="127.0.0.1", port=5000)
