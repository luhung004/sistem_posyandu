"""
Pengisian data awal (seed) untuk Sistem Informasi E-Posyandu.

Menghasilkan:
  - 3 akun pengguna    : admin, kader, bidan
  - 24 data balita     : dengan variasi status gizi (normal, berisiko, stunting)
  - riwayat penimbangan bulanan beserta Z-Score WHO yang sudah dihitung
  - beberapa catatan tindak lanjut

Nilai antropometri dibangkitkan dengan membalik rumus Z-Score WHO
(growth.value_for_z), sehingga data contoh konsisten dengan tabel rujukan WHO
dan hasil perhitungannya tetap dapat diverifikasi.

Jalankan:  python seed.py          (membuat ulang dari kosong)
"""
import os
import secrets
import random
import sqlite3
from datetime import date, timedelta

import db
import growth

random.seed(20260101)  # hasil dapat direproduksi

TODAY = date.today()

# ---------------------------------------------------------------------------
# Akun pengguna awal
# ---------------------------------------------------------------------------
from werkzeug.security import generate_password_hash  # noqa: E402

# Kata sandi TIDAK ditulis di sini.  Nilai yang tertanam dalam kode publik bisa
# ditebak siapa saja, sehingga akun admin pada server yang sedang daring akan
# dibobol hanya dengan mencoba beberapa kombinasi umum.  Sebagai gantinya, kata
# sandi acak dibuat saat penempatan dan disimpan di berkas lokal yang tidak
# ikut terunggah ke repositori.
def _sandi_acak():
    huruf = "abcdefghijkmnopqrstuvwxyz23456789"
    return "".join(secrets.choice(huruf) for _ in range(12))


USERS = [
    ("admin", "Administrator Sistem", "Pengelola Sistem", "admin"),
    ("kader", "Sri Wahyuni", "Kader Posyandu", "kader"),
    ("bidan", "Rina Puspitasari, A.Md.Keb", "Bidan Desa", "bidan"),
]
BERKAS_SANDI = "demo-credentials.txt"

# ---------------------------------------------------------------------------
# Data balita contoh
# ---------------------------------------------------------------------------
# profil: normal | risiko | stunting
NAMA_BALITA = [
    ("Ahmad Fauzan", "M"), ("Aisyah Putri", "F"), ("Bagas Setiawan", "M"),
    ("Bunga Amelia", "F"), ("Cahyo Nugroho", "M"), ("Citra Ayu Lestari", "F"),
    ("Dimas Pratama", "M"), ("Dewi Anggraeni", "F"), ("Eko Prasetyo", "M"),
    ("Eka Nurhayati", "F"), ("Fajar Ramadhan", "M"), ("Fitri Handayani", "F"),
    ("Galih Permana", "M"), ("Gita Savitri", "F"), ("Hendra Wijaya", "M"),
    ("Hana Salsabila", "F"), ("Irfan Maulana", "M"), ("Indah Permatasari", "F"),
    ("Joko Susilo", "M"), ("Jihan Aulia", "F"), ("Krisna Bayu", "M"),
    ("Kartika Sari", "F"), ("Lukman Hakim", "M"), ("Larasati Dewi", "F"),
]

NAMA_IBU = [
    "Siti Aminah", "Riyanti", "Sumarni", "Nur Hidayah", "Warsiti", "Endang Susanti",
    "Tuti Rahayu", "Sriyati", "Mujiati", "Lastri", "Umi Kulsum", "Dwi Astuti",
]
NAMA_AYAH = [
    "Slamet Riyadi", "Bambang Sutrisno", "Agus Setiawan", "Joko Widodo", "Sukirman",
    "Tarmuji", "Purnomo", "Wahyudi", "Santoso", "Margono", "Hariyanto", "Supriyadi",
]
RT_RW = [("01", "02"), ("02", "02"), ("03", "01"), ("04", "03"), ("01", "04"), ("02", "05")]

# sebaran profil: 60% normal, 20% berisiko, 20% stunting
PROFILE_POOL = ["normal"] * 14 + ["risiko"] * 5 + ["stunting"] * 5
random.shuffle(PROFILE_POOL)

CATATAN_TINDAK_LANJUT = {
    "stunting": [
        ("rujukan", "Dirujuk ke Puskesmas Purwanegara untuk pemeriksaan dan "
                    "penanganan gizi buruk/stunting."),
        ("PMT", "Diberikan Pemberian Makanan Tambahan (PMT) berupa biskuit "
                "dan susu selama 30 hari."),
        ("kunjungan rumah", "Kunjungan rumah oleh kader: edukasi gizi ibu, "
                            "sanitasi lingkungan, dan pemantauan asupan makan."),
    ],
    "risiko": [
        ("edukasi", "Edukasi gizi dan pemberian ASI/MP-ASI bergizi kepada ibu."),
        ("kunjungan rumah", "Pemantauan tumbuh kembang bulanan oleh kader."),
    ],
}


