"""VoltPilih, komponen BASIS MODEL: Fuzzy Mamdani.
Tidak bergantung pada Streamlit. Setiap langkah mengembalikan jejak (rumus, substitusi angka, hasil)
supaya asal-usul tiap angka bisa ditelusuri."""
import numpy as np

from data import BAD, GOOD, K, LABEL, NAMA, RULES_TXT, SATUAN, TITIK

DY = 0.01
Y = np.linspace(0, 100, 10001)  # resolusi 0,01 pada [0, 100]
OUT = {"kurang": (0, 0, 50), "cocok": (25, 50, 75), "sangat": (50, 100, 100)}
NAMA_OUT = {"kurang": "kurang cocok", "cocok": "cocok", "sangat": "sangat cocok"}
B_SANGAT, B_COCOK = 200 / 3, 100 / 3
BOBOT_LEMAH = 0.7


def num(x, d=3):
    """Angka berformat Indonesia (koma desimal), nol di belakang dibuang."""
    s = f"{float(x):.{d}f}"
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s.replace(".", ",")


# ---------------- himpunan fuzzy ----------------
def himpunan(v, titik):
    lo, mid, hi = titik
    a, b, c = LABEL[v]
    return {a: (lo, lo, mid), b: (lo, mid, hi), c: (mid, hi, hi)}


def semua_himpunan(titik=None):
    titik = titik or TITIK
    return {v: himpunan(v, titik[v]) for v in K}


def mf(x, p):
    """Keanggotaan segitiga. Himpunan di ujung (a==b atau b==c) berperan sebagai bahu."""
    a, b, c = p
    x = np.asarray(x, dtype=float)
    kiri = np.ones_like(x) if a == b else np.clip((x - a) / (b - a), 0, 1)
    kanan = np.ones_like(x) if b == c else np.clip((c - x) / (c - b), 0, 1)
    return np.where(x <= b, kiri, kanan)


def mf_jejak(x, p):
    """Mengembalikan (rumus, substitusi angka, nilai μ) untuk satu himpunan."""
    a, b, c = p
    if a == b:  # bahu kiri
        if x <= b:
            return "1 bila x ≤ b", f"x = {num(x)} ≤ {num(b)}", 1.0
        if x >= c:
            return "0 bila x ≥ c", f"x = {num(x)} ≥ {num(c)}", 0.0
        return "(c − x) / (c − b)", f"({num(c)} − {num(x)}) / ({num(c)} − {num(b)})", (c - x) / (c - b)
    if b == c:  # bahu kanan
        if x >= b:
            return "1 bila x ≥ b", f"x = {num(x)} ≥ {num(b)}", 1.0
        if x <= a:
            return "0 bila x ≤ a", f"x = {num(x)} ≤ {num(a)}", 0.0
        return "(x − a) / (b − a)", f"({num(x)} − {num(a)}) / ({num(b)} − {num(a)})", (x - a) / (b - a)
    if x <= a or x >= c:
        return "0 di luar (a, c)", f"x = {num(x)} di luar ({num(a)}; {num(c)})", 0.0
    if x <= b:
        return "(x − a) / (b − a)", f"({num(x)} − {num(a)}) / ({num(b)} − {num(a)})", (x - a) / (b - a)
    return "(c − x) / (c − b)", f"({num(c)} − {num(x)}) / ({num(c)} − {num(b)})", (c - x) / (c - b)


def fuzzifikasi(c, S):
    return {v: {s: float(mf(c[v], p)) for s, p in S[v].items()} for v in K}


def di_luar(c, titik):
    """Nilai di luar rentang himpunan. Keanggotaannya sama dengan nilai di batas (bahu)."""
    hasil = []
    for v in K:
        lo, _, hi = titik[v]
        if c[v] < lo or c[v] > hi:
            hasil.append(f"{NAMA[v].lower()} {num(c[v])} {SATUAN[v]} di luar rentang {num(lo)} sampai {num(hi)}".replace("  ", " "))
    return hasil


# ---------------- aturan ----------------
def parse_aturan(no, txt, out, kustom=False):
    groups = [[tuple(q.split(".")) for q in g.replace("(", "").replace(")", "").split("|")] for g in txt.split("&")]
    return {"no": no, "txt": txt, "out": out, "groups": groups, "kustom": kustom}


