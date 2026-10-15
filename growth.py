"""
Mesin perhitungan status gizi anak berbasis WHO Child Growth Standards (2006).

Rumus Z-Score (WHO, 2006 - Child Growth Standards, Technical Report):
    L != 0 :  Z = ((X / M) ** L - 1) / (L * S)
    L == 0 :  Z = ln(X / M) / S

dengan X = nilai antropometri anak, dan L, M, S = parameter Box-Cox
(Lambda, Median, Coefficient of Variation) dari tabel rujukan WHO.

Referensi:
  [1] WHO Multicentre Growth Reference Study Group (2006). WHO Child Growth
      Standards: Length/height-for-age, weight-for-age, weight-for-length,
      weight-for-height and body mass index-for-age. Geneva: WHO.
  [2] Kementerian Kesehatan RI (2020). Standar Antropometri Anak
      (Keputusan Menteri Kesehatan RI Nomor HK.01.07/MENKES/1990/2016).
  [3] WHO (2009). WHO Anthro and macros. Geneva: WHO.

Data L-M-S dibaca dari berkas JSON di folder who_data/ yang dibangun dari
tabel resmi WHO (lihat tools/build_who_data.py).
"""
import json
import os
from datetime import date

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "who_data")

# ---------------------------------------------------------------------------
# Metadata indikator
# ---------------------------------------------------------------------------
# axis: 'day' = sumbu umur (hari), 'height' = sumbu panjang/tinggi badan (cm)
INDICATORS = {
    "wfa": {
        "label": "Berat Badan menurut Umur",
        "short": "BB/U",
        "unit": "kg",
        "axis": "day",
        "plausible": (-6.0, 5.0),
    },
    "lhfa": {
        "label": "Panjang/Tinggi Badan menurut Umur",
        "short": "TB/U",
        "unit": "cm",
        "axis": "day",
        "plausible": (-6.0, 6.0),
    },
    "wfl": {
        "label": "Berat Badan menurut Panjang Badan",
        "short": "BB/PB",
        "unit": "kg",
        "axis": "height",
        "plausible": (-5.0, 5.0),
    },
    "wfh": {
        "label": "Berat Badan menurut Tinggi Badan",
        "short": "BB/TB",
        "unit": "kg",
        "axis": "height",
        "plausible": (-5.0, 5.0),
    },
    "hcfa": {
        "label": "Lingkar Kepala menurut Umur",
        "short": "LK/U",
        "unit": "cm",
        "axis": "day",
        "plausible": (-5.0, 5.0),
    },
}

# Batas usia tabel umur (hari) dan tabel tinggi badan (cm)
MAX_AGE_DAYS = 1856          # 5 tahun (60 bulan)
MIN_HEIGHT_CM, MAX_HEIGHT_CM = 45.0, 120.0

_cache = {}


# ---------------------------------------------------------------------------
# Pemuatan data
# ---------------------------------------------------------------------------
def _load(indicator, sex):
    key = (indicator, sex)
    if key not in _cache:
        path = os.path.join(DATA_DIR, f"{indicator}_{sex}.json")
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"Data rujukan WHO tidak ditemukan: {path}. "
                "Jalankan 'python tools/build_who_data.py' terlebih dahulu."
            )
        with open(path, "r", encoding="utf-8") as fh:
            _cache[key] = json.load(fh)
    return _cache[key]


def normalize_sex(sex):
    """Terima 'L'/'P'/'M'/'F'/'laki-laki'/'perempuan' -> 'M' atau 'F'."""
    if sex is None:
        raise ValueError("Jenis kelamin wajib diisi.")
    s = str(sex).strip().lower()
    if s in ("m", "l", "lk", "laki-laki", "laki laki", "male", "boys", "boy"):
        return "M"
    if s in ("f", "p", "pr", "perempuan", "female", "girls", "girl"):
        return "F"
    raise ValueError(f"Jenis kelamin tidak dikenali: {sex!r}")


def _nearest_index(table, key):
    """Indeks baris terdekat pada grid seragam (start + i*step)."""
    idx = (float(key) - table["start"]) / table["step"]
    i = int(round(idx))
    if i < 0 or i >= table["count"]:
        return None
    return i


