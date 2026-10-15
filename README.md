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

Tiga akun contoh dibuat saat basis data pertama kali dibangun, **hanya jika**
variabel `EPOSYANDU_SEED=1` diset.

| Peran | Nama Pengguna | Nama | Jabatan |
|---|---|---|---|
| Administrator | `admin` | Administrator Sistem | Pengelola Sistem |
| Kader Posyandu | `kader` | Sri Wahyuni | Kader Posyandu |
| Bidan Desa | `bidan` | Rina Puspitasari, A.Md.Keb | Bidan Desa |

**Kata sandinya acak dan dibuat berbeda setiap kali**, lalu disimpan di:

```
data/demo-credentials.txt
```

Berkas itu tidak ikut terunggah ke repositori. Buka untuk melihat kata sandi
ketiganya.

> **Kenapa tidak memakai `admin123`?**
> Nilai yang tertanam di kode bisa ditebak siapa saja. Pada server yang sedang
> daring, akun admin cukup dihantam dengan beberapa kombinasi umum. Karena itu
> kata sandi tidak pernah ditulis di kode maupun ditampilkan di halaman login.

---

## Variabel Lingkungan

Aplikasi menolak berjalan bila `EPOSYANDU_SECRET` belum diset.

| Variabel | Wajib | Kegunaan |
|---|---|---|
| `EPOSYANDU_SECRET` | ya | Menandatangani cookie sesi. Buat dengan `python -c "import secrets; print(secrets.token_hex(32))"` |
| `EPOSYANDU_SEED` | tidak | Isi `1` untuk membuat basis data beserta data contoh |
| `EPOSYANDU_HTTPS` | tidak | `0` untuk pemakaian lokal lewat http, `1` di server (bawaan) |
| `TZ` | disarankan | Isi `Asia/Jakarta` agar tanggal dan umur balita benar |
| `PORT` | tidak | Port server; biasanya diisi otomatis oleh platform |

> Data pribadi anak (NIK, nomor KK, alamat) dilindungi **UU PDP No. 27/2022**.
> Jangan menaruh data nyata di server publik tanpa persetujuan orang tua/wali
> dan tanpa pembatasan akses yang memadai.

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

Aplikasi ini bisa dijalankan di jaringan lokal maupun di server. Untuk pemakaian
sungguhan, perhatikan hal-hal berikut.

### Sudah ditangani di kode

||Ancaman |Penangan|
|---|---|
|Sesi dipalsukan |`SECRET_KEY` hanya dibaca dari `EPOSYANDU_SECRET`. Tidak ada nilai cadangan di kode, jadi aplikasi **menolak berjalan** bila variabel ini kosong.|
|Konsol Python terbuka |Mode debug mati secara bawaan. Hanya aktif bila `FLASK_DEBUG=1` diset.|
|Permintaan dari situs lain |Setiap POST harus membawa token CSRF milik sesinya sendiri; tanpa itu ditolak `400`.|
|Perkiraan kata sandi |Kata sandi dibatasi 5 percobaan gagal per nama pengguna, lalu dikunci 15 menit.|
|Penyamaran halaman |Header `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, dan HSTS.|
|Kebocoran lewat HTTP |Cookie sesi memakai flag `Secure` dan `HttpOnly`.|

### Sebelum diisi data nyata

1. **Ganti seluruh kata sandi** lewat menu Pengguna.
2. **Pastikan `EPOSYANDU_SECRET` dibuat acak** untuk setiap server:
   ```
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
3. **Set `TZ=Asia/Jakarta`.** Tanpa itu, antara pukul 17.00-24.00 WIB tanggal
   dan umur balita bisa terhitung salah satu hari karena server memakai UTC.
4. **Sediakan cadangan data.** Berkas `data/eposyandu.db` adalah satu-satunya
   salinan.Tidak ada mekanisme pencadangan otomatis.
5. **Tinjau hak akses.**
   `/laporan/export.csv` dan `/laporan/cetak` bisa diakses semua peran, termasuk
   `kader`. Persempit bila mengizinkan data nyata.
6. **`pengukuran/<id>/hapus`** hanya butuh peran apa pun, tidak seperti
   `balita/<id>/hapus` yang khusus admin.

### Menjalankan di server

Jangan pernah menjalankan `python app.py` di server. Gunakan WSGI:

```bash
# Linux / PaaS
gunicorn --bind 0.0.0.0:$PORT wsgi:application

# Windows
waitress-serve --host=0.0.0.0 --port=$PORT wsgi:application
```

Basis data dan tabel dibuat otomatis oleh `wsgi.py` saat server mulai.

> **Penting: SQLite perlu penyimpanan yang bertahan.** Pada platform hosting
> dengan sistem berkas sementara (sebagian besar paket gratis), `data/`
> akan hilang setiap kali server dimulai ulang atau diperbarui. Paket
> berbayar dengan persistent disk diperlukan, atau pindahkan ke PostgreSQL.

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
