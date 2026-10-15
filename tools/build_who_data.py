"""
Konverter tabel resmi WHO Child Growth Standards -> data L-M-S ringkas (JSON).

Sumber: WHO Child Growth Standards (2006) - expanded z-score tables.
        https://www.who.int/tools/child-growth-standards/standards
File sumber (xlsx) disimpan di tools/who_source/ dan TIDAK diubah.

Output: who_data/{indikator}_{sex}.json  berisi deret L, M, S.

Indikator:
  wfa  = Berat Badan menurut Umur  (Weight-for-age)
  lhfa = Panjang/Tinggi Badan menurut Umur (Length/Height-for-age)
  wfl  = Berat menurut Panjang Badan (Weight-for-length, 45-110 cm, <2 th)
  wfh  = Berat menurut Tinggi Badan (Weight-for-height, 65-120 cm, >=2 th)
  hcfa = Lingkar Kepala menurut Umur (Head-circumference-for-age)

Dijalankan sekali dari folder tools/:  python build_who_data.py
"""
import json
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "who_source")
OUT = os.path.join(os.path.dirname(HERE), "who_data")

# kunci output -> (nama file xlsx, nama kolom kunci, jenis sumbu)
TABLES = {
    "wfa": ("wfa", "Day", "day"),
    "lhfa": ("lhfa", "Day", "day"),
    "wfl": ("wfl", "Length", "height"),
    "wfh": ("wfh", "Height", "height"),
    "hcfa": ("hcfa", "Day", "day"),
}

SEXES = {"boys": "M", "girls": "F"}


def clean_table(path, key_col):
    """Baca satu xlsx WHO -> DataFrame berkolom key, L, M, S (float)."""
    df = pd.read_excel(path, sheet_name=0)
    df.columns = [str(c).strip() for c in df.columns]

    # WHO memakai 'Day' atau 'Length'/'Height' sebagai kolom kunci
    if key_col not in df.columns:
        candidates = [c for c in df.columns if c.lower() in
                      ("day", "length", "height", "age", "agedays")]
        if not candidates:
            raise SystemExit(f"Kolom kunci '{key_col}' tidak ditemukan di {path}. "
                             f"Kolom tersedia: {list(df.columns)}")
        key_col = candidates[0]

    for col in ("L", "M", "S"):
        if col not in df.columns:
            raise SystemExit(f"Kolom '{col}' tidak ada di {path}")

    df = df[[key_col, "L", "M", "S"]].copy()
    df.columns = ["key", "L", "M", "S"]
    df["key"] = pd.to_numeric(df["key"], errors="coerce")
    for col in ("L", "M", "S"):
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna().sort_values("key").reset_index(drop=True)
    return df, key_col


def build():
    os.makedirs(OUT, exist_ok=True)
    manifest = {}

    for indicator, (stem, key_col, axis) in TABLES.items():
        for sex_file, sex_code in SEXES.items():
            path = os.path.join(SRC, f"{stem}_{sex_file}.xlsx")
            if not os.path.exists(path):
                raise SystemExit(f"File sumber hilang: {path}")

            df, used_key = clean_table(path, key_col)

            keys = df["key"].tolist()
            # pastikan langkah seragam supaya bisa disimpan sebagai start+step
            step = round(keys[1] - keys[0], 4) if len(keys) > 1 else 1
            uniform = all(
                abs((keys[i] - keys[i - 1]) - step) < 1e-6 for i in range(1, len(keys))
            )
            if not uniform:
                raise SystemExit(f"Jarak baris tidak seragam pada {path}")

            payload = {
                "indicator": indicator,
                "sex": sex_code,
                "axis": axis,
                "key_name": used_key,
                "start": round(float(keys[0]), 4),
                "step": float(step),
                "count": len(keys),
                "L": [round(v, 6) for v in df["L"]],
                "M": [round(v, 6) for v in df["M"]],
                "S": [round(v, 6) for v in df["S"]],
            }

            out_path = os.path.join(OUT, f"{indicator}_{sex_code}.json")
            with open(out_path, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, separators=(",", ":"))

            manifest[f"{indicator}_{sex_code}"] = {
                "rows": len(keys),
                "start": payload["start"],
                "end": round(float(keys[-1]), 4),
                "step": payload["step"],
                "bytes": os.path.getsize(out_path),
            }
            print(f"  {indicator}_{sex_code:<7} baris={len(keys):>4}  "
                  f"rentang {payload['start']}..{round(float(keys[-1]), 4)}  "
                  f"step={payload['step']}")

    with open(os.path.join(OUT, "_manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
    print("\nSelesai. Data ditulis ke:", OUT)


if __name__ == "__main__":
    print("Membangun data L-M-S WHO Child Growth Standards\n")
    build()