def lms(indicator, sex, key):
    """
    Ambil parameter (L, M, S) pada titik `key`
    (umur dalam hari untuk axis 'day', tinggi badan cm untuk axis 'height').

    Mengembalikan (L, M, S) atau None bila di luar rentang tabel.
    """
    if indicator not in INDICATORS:
        raise ValueError(f"Indikator tidak dikenal: {indicator}")
    table = _load(indicator, normalize_sex(sex))
    i = _nearest_index(table, key)
    if i is None:
        return None
    return table["L"][i], table["M"][i], table["S"][i]


def lms_at_index(indicator, sex, i):
    table = _load(indicator, normalize_sex(sex))
    if i < 0 or i >= table["count"]:
        return None
    return table["L"][i], table["M"][i], table["S"][i], table["start"] + i * table["step"]


# ---------------------------------------------------------------------------
# Konversi Z-Score dan kebalikannya
# ---------------------------------------------------------------------------
def zscore(value, indicator, sex, key):
    """
    Hitung Z-Score. Mengembalikan float, atau None bila data tidak tersedia
    (di luar rentang tabel atau nilai tidak valid).
    """
    if value is None or key is None:
        return None
    try:
        value = float(value)
        key = float(key)
    except (TypeError, ValueError):
        return None
    if value <= 0:
        return None

    params = lms(indicator, sex, key)
    if params is None:
        return None
    L, M, S = params
    if M is None or S in (None, 0):
        return None

    if abs(L) < 1e-9:
        return _safe_log(value / M) / S
    return (((value / M) ** L) - 1.0) / (L * S)


def _safe_log(x):
    import math
    if x <= 0:
        return None
    return math.log(x)


def value_for_z(z, indicator, sex, key):
    """Kebalikan: nilai antropometri pada Z-Score tertentu (untuk kurva rujukan)."""
    params = lms(indicator, sex, key)
    if params is None:
        return None
    L, M, S = params
    if abs(L) < 1e-9:
        import math
        return M * math.exp(S * z)
    base = 1.0 + L * S * z
    if base <= 0:
        return None
    return M * (base ** (1.0 / L))


def is_plausible(z, indicator):
    """Saring Z-Score di luar batas wajar WHO (indikasi salah ukur/input)."""
    if z is None:
        return False
    lo, hi = INDICATORS[indicator]["plausible"]
    return lo <= z <= hi


# ---------------------------------------------------------------------------
# Klasifikasi status gizi (ambang batas Kemenkes RI / WHO)
# ---------------------------------------------------------------------------
# Setiap indikator -> daftar (batas_atas, kode, label, tingkat)
# 'tingkat' dipakai untuk pewarnaan antarmuka.
CLASSIFICATION = {
    "wfa": [
        (-3.0, "sangat_kurang", "Berat badan sangat kurang", "bahaya"),
        (-2.0, "kurang", "Berat badan kurang", "waspada"),
        (2.0, "normal", "Berat badan normal", "normal"),
        (float("inf"), "lebih", "Risiko berat badan lebih", "waspada"),
    ],
    "lhfa": [
        (-3.0, "sangat_pendek", "Sangat pendek (severely stunted)", "bahaya"),
        (-2.0, "pendek", "Pendek (stunted)", "bahaya"),
        (3.0, "normal", "Normal", "normal"),
        (float("inf"), "tinggi", "Tinggi", "normal"),
    ],
    "wfl": None,   # diisi di bawah (sama dengan wfh)
    "wfh": [
        (-3.0, "gizi_buruk", "Gizi buruk (severely wasted)", "bahaya"),
        (-2.0, "gizi_kurang", "Gizi kurang (wasted)", "waspada"),
        (2.0, "gizi_baik", "Gizi baik", "normal"),
        (3.0, "gizi_lebih", "Gizi lebih (overweight)", "waspada"),
        (float("inf"), "obesitas", "Obesitas", "bahaya"),
    ],
    "hcfa": [
        (-2.0, "mikrosefali", "Mikrosefali", "bahaya"),
        (2.0, "normal", "Normal", "normal"),
        (float("inf"), "makrosefali", "Makrosefali", "waspada"),
    ],
}
CLASSIFICATION["wfl"] = CLASSIFICATION["wfh"]


