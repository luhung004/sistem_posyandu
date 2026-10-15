-- ===========================================================================
-- Sistem Informasi E-Posyandu Terintegrasi
-- Pemantauan dan Prediksi Dini Stunting
-- Posyandu Lestari 12, Merden, Rawawungu, Kecamatan Purwanegara, Banjarnegara
-- ---------------------------------------------------------------------------
-- Basis data: SQLite
-- ===========================================================================

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------------
-- Pengguna sistem
--   role: admin   = mengelola seluruh data & akun
--         kader   = input data balita dan hasil penimbangan
--         bidan   = memantau, memvalidasi, dan menindaklanjuti kasus
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    NOT NULL UNIQUE,
    password_hash TEXT    NOT NULL,
    nama          TEXT    NOT NULL,
    jabatan       TEXT,
    role          TEXT    NOT NULL DEFAULT 'kader'
                          CHECK (role IN ('admin', 'kader', 'bidan')),
    aktif         INTEGER NOT NULL DEFAULT 1,
    dibuat        TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- ---------------------------------------------------------------------------
-- Balita (beserta data orang tua)
--   sex: 'M' = laki-laki, 'F' = perempuan
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS balita (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    nik            TEXT,
    no_kk          TEXT,
    nama           TEXT    NOT NULL,
    sex            TEXT    NOT NULL CHECK (sex IN ('M', 'F')),
    birth_date     TEXT    NOT NULL,          -- format YYYY-MM-DD
    nama_ibu       TEXT,
    nama_ayah      TEXT,
    no_hp          TEXT,
    alamat         TEXT,
    rt             TEXT,
    rw             TEXT,
    -- data lahir
    bb_lahir       REAL,                      -- kg
    pb_lahir       REAL,                      -- cm
    asi_eksklusif  INTEGER,                   -- 1 = ya, 0 = tidak, NULL = belum diketahui
    -- faktor pendukung pemantauan
    berat_ibu_hamil REAL,
    tinggi_ibu     REAL,
    catatan        TEXT,
    aktif          INTEGER NOT NULL DEFAULT 1,
    dibuat         TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS idx_balita_nama  ON balita (nama);
CREATE INDEX IF NOT EXISTS idx_balita_aktif ON balita (aktif);

-- ---------------------------------------------------------------------------
-- Penimbangan / pengukuran bulanan
--   Z-Score disimpan hasil perhitungan WHO saat data disimpan, agar laporan
--   tidak perlu menghitung ulang dan riwayat tetap terekam apa adanya.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pengukuran (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    balita_id        INTEGER NOT NULL REFERENCES balita (id) ON DELETE CASCADE,
    tanggal          TEXT    NOT NULL,        -- YYYY-MM-DD
    umur_hari        INTEGER,                 -- umur saat diukur
    berat            REAL,                    -- kg
    tinggi           REAL,                    -- cm
    lingkar_kepala   REAL,                    -- cm
    lingkar_lengan   REAL,                    -- cm (LiLA)
    cara_ukur        TEXT    CHECK (cara_ukur IN ('berbaring', 'berdiri')),
    -- hasil perhitungan Z-Score WHO
    z_wfa            REAL,                    -- BB/U
    z_lhfa           REAL,                    -- TB/U
    z_wfh            REAL,                    -- BB/TB atau BB/PB
    z_hcfa           REAL,                    -- LK/U
    indikator_wfh    TEXT,                    -- 'wfl' atau 'wfh'
    status_gizi      TEXT,                    -- ringkasan status BB/U
    status_stunting  TEXT,                    -- normal / pendek / sangat_pendek
    catatan          TEXT,
    dicatat_oleh     INTEGER REFERENCES users (id),
    dibuat           TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (balita_id, tanggal)
);
CREATE INDEX IF NOT EXISTS idx_ukur_balita  ON pengukuran (balita_id, tanggal);
CREATE INDEX IF NOT EXISTS idx_ukur_tanggal ON pengukuran (tanggal);

-- ---------------------------------------------------------------------------
-- Riwayat tindak lanjut / intervensi kasus stunting
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tindak_lanjut (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    balita_id     INTEGER NOT NULL REFERENCES balita (id) ON DELETE CASCADE,
    pengukuran_id INTEGER REFERENCES pengukuran (id) ON DELETE SET NULL,
    tanggal       TEXT    NOT NULL,
    jenis         TEXT    NOT NULL,   -- rujukan / PMT / edukasi / kunjungan rumah
    keterangan    TEXT,
    petugas       TEXT,
    dicatat_oleh  INTEGER REFERENCES users (id),
    dibuat        TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS idx_tl_balita ON tindak_lanjut (balita_id, tanggal);

-- ---------------------------------------------------------------------------
-- Pengaturan aplikasi (mis. identitas posyandu)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pengaturan (
    kunci TEXT PRIMARY KEY,
    nilai TEXT
);
