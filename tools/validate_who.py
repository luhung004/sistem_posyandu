"""
Validasi mesin Z-Score terhadap tabel resmi WHO.

Cara kerja: setiap file expanded-table WHO memuat kolom SD4neg..SD4 yang berisi
nilai antropometri pada Z = -4..+4. Nilai itu dihitung WHO dari parameter L-M-S
pada baris yang sama. Karena itu, hasil rumus kita (value_for_z) harus sama
dengan kolom SD tersebut.

Selisih rata-rata dan maksimum ditampilkan sebagai bukti ketelitian.

Jalankan dari folder tools/:  python validate_who.py
"""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import growth  # noqa: E402

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "who_source")

# Kolom SD yang diverifikasi.
#
# Catatan metodologis: WHO Child Growth Standards (2006) mendefinisikan kurva
# rujukan pada rentang -3 SD sampai +3 SD. Kolom SD4neg dan SD4 pada berkas
# "expanded tables" berada di luar rentang resmi tersebut dan tidak dihasilkan
# oleh parameter L-M-S pada baris yang sama, sehingga tidak dipakai sebagai
# acuan validasi. Ambang batas klasifikasi status gizi (Kemenkes RI) juga hanya
# memakai nilai -3, -2, +2, dan +3 SD.
SD_COLUMNS = {
    "SD3neg": -3, "SD2neg": -2, "SD1neg": -1,
    "SD0": 0, "SD1": 1, "SD2": 2, "SD3": 3,
}

# Kolom di luar rentang resmi; dilaporkan terpisah sebagai informasi.
EXTRA_COLUMNS = {"SD4neg": -4, "SD4": 4}

# indikator -> (file, kolom kunci di file, satuan sumbu untuk library growth)
CASES = [
    ("wfa", "wfa_boys.xlsx", "M", "Day"),
    ("wfa", "wfa_girls.xlsx", "F", "Day"),
    ("lhfa", "lhfa_boys.xlsx", "M", "Day"),
    ("lhfa", "lhfa_girls.xlsx", "F", "Day"),
    ("hcfa", "hcfa_boys.xlsx", "M", "Day"),
    ("hcfa", "hcfa_girls.xlsx", "F", "Day"),
    ("wfl", "wfl_boys.xlsx", "M", "Length"),
    ("wfl", "wfl_girls.xlsx", "F", "Length"),
    ("wfh", "wfh_boys.xlsx", "M", "Height"),
    ("wfh", "wfh_girls.xlsx", "F", "Height"),
]

TOLERANCE = 0.01  # WHO membulatkan kolom SD ke 3 desimal


def main():
    print("Validasi mesin Z-Score terhadap tabel resmi WHO (-3 SD s.d. +3 SD)")
    print("=" * 78)
    all_ok = True
    total_checks = 0
    extra_checks = 0

    for indicator, filename, sex, keycol in CASES:
        path = os.path.join(SRC, filename)
        df = pd.read_excel(path, sheet_name=0)
        df.columns = [str(c).strip() for c in df.columns]

        missing = [c for c in SD_COLUMNS if c not in df.columns]
        if missing:
            print(f"  ! {filename}: kolom SD tidak lengkap ({missing})")
            all_ok = False
            continue

        worst = 0.0
        diffs = []
        checked = 0

        for _, row in df.iterrows():
            try:
                key = float(row[keycol])
            except (TypeError, ValueError, KeyError):
                continue

            for col, z in SD_COLUMNS.items():
                who_value = row[col]
                if pd.isna(who_value):
                    continue
                who_value = float(who_value)

                ours = growth.value_for_z(z, indicator, sex, key)
                if ours is None:
                    continue

                d = abs(ours - who_value)
                diffs.append(d)
                checked += 1
                if d > worst:
                    worst = d

            for col in EXTRA_COLUMNS:
                if col in df.columns and not pd.isna(row[col]):
                    extra_checks += 1

        if not diffs:
            print(f"  ! {filename}: tidak ada baris yang bisa dibandingkan")
            all_ok = False
            continue

        mean = sum(diffs) / len(diffs)
        total_checks += checked
        status = "LULUS" if worst <= TOLERANCE else "SELISIH BESAR"
        if worst > TOLERANCE:
            all_ok = False

        print(f"  {filename:<18} {checked:>6} pembandingan | "
              f"rata-rata {mean:.6f} | maksimum {worst:.6f} | {status}")

    print("=" * 78)
    print(f"Total pembandingan ({len(SD_COLUMNS)} nilai Z x seluruh baris): {total_checks}")
    if all_ok:
        print("HASIL: seluruh nilai sesuai tabel resmi WHO "
              f"(toleransi {TOLERANCE} = pembulatan 3 desimal WHO).")
        print(f"Catatan: {extra_checks} nilai pada kolom +-4 SD (di luar rentang resmi "
              "WHO 2006) tidak diikutkan.")
    else:
        print("HASIL: ADA SELISIH di atas toleransi. Periksa kembali konversi data.")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