ATURAN0 = [parse_aturan(i + 1, t, "sangat" if i < 8 else "cocok" if i < 20 else "kurang") for i, t in enumerate(RULES_TXT)]


def siapkan_aturan(rules, aktif=None, off=()):
    """Buang aturan nonaktif. Syarat pada kriteria yang diabaikan (off) dihapus dari aturan."""
    hasil = []
    for a in rules:
        if aktif is not None and not aktif.get(a["no"], True):
            continue
        gs = [[(v, s) for v, s in g if v not in off] for g in a["groups"]]
        gs = [g for g in gs if g]
        if gs:
            hasil.append({**a, "groups": gs})
    return hasil


def teks_aturan(groups):
    bag = []
    for g in groups:
        t = " atau ".join(f"{NAMA[v].lower()} {s}" for v, s in g)
        bag.append(f"({t})" if len(g) > 1 else t)
    return " dan ".join(bag)


def bobot_aturan(groups, prio, lemah):
    """w = 1 bila aturan memuat kriteria 'Penting', selain itu 'lemah' (0,7). Tanpa kriteria penting: semua 1."""
    if not prio:
        return 1.0
    return 1.0 if {v for g in groups for v, _ in g} & set(prio) else lemah


def evaluasi(F, groups):
    nilai, bag = [], []
    for g in groups:
        vs = [F[v][s] for v, s in g]
        nilai.append(max(vs))
        bag.append(num(vs[0]) if len(vs) == 1 else "maks(" + "; ".join(num(x) for x in vs) + ")")
    jejak = bag[0] if len(bag) == 1 else "min(" + "; ".join(bag) + ")"
    return min(nilai), jejak


# ---------------- Mamdani ----------------
def infer(c, cfg):
    F = fuzzifikasi(c, cfg["S"])
    agg = {k: 0.0 for k in OUT}
    aktif = []
    for a in cfg["aturan"]:
        lam, jejak = evaluasi(F, a["groups"])
        w = bobot_aturan(a["groups"], cfg["prio"], cfg["lemah"])
        lamp = lam * w  # λ' = w × λ
        agg[a["out"]] = max(agg[a["out"]], lamp)
        aktif.append({"no": a["no"], "txt": teks_aturan(a["groups"]), "out": a["out"], "lam": lam, "w": w, "lamp": lamp, "jejak": jejak})
    mu = np.max([np.minimum(agg[k], mf(Y, OUT[k])) for k in OUT], axis=0)
    luas = float(mu.sum() * DY)
    momen = float((Y * mu).sum() * DY)
    skor = momen / luas if luas > 0 else 50.0
    return {"c": c, "F": F, "aktif": aktif, "agg": agg, "mu": mu, "skor": skor, "luas": luas, "momen": momen}


def hitung(db, cfg):
    """Skor Mamdani untuk semua mobil di db."""
    if db.empty:
        return []
    return [infer(c, cfg) for c in db.to_dict("records")]


def peringkat(rs, kunci="skor", desimal=4):
    """Peringkat kompetisi (1,2,2,4)."""
    v = [round(x[kunci], desimal) for x in rs]
    return [1 + sum(1 for y in v if y > a) for a in v]


# ---------------- teks penjelas ----------------
def dominan(F, v):
    return max(F[v].items(), key=lambda x: x[1])[0]


def alasan(r):
    unggul, kurang = [], []
    for v in K:
        s = dominan(r["F"], v)
        (unggul if s in GOOD else kurang if s in BAD else []).append(f"{NAMA[v].lower()} {s}")
    return unggul, kurang


def kalimat(r):
    u, k = alasan(r)
    t = "karena " + (", ".join(u) if u else "tidak ada kriteria yang menonjol")
    if k:
        t += f". Kekurangannya: {', '.join(k)}"
    return t + "."


def penilaian(s):
    return "🟢 Sangat cocok" if s > B_SANGAT else "🟡 Cocok" if s >= B_COCOK else "🔴 Kurang cocok"


def rp(n):
    return f"Rp{n/1000:.2f} miliar".replace(".", ",") if n >= 1000 else f"Rp{n:.0f} juta"


def nilai_teks(c, v):
    return rp(c[v]) if v == "h" else f"{num(c[v])} {SATUAN[v]}".strip()


def aturan_terkuat(r, n=2):
    return [a for a in sorted(r["aktif"], key=lambda a: -a["lamp"])[:n] if a["lamp"] > 0]