def classify(indicator, z):
    """Kembalikan dict status gizi untuk sebuah Z-Score."""
    if z is None:
        return {
            "code": "tidak_diketahui",
            "label": "Data belum lengkap",
            "level": "netral",
        }
    for batas, code, label, level in CLASSIFICATION[indicator]:
        if z < batas:
            return {"code": code, "label": label, "level": level}
    return {"code": "tidak_diketahui", "label": "Tidak diketahui", "level": "netral"}


# ---------------------------------------------------------------------------
# Utilitas umur
# ---------------------------------------------------------------------------
def parse_date(value):
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def age_in_days(birth_date, measured_date):
    b, m = parse_date(birth_date), parse_date(measured_date)
    if b is None or m is None:
        return None
    return (m - b).days


def age_text(days):
    """Ubah umur dalam hari menjadi teks Indonesia, mis. '1 tahun 3 bulan'."""
    if days is None:
        return "-"
    if days < 0:
        return "belum lahir"
    years, rem = divmod(days, 365)
    months = rem // 30
    if years and months:
        return f"{years} tahun {months} bulan"
    if years:
        return f"{years} tahun"
    if months:
        return f"{months} bulan"
    return f"{days} hari"


# ---------------------------------------------------------------------------
# Penilaian lengkap
# ---------------------------------------------------------------------------
def _choose_weight_height_indicator(age_days, measured_lying=None):
    """
    Pilih tabel BB/PB atau BB/TB.
    Anak < 24 bulan diukur berbaring (panjang) -> BB/PB.
    Anak >= 24 bulan diukur berdiri (tinggi) -> BB/TB.
    """
    if measured_lying is not None:
        return "wfl" if measured_lying else "wfh"
    if age_days is not None and age_days < 730:
        return "wfl"
    return "wfh"


def assess(*, sex, birth_date, measured_date=None, weight=None, height=None,
           head_circumference=None, measured_lying=None):
    """
    Penilaian status gizi lengkap seorang anak.

    Mengembalikan dict:
      age_days, age_text, results (per indikator), stunting, warnings
    """
    measured_date = parse_date(measured_date) or date.today()
    age_days = age_in_days(birth_date, measured_date)

    out = {
        "sex": normalize_sex(sex),
        "birth_date": str(parse_date(birth_date)) if parse_date(birth_date) else None,
        "measured_date": str(measured_date),
        "age_days": age_days,
        "age_text": age_text(age_days),
        "results": {},
        "warnings": [],
    }

    def add(indicator, value, key, key_label):
        if value is None or key is None:
            return
        z = zscore(value, indicator, sex, key)
        if z is None:
            out["warnings"].append(
                f"{INDICATORS[indicator]['short']}: nilai di luar rentang tabel rujukan WHO."
            )
            return
        zr = round(z, 2)
        plausible = is_plausible(zr, indicator)
        if not plausible:
            out["warnings"].append(
                f"{INDICATORS[indicator]['short']}: Z-Score {zr:+.2f} di luar batas wajar "
                "WHO. Periksa kembali hasil pengukuran."
            )
        out["results"][indicator] = {
            "indicator": indicator,
            "label": INDICATORS[indicator]["label"],
            "short": INDICATORS[indicator]["short"],
            "value": float(value),
            "key": float(key),
            "key_label": key_label,
            "z": zr,
            "z_raw": z,
            "status": classify(indicator, zr),
            "plausible": plausible,
        }

    # BB/U dan TB/U dan LK/U memakai sumbu umur
    if age_days is not None and 0 <= age_days <= MAX_AGE_DAYS:
        if weight is not None:
            add("wfa", weight, age_days, f"{age_days} hari")
        if height is not None:
            add("lhfa", height, age_days, f"{age_days} hari")
        if head_circumference is not None:
            add("hcfa", head_circumference, age_days, f"{age_days} hari")
    elif age_days is not None:
        out["warnings"].append(
            "Umur di luar rentang tabel rujukan WHO (0-5 tahun / 1856 hari), "
            "sehingga BB/U, TB/U, dan LK/U tidak dapat dihitung."
        )

    # BB/PB atau BB/TB memakai sumbu tinggi badan
    if weight is not None and height is not None:
        ind = _choose_weight_height_indicator(age_days, measured_lying)
        if MIN_HEIGHT_CM <= float(height) <= MAX_HEIGHT_CM:
            add(ind, weight, height, f"{height} cm")
        else:
            out["warnings"].append(
                f"{INDICATORS[ind]['short']}: panjang/tinggi badan harus antara "
                f"{MIN_HEIGHT_CM:.0f}-{MAX_HEIGHT_CM:.0f} cm."
            )

    # Kesimpulan stunting diambil dari indikator TB/U (definisi WHO)
    lhfa = out["results"].get("lhfa")
    if lhfa:
        code = lhfa["status"]["code"]
        out["stunting"] = {
            "status": code,
            "label": lhfa["status"]["label"],
            "level": lhfa["status"]["level"],
            "z": lhfa["z"],
            "stunted": code in ("pendek", "sangat_pendek"),
        }
    else:
        out["stunting"] = {
            "status": "tidak_diketahui",
            "label": "Tidak dapat dinilai",
            "level": "netral",
            "z": None,
            "stunted": None,
        }

    return out