def sub_months(y, m, k):
    """Kurangi k bulan dari (tahun y, bulan m). Bulan 1-12."""
    total = (y * 12 + (m - 1)) - k
    return total // 12, total % 12 + 1


def umur_bulan(tahun, bulan, ref=TODAY):
    return (ref.year - tahun) * 12 + (ref.month - bulan)


# ---------------------------------------------------------------------------
def seed_database():
    db.init_db()

    if db.query("SELECT COUNT(*) AS n FROM users", one=True)["n"] > 0:
        print("Data awal sudah ada. Lewati pengisian (seed) untuk mencegah duplikasi.")
        return

    # ---- pengguna --------------------------------------------------------
    daftar_sandi = []
    for username, nama, jabatan, role in USERS:
        pw = _sandi_acak()
        daftar_sandi.append((username, pw))
        db.execute(
            """INSERT INTO users (username, password_hash, nama, jabatan, role)
               VALUES (?, ?, ?, ?, ?)""",
            (username, generate_password_hash(pw), nama, jabatan, role),
        )

    # Kredensial demo ditulis ke berkas lokal (sudah masuk .gitignore), bukan
    # ditampilkan di layar atau dicetak ke log server.
    try:
        with open(os.path.join(db.DATA_DIR, BERKAS_SANDI), "w",
                  encoding="utf-8") as fh:
            fh.write("Kredensial demo E-Posyandu\n")
            fh.write("=" * 40 + "\n")
            for username, pw in daftar_sandi:
                fh.write("%-8s : %s\n" % (username, pw))
            fh.write("=" * 40 + "\n")
            fh.write("Segera ganti kata sandi ini lewat menu Pengguna.\n")
    except OSError:
        pass
    kader_id = db.query("SELECT id FROM users WHERE username = 'kader'", one=True)["id"]

    # ---- pengaturan ------------------------------------------------------
    pengaturan = [
        ("nama_posyandu", "Posyandu Lestari 12"),
        ("desa", "Merden"),
        ("kecamatan", "Purwanegara"),
        ("kabupaten", "Banjarnegara"),
        ("provinsi", "Jawa Tengah"),
        ("wilayah", "Rawawungu"),
        ("puskesmas", "Puskesmas Purwanegara"),
        ("nama_ketua", "Sri Wahyuni"),
    ]
    for k, v in pengaturan:
        db.execute("INSERT OR REPLACE INTO pengaturan (kunci, nilai) VALUES (?, ?)", (k, v))

    # ---- balita ----------------------------------------------------------
    dibuat_balita = 0
    dibuat_ukur = 0
    dibuat_tl = 0

    for idx, (nama, sex) in enumerate(NAMA_BALITA):
        profil = PROFILE_POOL[idx]

        # umur anak saat ini antara 2 dan 58 bulan
        umur_bln = random.randint(2, 58)
        # tanggal lahir di awal bulan + offset acak
        by, bm = sub_months(TODAY.year, TODAY.month, umur_bln)
        birth = date(by, bm, min(random.randint(1, 20), 28))
        if birth > TODAY:
            birth = TODAY - timedelta(days=umur_bln * 30)

        # faktor pendukung
        tinggi_ibu = round(random.uniform(145, 165), 1)
        berat_ibu = round(random.uniform(45, 72), 1)
        asi_eks = 1 if random.random() < 0.7 else 0

        bb_lahir = round(random.uniform(2.5, 3.8), 2)
        pb_lahir = round(random.uniform(46, 52), 1)

        rt, rw = random.choice(RT_RW)
        alamat = f"Rawawungu RT {rt} RW {rw}, Merden, Purwanegara"

        balita_id = db.execute(
            """INSERT INTO balita (nama, sex, birth_date, nama_ibu, nama_ayah, no_hp,
                                   alamat, rt, rw, bb_lahir, pb_lahir, asi_eksklusif,
                                   berat_ibu_hamil, tinggi_ibu)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (nama, sex, birth.isoformat(),
             random.choice(NAMA_IBU), random.choice(NAMA_AYAH),
             "08" + "".join(str(random.randint(0, 9)) for _ in range(9)),
             alamat, rt, rw, bb_lahir, pb_lahir, asi_eks, berat_ibu, tinggi_ibu),
        )
        dibuat_balita += 1

        # ---- riwayat penimbangan bulanan --------------------------------
        # maksimum 24 bulan riwayat terakhir, dan tidak melewati umur 59 bulan
        mulai_bulan = min(24, umur_bln)
        n_ukur = 0
        arah = 0.0  # pergeseran Z-Score tinggi badan tiap bulan

        if profil == "stunting":
            z_target = -2.4 - random.uniform(0.0, 0.7)      # di bawah -2 SD
            arah = random.uniform(-0.03, 0.02)
        elif profil == "risiko":
            z_target = -1.6 - random.uniform(0.0, 0.4)      # mendekati -2 SD
            arah = random.uniform(-0.05, -0.01)             # cenderung menurun
        else:
            z_target = random.uniform(-0.6, 0.5)
            arah = random.uniform(-0.01, 0.02)

        z_berat_target = z_target + random.uniform(-0.4, 0.6)

        for langkah in range(mulai_bulan, -1, -1):
            dy, dm = sub_months(TODAY.year, TODAY.month, langkah)
            hari = min(10 + (idx % 5), 28)
            try:
                tgl = date(dy, dm, hari)
            except ValueError:
                continue
            if tgl < birth or tgl > TODAY:
                continue

            umur_hari = (tgl - birth).days
            if umur_hari < 0 or umur_hari > growth.MAX_AGE_DAYS:
                continue

            # pergeseran tren: makin ke belakang makin tinggi Z-nya
            geser = arah * (langkah - mulai_bulan / 2)

            z_h = z_target - geser + random.uniform(-0.08, 0.08)
            z_w = z_berat_target - geser * 0.6 + random.uniform(-0.15, 0.15)
            z_k = random.uniform(-0.8, 0.8)

            tinggi = growth.value_for_z(z_h, "lhfa", sex, umur_hari)
            berat = growth.value_for_z(z_w, "wfa", sex, umur_hari)
            lk = growth.value_for_z(z_k, "hcfa", sex, umur_hari)
            if None in (tinggi, berat, lk):
                continue

            tinggi = round(tinggi, 1)
            berat = round(berat, 2)
            lk = round(lk, 1)
            lila = round(random.uniform(11.5, 16.5) if umur_hari < 730
                         else random.uniform(12.5, 17.5), 1)
            cara = "berbaring" if umur_hari < 730 else "berdiri"

            # hitung Z-Score resmi dengan mesin WHO
            hasil = growth.assess(
                sex=sex, birth_date=birth, measured_date=tgl,
                weight=berat, height=tinggi, head_circumference=lk,
                measured_lying=(cara == "berbaring"),
            )
            r = hasil["results"]
            z_wfa = r["wfa"]["z"] if "wfa" in r else None
            z_lhfa = r["lhfa"]["z"] if "lhfa" in r else None
            ind_wfh = "wfl" if "wfl" in r else ("wfh" if "wfh" in r else None)
            z_wfh = r[ind_wfh]["z"] if ind_wfh else None
            z_hcfa = r["hcfa"]["z"] if "hcfa" in r else None

            db.execute(
                """INSERT OR IGNORE INTO pengukuran
                   (balita_id, tanggal, umur_hari, berat, tinggi, lingkar_kepala,
                    lingkar_lengan, cara_ukur, z_wfa, z_lhfa, z_wfh, z_hcfa,
                    indikator_wfh, status_gizi, status_stunting, dicatat_oleh)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (balita_id, tgl.isoformat(), umur_hari, berat, tinggi, lk, lila, cara,
                 z_wfa, z_lhfa, z_wfh, z_hcfa, ind_wfh,
                 growth.classify("wfa", z_wfa)["label"] if z_wfa is not None else None,
                 growth.classify("lhfa", z_lhfa)["code"] if z_lhfa is not None else None,
                 kader_id),
            )
            n_ukur += 1
            dibuat_ukur += 1

        # ---- tindak lanjut untuk kasus berisiko / stunting ---------------
        if profil in ("risiko", "stunting") and n_ukur:
            terakhir = db.query(
                "SELECT id, tanggal FROM pengukuran WHERE balita_id = ? "
                "ORDER BY tanggal DESC LIMIT 1", (balita_id,), one=True)
            for jenis, ket in random.sample(
                    CATATAN_TINDAK_LANJUT[profil],
                    k=min(2, len(CATATAN_TINDAK_LANJUT[profil]))):
                db.execute(
                    """INSERT INTO tindak_lanjut
                       (balita_id, pengukuran_id, tanggal, jenis, keterangan,
                        petugas, dicatat_oleh)
                       VALUES (?,?,?,?,?,?,?)""",
                    (balita_id, terakhir["id"] if terakhir else None,
                     terakhir["tanggal"] if terakhir else TODAY.isoformat(),
                     jenis, ket, "Sri Wahyuni", kader_id),
                )
                dibuat_tl += 1

    print("Data awal berhasil dibuat:")
    print(f"  pengguna         : {len(USERS)}")
    print(f"  balita           : {dibuat_balita}")
    print(f"  penimbangan      : {dibuat_ukur}")
    print(f"  tindak lanjut    : {dibuat_tl}")
    # Kata sandi sengaja tidak dicetak di sini.  Log server mudah dibaca pihak
    # lain, sedangkan berkas kredensial lokal bisa dikendalikan sendiri.
    print(f"\nKredensial demo tersimpan di: "
          f"{os.path.join(db.DATA_DIR, BERKAS_SANDI)}")


if __name__ == "__main__":
    # Sekali jalan: hapus basis data lama supaya bersih
    if os.path.exists(db.DB_PATH):
        os.remove(db.DB_PATH)
        print("Basis data lama dihapus.")
    seed_database()
