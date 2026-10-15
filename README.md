# Sistem Informasi E-Posyandu Terintegrasi

Aplikasi web untuk **pemantauan tumbuh kembang balita dan deteksi dini stunting**
di Posyandu. Perhitungan status gizi memakai **standar WHO Child Growth Standards
(2006)**, sehingga hasil Z-Score dan klasifikasi status gizi sesuai rujukan resmi
Kementerian Kesehatan RI.

Dikembangkan untuk **Posyandu Lestari 12**, Rawawungu, Merden, Kecamatan
Purwanegara, Kabupaten Banjarnegara, Jawa Tengah.

---

## Daftar Isi

- [Fitur](#fitur)
- [Teknologi](#teknologi)
- [Kebutuhan Sistem](#kebutuhan-sistem)
- [Cara Menjalankan](#cara-menjalankan)
- [Akun Bawaan](#akun-bawaan)
- [Struktur Proyek](#struktur-proyek)
- [Basis Data](#basis-data)
- [Data Rujukan WHO](#data-rujukan-who)
- [Peran Pengguna](#peran-pengguna)
- [Catatan Keamanan](#catatan-keamanan)
- [Pemecahan Masalah](#pemecahan-masalah)

---

## Fitur

**Manajemen data balita**
- Pendaftaran, penyuntingan, dan penghapusan data balita
- Profil balita lengkap: identitas, data orang tua, alamat, riwayat pengukuran

**Pengukuran & pemantauan pertumbuhan**
- Pencatatan berat badan, tinggi/panjang badan, dan lingkar kepala
- Perhitungan Z-Score otomatis untuk indikator BB/U, TB/U, BB/TB, dan IMT/U
- Klasifikasi status gizi (normal, kurang, sangat kurang, pendek, dsb.)
- Grafik pertumbuhan interaktif dan Kartu Menuju Sehat (KMS)
- Prediksi tinggi badan dan deteksi dini risiko stunting
- Pencatatan tindak lanjut hasil pemantauan

**Pelaporan**
- Rekap status gizi posyandu
- Laporan siap cetak
- Ekspor data ke CSV

**Administrasi**
- Manajemen pengguna dan hak akses
- Pengaturan identitas posyandu dan wilayah

---

## Teknologi

| Komponen | Keterangan |
|---|---|
| Bahasa | Python 3 |
| Kerangka web | Flask |
| Basis data | SQLite (berkas tunggal, tanpa server) |
| Antarmuka | HTML + CSS + JavaScript (vanilla) |
| Rujukan gizi | WHO Child Growth Standards 2006 (data L-M-S) |

Tidak memerlukan Node.js, build tool, atau server basis data terpisah.

---

## Kebutuhan Sistem

- **Python 3.8 atau lebih baru** — [unduh di python.org](https://www.python.org/downloads/)
  - Saat instalasi di Windows, **centang "Add Python to PATH"**
- **Flask** — dipasang otomatis oleh `run.bat` bila belum ada
- Peramban modern (Chrome, Edge, Firefox)
- Koneksi internet **hanya** dibutuhkan untuk memuat Google Fonts; aplikasi tetap
  berjalan tanpa internet

Memasang Flask secara manual:

```
python -m pip install flask
```

---

## Cara Menjalankan

### Cara 1 — Klik dua kali `run.bat` (disarankan, Windows)

1. Klik dua kali berkas `run.bat` di folder proyek
2. Jendela terminal terbuka dan server mulai berjalan
3. Peramban otomatis terbuka ke `http://127.0.0.1:5000`
4. Masuk memakai salah satu [akun bawaan](#akun-bawaan)

**Jendela terminal harus tetap terbuka** selama aplikasi dipakai. Menutupnya
akan menghentikan server.

`run.bat` otomatis:
- Memeriksa Python tersedia di PATH
- Memasang Flask bila belum terpasang
- Membuat basis data bila belum ada
- Membuka peramban

### Cara 2 — Lewat terminal

```
cd "sistem e-posyandu"
python app.py
```

Lalu buka `http://127.0.0.1:5000` di peramban.

### Menghentikan aplikasi

Tekan `Ctrl+C` di jendela terminal, atau tutup jendela tersebut.

### Mengulang data contoh (opsional)

Untuk membangun ulang basis data beserta data contoh:

```
python seed.py
```

---

## Akun Bawaan

Aplikasi menyertakan tiga akun contoh yang dibuat otomatis saat basis data
pertama kali dibangun. **Ganti kata sandi ini sebelum dipakai sungguhan.**

| Peran | Nama Pengguna | Kata Sandi | Nama | Jabatan |
|---|---|---|---|---|
| Administrator | `admin` | `admin123` | Administrator Sistem | Pengelola Sistem |
| Kader Posyandu | `kader` | `kader123` | Sri Wahyuni | Kader Posyandu |
| Bidan Desa | `bidan` | `bidan123` | Rina Puspitasari, A.Md.Keb | Bidan Desa |

> **Catatan:** kotak "akun contoh" pada halaman login sengaja dihapus agar kredensial
> tidak tampil di layar. Daftar akun kini hanya ada di dokumen ini dan pada keluaran
> terminal saat aplikasi dijalankan.

---

## Struktur Proyek

```
sistem e-posyandu/
├── app.py                  # Aplikasi Flask: rute, autentikasi, logika tampilan
├── db.py                   # Lapisan akses SQLite (koneksi, query, inisialisasi)
├── growth.py               # Mesin perhitungan Z-Score & klasifikasi status gizi
├── schema.sql              # Skema tabel basis data
├── seed.py                 # Pengisi data awal/contoh
├── run.bat                 # Penjalan praktis untuk Windows
├── README.md
├── data/
│   └── eposyandu.db        # Basis data SQLite (dibuat otomatis)
├── templates/              # Templat HTML (Jinja2)
│   ├── base.html           # Kerangka halaman
│   ├── login.html          # Halaman masuk
│   ├── splash.html         # Layar pembuka setelah masuk
│   ├── dashboard.html      # Ikhtisar
│   ├── balita_*.html       # Daftar, formulir, detail balita
│   ├── pengukuran_*.html   # Daftar & formulir pengukuran
│   ├── prediksi_*.html     # Daftar & detail prediksi
│   ├── kms.html            # Kartu Menuju Sehat
│   ├── laporan*.html       # Laporan & versi cetak
│   ├── pengguna_*.html     # Manajemen pengguna (admin)
│   ├── pengaturan.html     # Pengaturan identitas posyandu
│   ├── _ikon.html          # Kumpulan ikon SVG
│   └── error.html          # Halaman galat 404/500
├── static/
│   ├── css/style.css       # Gaya tampilan
│   ├── js/app.js           # Skrip antarmuka
│   ├── js/grafik.js        # Penggambaran grafik pertumbuhan
│   └── img/                # Logo posyandu
├── who_data/               # Tabel rujukan WHO (L-M-S) dalam JSON
│   ├── wfa_M.json / wfa_F.json   # Berat badan menurut umur
│   ├── lhfa_M.json / lhfa_F.json # Panjang/tinggi badan menurut umur
│   ├── wfl_M.json / wfl_F.json   # Berat menurut panjang badan
│   ├── wfh_M.json / wfh_F.json   # Berat menurut tinggi badan
│   ├── hcfa_M.json / hcfa_F.json # Lingkar kepala menurut umur
│   └── _manifest.json
└── tools/                  # Skrip bantu (tidak dipakai saat aplikasi berjalan)
    ├── build_who_data.py   # Membangun who_data/*.json dari berkas Excel WHO
    ├── validate_who.py     # Memeriksa kewajaran data rujukan
    ├── inspect_who.py      # Menampilkan isi data rujukan
    └── who_source/         # Berkas Excel sumber dari WHO
```

---

## Basis Data

SQLite, tersimpan di `data/eposyandu.db`. Dibuat otomatis dari `schema.sql`
saat aplikasi pertama kali dijalankan. Lima tabel utama:

| Tabel | Isi |
|---|---|
| `users` | Akun pengguna: nama pengguna, kata sandi (hash), nama, jabatan, peran, status aktif |
| `balita` | Data balita: identitas, tanggal lahir, jenis kelamin, data orang tua, alamat |
| `pengukuran` | Riwayat pengukuran: tanggal, berat, tinggi, lingkar kepala, Z-Score tiap indikator |
| `tindak_lanjut` | Catatan tindak lanjut hasil pemantauan |
| `pengaturan` | Identitas posyandu dan wilayah (pasangan kunci–nilai) |

Kata sandi disimpan sebagai **hash** (Werkzeug `generate_password_hash`), bukan
teks biasa. Cadangkan berkas `data/eposyandu.db` secara berkala untuk menyimpan
data.

---

## Data Rujukan WHO

Perhitungan status gizi memakai rumus Z-Score WHO 2006:

```
L ≠ 0 :  Z = ((X / M) ** L − 1) / (L × S)
L = 0 :  Z = ln(X / M) / S
```

dengan `X` = nilai antropometri anak, dan `L`, `M`, `S` = parameter Box-Cox
dari tabel rujukan WHO.

Data L-M-S disimpan sebagai JSON di `who_data/`, dibangun dari tabel resmi WHO
memakai `tools/build_who_data.py`. Berkas Excel sumbernya ada di
`tools/who_source/`. Indikator yang didukung: BB/U, TB/U, BB/TB, BB/PB, dan
lingkar kepala menurut umur, terpisah untuk laki-laki dan perempuan.

Modul `growth.py` juga dapat dipakai langsung dari terminal:

```
python -c "import growth; print(growth.classify('tinggi', -2.8))"
```

---

## Peran Pengguna

| Peran | Hak akses |
|---|---|
| `admin` | Seluruh fitur, termasuk manajemen pengguna dan pengaturan posyandu |
| `kader` | Data balita, pengukuran, pemantauan, prediksi, dan laporan |
| `bidan` | Sama seperti kader, dengan akses tindak lanjut hasil pemantauan |

Halaman manajemen pengguna (`/pengguna`) dan pengaturan (`/pengaturan`) hanya
dapat diakses oleh `admin`.

---

## Catatan Keamanan

Aplikasi ini ditujukan untuk **jaringan lokal / komputer sendiri**, bukan untuk
dipasang langsung di internet. Sebelum dipakai sungguhan:

1. **Ganti semua kata sandi bawaan** lewat menu Pengguna.
2. **Ganti `SECRET_KEY`.** Kunci bawaan ada di `app.py` dan sebaiknya diisi lewat
   variabel lingkungan:
   ```
   set EPOSYANDU_SECRET=kunci-rahasia-anda-sendiri
   python app.py
   ```
3. **Matikan mode debug** untuk pemakaian nyata. Mode debug membuka konsol
   interaktif yang berbahaya bila dapat diakses orang lain. Ubah baris terakhir
   `app.py` menjadi:
   ```python
   app.run(debug=False, host="127.0.0.1", port=5000)
   ```
4. **Jangan jadikan pesan galat detail** sebagai tampilan publik.
5. Untuk pemakaian bersama lewat jaringan, gunakan server WSGI produksi
   (mis. Waitress di Windows) di belakang reverse proxy, bukan server
   pengembangan Flask.

---

## Pemecahan Masalah

**"Python tidak ditemukan"**
Python belum terpasang atau belum masuk PATH. Pasang ulang dari python.org dan
centang "Add Python to PATH", lalu jalankan `run.bat` lagi.

**"Address already in use" saat menjalankan `run.bat`**
Aplikasi sudah berjalan di jendela lain. Cukup buka `http://127.0.0.1:5000`.
Untuk memulai ulang dari awal, tutup dulu jendela lama, atau hentikan prosesnya:
```
netstat -ano | findstr :5000
taskkill /PID <nomor_pid> /F
```

**Halaman gagal dimuat / tidak bisa diakses**
Pastikan jendela terminal masih terbuka dan menampilkan
`Running on http://127.0.0.1:5000`. Tutup jendela berarti server berhenti.

**Perubahan berkas tidak muncul di peramban**
Segarkan halaman dengan `Ctrl+F5` untuk membersihkan tembolok.

**Ingin mengosongkan data dan mulai dari nol**
Hapus `data/eposyandu.db`, lalu jalankan `python app.py` (basis data akan dibuat
ulang) atau `python seed.py` (dibuat ulang beserta data contoh).

---

## Lisensi & Atribusi

Data rujukan pertumbuhan bersumber dari **WHO Child Growth Standards (2006)** dan
**Standar Antropometri Anak, Kementerian Kesehatan RI (2020)**. Aplikasi ini
dikembangkan untuk keperluan Posyandu Lestari 12, Banjarnegara.