# ---------------------------------------------------------------------------
# Kurva rujukan (untuk grafik KMS digital)
# ---------------------------------------------------------------------------
REFERENCE_Z_LINES = (-3, -2, -1, 0, 1, 2, 3)


def reference_curve(indicator, sex, key_from, key_to, z_lines=REFERENCE_Z_LINES):
    """
    Deret nilai rujukan WHO untuk menggambar kurva pertumbuhan.
    Mengembalikan dict {z: [[key, value], ...]}.
    """
    axis = INDICATORS[indicator]["axis"]
    step = 1.0 if axis == "day" else 0.5
    if axis == "day":
        step = 7.0  # satu titik per minggu cukup untuk tampilan

    out = {z: [] for z in z_lines}
    key = float(key_from)
    while key <= float(key_to):
        for z in z_lines:
            v = value_for_z(z, indicator, sex, key)
            if v is not None:
                out[z].append([round(key, 2), round(v, 3)])
        key += step
    return out


def growth_curve(indicator, sex, key_from, key_to):
    """Kurva median (Z=0) plus batas -2 SD dan -3 SD."""
    return reference_curve(indicator, sex, key_from, key_to, z_lines=(-3, -2, 0, 2, 3))


def table_span(indicator, sex):
    """Rentang tabel rujukan: (mulai, akhir, langkah, satuan sumbu)."""
    t = _load(indicator, normalize_sex(sex))
    return t["start"], round(t["start"] + (t["count"] - 1) * t["step"], 2), t["step"], t["axis"]


# ---------------------------------------------------------------------------
# Tren pertumbuhan (dasar peringatan dini berbasis Z-Score)
# ---------------------------------------------------------------------------
def trend_from_history(history, indicator="lhfa"):
    """
    Analisis tren Z-Score dari riwayat pengukuran.
    `history` = daftar dict {measured_date, z} terurut lama -> baru.
    Mengembalikan dict {delta_per_bulan, arah, label, level}.
    """
    points = [h for h in history if h.get("z") is not None and h.get("measured_date")]
    if len(points) < 2:
        return {
            "delta_per_bulan": None,
            "arah": "tidak_cukup_data",
            "label": "Riwayat belum cukup",
            "level": "netral",
        }

    first, last = points[0], points[-1]
    d0, d1 = parse_date(first["measured_date"]), parse_date(last["measured_date"])
    days = (d1 - d0).days
    if days <= 0:
        return {
            "delta_per_bulan": None,
            "arah": "tidak_cukup_data",
            "label": "Riwayat belum cukup",
            "level": "netral",
        }

    delta = last["z"] - first["z"]
    per_month = delta / (days / 30.44)

    if delta <= -0.5:
        arah, label, level = ("menurun", "Tren menurun", "bahaya")
    elif delta <= -0.2:
        arah, label, level = ("menurun_ringan", "Cenderung menurun", "waspada")
    elif delta >= 0.2:
        arah, label, level = ("membaik", "Tren membaik", "normal")
    else:
        arah, label, level = ("stabil", "Tren stabil", "normal")

    return {
        "delta_per_bulan": round(per_month, 3),
        "delta_total": round(delta, 2),
        "rentang_hari": days,
        "arah": arah,
        "label": label,
        "level": level,
    }


def early_warning(assessment, history=None):
    """
    Peringatan dini stunting berbasis ambang Z-Score WHO (tanpa model ML).

    Aturan:
      1. TB/U < -2 SD                        -> sudah stunting
      2. -2 SD <= TB/U < -1.5 SD             -> berisiko, perlu pendampingan
      3. Tren Z-Score TB/U turun >= 0.5 SD   -> waspada penurunan
      4. BB/TB < -2 SD atau BB/U < -2 SD     -> gizi kurang (faktor risiko)
    """
    flags = []
    st = assessment.get("stunting", {})
    z = st.get("z")

    if z is not None:
        if z < -2:
            flags.append({
                "kode": "stunting",
                "label": "Terdeteksi stunting",
                "pesan": f"TB/U {z:+.2f} SD (di bawah -2 SD). Rujuk ke puskesmas "
                         "untuk pemeriksaan dan intervensi gizi.",
                "level": "bahaya",
            })
        elif z < -1.5:
            flags.append({
                "kode": "risiko_stunting",
                "label": "Berisiko stunting",
                "pesan": f"TB/U {z:+.2f} SD (mendekati -2 SD). Beri PMT, "
                         "pantau tiap bulan, dan edukasi gizi ibu.",
                "level": "waspada",
            })
        else:
            flags.append({
                "kode": "normal",
                "label": "Pertumbuhan tinggi badan normal",
                "pesan": f"TB/U {z:+.2f} SD. Pertahankan pemberian ASI/MP-ASI "
                         "bergizi dan pemantauan rutin.",
                "level": "normal",
            })

    if history:
        trend = trend_from_history(history, "lhfa")
        if trend["arah"] in ("menurun",):
            flags.append({
                "kode": "tren_menurun",
                "label": "Tren tinggi badan menurun",
                "pesan": f"Z-Score TB/U turun {abs(trend['delta_total']):.2f} SD "
                         f"dalam {trend['rentang_hari']} hari. Waspadai risiko stunting.",
                "level": "bahaya",
            })
        elif trend["arah"] == "menurun_ringan":
            flags.append({
                "kode": "tren_menurun_ringan",
                "label": "Tren tinggi badan cenderung menurun",
                "pesan": f"Z-Score TB/U turun {abs(trend['delta_total']):.2f} SD. "
                         "Perlu pemantauan lebih ketat.",
                "level": "waspada",
            })
        assessment["trend"] = trend

    res = assessment.get("results", {})
    for ind, kode, pesan in (
        ("wfh", "gizi_kurang", "Berat badan menurut tinggi badan di bawah standar."),
        ("wfl", "gizi_kurang", "Berat badan menurut panjang badan di bawah standar."),
        ("wfa", "kurang", "Berat badan menurut umur di bawah standar."),
    ):
        r = res.get(ind)
        if r and r["status"]["code"] in ("gizi_kurang", "gizi_buruk", "kurang", "sangat_kurang"):
            flags.append({
                "kode": f"{ind}_kurang",
                "label": f"{r['short']} kurang",
                "pesan": f"{r['short']} {r['z']:+.2f} SD. {pesan}",
                "level": r["status"]["level"],
            })

    assessment["flags"] = flags
    # tingkat risiko keseluruhan
    order = {"bahaya": 3, "waspada": 2, "normal": 1, "netral": 0}
    lvl = max((order.get(f["level"], 0) for f in flags), default=0)
    assessment["risk_level"] = {3: "bahaya", 2: "waspada", 1: "normal", 0: "netral"}[lvl]
    return assessment
