"""VoltPilih: aplikasi pemilihan mobil listrik dengan logika fuzzy (Mamdani).
Jalankan: streamlit run app.py
Berkas: data.py (data dan aturan), model.py (perhitungan), app.py (tampilan)."""
import html
import io
import json

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import data as D
import model as M

K = D.K
st.set_page_config(page_title="VoltPilih - Pilih Mobil Listrik", page_icon="⚡", layout="wide")
st.markdown("""<style>
.kartu{border:1px solid rgba(128,128,128,.3);border-radius:14px;padding:14px 16px;height:100%}
.kartu h3{margin:.2rem 0;font-size:1.15rem}.skor{font-size:2.3rem;font-weight:800;line-height:1.1}
.hijau{border-left:8px solid #0b8f7e}.kuning{border-left:8px solid #c98a06}.merah{border-left:8px solid #d1453b}
.kecil{opacity:.75;font-size:.9rem}</style>""", unsafe_allow_html=True)
WARNA = {"hijau": "#0b8f7e", "kuning": "#c98a06", "merah": "#d1453b"}


def kelas(s):
    return "hijau" if s > M.B_SANGAT else "kuning" if s >= M.B_COCOK else "merah"


COLS = {"n": "Mobil", "h": "Harga (juta Rp)", "t": "Tahun", "j": "Jarak (km)", "k": "Kursi", "e": "Tenaga (hp)", "b": "Baterai (kWh)"}
KUSTOM = "Atur sendiri"
CARA_GANTI, CARA_TAMBAH = "Ganti semua data dengan file ini", "Tambahkan ke data yang sudah ada"
LANGKAH = ["Mulai", "Data mobil", "Kebutuhan Anda", "Hasil", "Cara skor dihitung", "Cek & unduh"]
OPSI_KOND = [f"{v}.{s}" for v in K for s in D.LABEL[v]]
LAM, LAMP = "Kekuatan (λ)", "Kekuatan akhir (λ′ = w × λ)"
TEKS_LEVEL = {"Abaikan": "tidak dipakai", "Biasa": "dipakai", "Penting": "dipakai, aturan terkait berbobot penuh"}


def db_awal():
    d = D.BASE.rename(columns=COLS)
    d["Sumber"] = "Bawaan"
    return d


# ======================= STATE =======================
ss = st.session_state
DEF = {"step": 1, "db": db_awal(), "preset": "Seimbang", "max_h": 4000.0, "min_j": 0.0, "min_k": 0, "lemah": M.BOBOT_LEMAH,
       "rule_on": {a["no"]: True for a in M.ATURAN0}, "rules_custom": [], "upn": 0, "pesan": ""}
for v in K:
    DEF[f"lv_{v}"] = D.PRESET["Seimbang"][1][v]
    for i in range(3):
        DEF[f"sp_{v}_{i}"] = float(D.TITIK[v][i])
for k_, v_ in DEF.items():
    ss.setdefault(k_, v_)
SKEYS = ["max_h", "min_j", "min_k", "lemah", "preset"] + [f"lv_{v}" for v in K] + [f"sp_{v}_{i}" for v in K for i in range(3)]
for k_ in SKEYS:  # agar nilai widget tidak hilang saat berpindah langkah
    ss[k_] = ss[k_]


# ======================= CALLBACK =======================
def ke(i):
    ss.step = i


def terapkan_preset():
    if ss.preset in D.PRESET:
        for v in K:
            ss[f"lv_{v}"] = D.PRESET[ss.preset][1][v]


def tandai_kustom():
    ss.preset = KUSTOM


def reset_himpunan():
    for v in K:
        for i in range(3):
            ss[f"sp_{v}_{i}"] = float(D.TITIK[v][i])


def sync_aturan():
    for i, ch in ss.tbl_aturan.get("edited_rows", {}).items():
        if "Aktif" in ch:
            ss.rule_on[ALLNO[int(i)]] = bool(ch["Aktif"])


def tambah_aturan():
    if ss.f_kond:
        ss.rules_custom.append(["&".join(ss.f_kond), ss.f_out])


def hapus_aturan_kustom():
    for i in range(len(ss.rules_custom)):
        ss.rule_on.pop(28 + i, None)
    ss.rules_custom = []


def terapkan_csv(d, mode):
    d = d.copy()
    d.columns = [COLS[c] if c in COLS else c for c in d.columns]
    d["Sumber"] = "Pengguna"
    ss.db = d if mode == CARA_GANTI else pd.concat([ss.db, d], ignore_index=True)
    ss.upn += 1


def reset_data():
    ss.db = db_awal()


def skenario():
    d = {k_: ss[k_] for k_ in SKEYS}
    d["rule_on"] = {str(k_): v_ for k_, v_ in ss.rule_on.items()}
    d["rules_custom"] = ss.rules_custom
    d["db"] = json.loads(ss.db.to_json(orient="records"))
    return d


def muat_skenario():
    f = ss.get("up_skenario")
    if f is None:
        ss.pesan = "Pilih file pengaturan (.json) terlebih dahulu."
        return
    try:
        d = json.loads(f.getvalue().decode("utf-8"))
        for k_ in SKEYS:
            if k_ in d:
                ss[k_] = d[k_]
        for k_ in ["max_h", "min_j", "lemah"] + [f"sp_{v}_{i}" for v in K for i in range(3)]:
            ss[k_] = float(ss[k_])
        ss.min_k = int(ss.min_k)
        for v in K:
            if ss[f"lv_{v}"] not in D.LEVEL:
                ss[f"lv_{v}"] = "Biasa"
        ss.rule_on = {int(k_): bool(v_) for k_, v_ in d.get("rule_on", {}).items()} or DEF["rule_on"]
        ss.rules_custom = d.get("rules_custom", [])
        if d.get("db"):
            x = pd.DataFrame(d["db"])
            x = x.reindex(columns=list(COLS.values()) + ["Sumber"])
            for c in list(COLS.values())[1:]:
                x[c] = pd.to_numeric(x[c], errors="coerce")
            ss.db = x
        ss.pesan = "Pengaturan berhasil dimuat."
    except Exception as e:  # noqa: BLE001
        ss.pesan = f"Pengaturan gagal dimuat: {e}"


# ======================= PERHITUNGAN =======================
def semua_aturan():
    return M.ATURAN0 + [M.parse_aturan(28 + i, t, o, True) for i, (t, o) in enumerate(ss.rules_custom)]


ALLNO = [a["no"] for a in semua_aturan()]


def bersihkan(df):
    """Ubah tabel editor menjadi data valid (kolom internal). Mengembalikan (data, jumlah baris dilewati)."""
    d = df.copy()
    for c in COLS.values():
        if c not in d.columns:
            d[c] = np.nan
    if "Sumber" not in d.columns:
        d["Sumber"] = None
    d = d.dropna(how="all", subset=list(COLS.values()))
    n0 = len(d)
    for c in list(COLS.values())[1:]:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d.dropna(subset=list(COLS.values())[1:])
    d = d[(d[list(COLS.values())[1:]] > 0).all(axis=1)].copy()
    d["Sumber"] = d["Sumber"].fillna("Pengguna")
    ada, nama = set(), []
    for n in d[COLS["n"]]:
        nm = str(n).strip() if pd.notna(n) and str(n).strip() else "Mobil"
        t, i = nm, 2
        while t in ada:
            t, i = f"{nm} ({i})", i + 1
        ada.add(t)
        nama.append(t)
    d[COLS["n"]] = nama
    inv = {v: k_ for k_, v in COLS.items()}
    out = d.rename(columns=inv)[["n"] + K + ["Sumber"]].reset_index(drop=True)
    return out, n0 - len(out)


def bangun_cfg(lv=None):
    lv = lv or {v: ss[f"lv_{v}"] for v in K}
    off = {v for v in K if lv[v] == "Abaikan"}
    prio = [v for v in K if lv[v] == "Penting"]
    galat, titik = [], {}
    for v in K:
        t = tuple(float(ss[f"sp_{v}_{i}"]) for i in range(3))
        if not t[0] < t[1] < t[2]:
            galat.append(f"{D.NAMA[v]}: urutan harus batas bawah < titik tengah < batas atas. Sementara memakai nilai bawaan.")
            t = tuple(float(x) for x in D.TITIK[v])
        titik[v] = t
    return {"S": M.semua_himpunan(titik), "titik": titik, "aturan": M.siapkan_aturan(semua_aturan(), ss.rule_on, off),
            "prio": prio, "lemah": ss.lemah, "off": off, "galat": galat}


def saring(d):
    tolak, ok = {}, []
    for i, c in enumerate(d.to_dict("records")):
        s = []
        if c["h"] > ss.max_h:
            s.append("harga di atas anggaran")
        if c["j"] < ss.min_j:
            s.append("jarak di bawah minimal")
        if c["k"] < ss.min_k:
            s.append("kursi kurang")
        tolak[c["n"]] = s
        if not s:
            ok.append(i)
    return d.iloc[ok].reset_index(drop=True), tolak


def skor_semua(d, cfg):
    rs = M.hitung(d, cfg)
    rs.sort(key=lambda r: -r["skor"])
    for r, p in zip(rs, M.peringkat(rs)):
        r["rk"] = p
    return rs


def fig_himpunan(sets, lo, hi, judul, h=240):
    pad = (hi - lo) * 0.05
    x = np.linspace(lo - pad, hi + pad, 300)
    f = go.Figure([go.Scatter(x=x, y=M.mf(x, p), name=s) for s, p in sets.items()])
    f.update_layout(title=judul, height=h, margin=dict(l=10, r=10, t=40, b=10), legend=dict(orientation="h"), yaxis_title="Derajat")
    return f


def md_tabel(df):
    t = "| " + " | ".join(map(str, df.columns)) + " |\n|" + "---|" * len(df.columns) + "\n"
    return t + "".join("| " + " | ".join(str(x) for x in row) + " |\n" for row in df.values)


# ======================= SIDEBAR =======================
with st.sidebar:
    st.header("Simpan & muat pengaturan")
    st.caption("Simpan semua pilihan Anda (data mobil, kebutuhan, aturan) ke satu file, lalu muat lagi kapan saja.")
    st.download_button("Simpan pengaturan (.json)", json.dumps(skenario(), ensure_ascii=False, indent=1), "pengaturan_voltpilih.json", "application/json")
    st.file_uploader("Muat pengaturan", type="json", key="up_skenario")
    st.button("Terapkan pengaturan", on_click=muat_skenario)
    if ss.pesan:
        st.caption(ss.pesan)
    with st.expander("Kamus istilah"):
        st.markdown("""- **Alternatif**: pilihan yang dibandingkan, di sini mobil.
- **Kriteria**: dasar penilaian: harga, tahun, jarak, kursi, tenaga, baterai.
- **Fuzzy**: nilai boleh 'setengah murah dan setengah menengah', tidak harus salah satu.
- **Derajat keanggotaan (μ)**: seberapa kuat suatu nilai masuk ke satu kategori, dari 0 sampai 1.
- **Aturan jika-maka**: misalnya jika harga murah dan baterai besar, maka sangat cocok.
- **Kekuatan aturan (λ)**: seberapa kuat aturan terpenuhi. DAN memakai nilai terkecil, ATAU memakai nilai terbesar.
- **Bobot aturan (w)**: 1 untuk aturan yang memuat kriteria 'Penting', selain itu lebih kecil (bawaan 0,7).
- **Titik berat (centroid)**: cara mengubah gabungan aturan menjadi satu skor, yaitu pusat area hasilnya.""")

# ======================= HEADER =======================
st.title("VoltPilih ⚡ Pilih Mobil Listrik yang Tepat")
st.caption("Jawab beberapa pertanyaan tentang kebutuhan Anda, lalu lihat mobil mana yang paling cocok beserta alasannya. "
           "Anda bisa pindah ke langkah mana pun kapan saja.")
for kol, (i, nm_) in zip(st.columns(6), enumerate(LANGKAH, 1)):
    kol.button(f"{i}. {nm_}", key=f"hd{i}", on_click=ke, args=(i,), type="primary" if i == ss.step else "secondary", width="stretch")
st.progress(ss.step / 6, text=f"Langkah {ss.step} dari 6: {LANGKAH[ss.step - 1]}")
body = st.container()


# ======================= LANGKAH 2 (editor, dijalankan sebelum perhitungan) =======================
def blok_editor():
    st.subheader("Langkah 2. Data mobil")
    st.markdown("Tabel ini bisa **diedit langsung**: ubah angka, tambah baris di bagian bawah, atau hapus baris (pilih baris lalu tekan Delete). "
                "Kolom *Sumber* menunjukkan asal data: **Bawaan** dari aplikasi, **Pengguna** dari Anda.")
    ed = st.data_editor(ss.db, num_rows="dynamic", hide_index=True, width="stretch", height=400, disabled=["Sumber"],
                        column_config={COLS["h"]: st.column_config.NumberColumn(format="%g", help="Dalam juta rupiah"),
                                       COLS["t"]: st.column_config.NumberColumn(format="%d"),
                                       COLS["k"]: st.column_config.NumberColumn(format="%g"),
                                       COLS["j"]: st.column_config.NumberColumn(format="%g"),
                                       COLS["e"]: st.column_config.NumberColumn(format="%g"),
                                       COLS["b"]: st.column_config.NumberColumn(format="%g")})
    ss.db = ed.reset_index(drop=True)


if ss.step == 2:
    with body:
        blok_editor()

# ======================= HITUNG =======================
db, dilewati = bersihkan(ss.db)
cfg = bangun_cfg()
lolos_df, tolak = saring(db)
semua = skor_semua(lolos_df, cfg)


# ======================= LANGKAH 1: MULAI =======================
def l1():
    st.subheader("Selamat datang di VoltPilih")
    st.markdown("""Memilih mobil listrik itu membingungkan: harga, jarak tempuh, baterai, dan jumlah kursi semuanya berbeda-beda.
VoltPilih menilai tiap mobil dengan **skor 0 sampai 100** sesuai kebutuhan Anda, lalu mengurutkannya.
Semua perhitungan bisa dilihat, jadi Anda tahu dari mana skor itu berasal.""")
    st.markdown("##### Cara pakai")
    langkah = [("1. Cek data mobil", "Lihat daftar mobil yang dinilai. Boleh diubah, ditambah, atau diganti dengan file Anda.", 2),
               ("2. Ceritakan kebutuhan Anda", "Isi anggaran, jarak minimal, dan jumlah kursi, lalu pilih mana yang penting bagi Anda.", 3),
               ("3. Lihat hasil", "Dapatkan peringkat, alasan tiap mobil, dan perbandingan dua mobil.", 4)]
    for kol, (jd, tx, tujuan) in zip(st.columns(3), langkah):
        with kol.container(border=True):
            st.markdown(f"**{jd}**")
            st.write(tx)
            st.button("Buka langkah ini", key=f"go{tujuan}", on_click=ke, args=(tujuan,))
    st.markdown("##### Hal yang dinilai")
    st.dataframe(pd.DataFrame([{"Kriteria": D.NAMA[v], "Satuan": D.SATUAN[v] or "-", "Arti": D.ARTI[v]} for v in K]), hide_index=True, width="stretch")
    st.markdown("##### Bagaimana skor dihitung")
    st.markdown("Skor dihitung dengan **logika fuzzy**, yaitu cara menilai yang mengenal 'agak murah' atau 'cukup jauh', bukan hanya 'ya' atau 'tidak'. Alurnya:")
    st.graphviz_chart("""digraph { rankdir=LR; node [shape=box, style="rounded,filled", fillcolor="#e8f4f2", fontcolor="#102a27", fontname="Helvetica"];
        a [label="Data mobil"]; b [label="Kebutuhan Anda"]; c [label="1. Fuzzifikasi\\nangka menjadi kategori\\n(murah, menengah, mahal)"];
        d [label="2. Inferensi\\ncek aturan jika-maka"]; e [label="3. Agregasi\\ngabung hasil aturan"]; f [label="4. Defuzzifikasi\\nmenjadi satu skor"];
        g [label="Peringkat dan\\nrekomendasi", fillcolor="#fff1cc"];
        a -> c; b -> d; c -> d -> e -> f -> g; }""")
    st.caption("Rincian setiap tahap, lengkap dengan rumus dan angkanya, ada di Langkah 5.")
    st.markdown("##### Dari mana angka-angka ini berasal")
    st.dataframe(pd.DataFrame(D.SUMBER, columns=["Komponen", "Sumber"]), hide_index=True, width="stretch")


# ======================= LANGKAH 2: DATA =======================
def l2():
    a, b, c = st.columns(3)
    a.metric("Jumlah mobil valid", len(db))
    b.metric("Data bawaan", int((db["Sumber"] == "Bawaan").sum()))
    c.metric("Data dari Anda", int((db["Sumber"] != "Bawaan").sum()))
    if dilewati:
        st.warning(f"{dilewati} baris tidak dihitung karena ada kolom kosong, bukan angka, atau nol. Lengkapi baris tersebut di tabel.")
    luar = [(c_["n"], M.di_luar(c_, cfg["titik"])) for c_ in db.to_dict("records")]
    luar = [(n, x) for n, x in luar if x]
    if luar:
        with st.expander(f"⚠️ {len(luar)} mobil punya nilai di luar rentang kategori"):
            st.caption("Nilai di luar rentang diperlakukan sama dengan nilai di batas rentang, jadi dianggap kategori paling ekstrem.")
            for n, x in luar:
                st.write(f"- **{n}**: " + "; ".join(x))
    st.markdown("##### Impor data dari file")
    kiri, kanan = st.columns(2)
    with kiri:
        st.download_button("Unduh template CSV", "nama,harga,tahun,jarak,kursi,tenaga,baterai\nContoh Mobil,800,2024,450,5,200,60\n", "template_mobil.csv", "text/csv")
        st.caption("Harga dalam juta rupiah. Isi semua kolom dengan angka lebih dari 0.")
        st.button("Kembalikan ke data bawaan", on_click=reset_data)
    with kanan:
        cara = st.radio("Saat file CSV dipakai", [CARA_GANTI, CARA_TAMBAH], key="cara_impor")
        up = st.file_uploader("Unggah CSV", type="csv", key=f"up{ss.upn}")
        if up is not None:
            wajib = ["nama", "harga", "tahun", "jarak", "kursi", "tenaga", "baterai"]
            try:
                d = pd.read_csv(up)
                d.columns = [x.strip().lower() for x in d.columns]
                hilang = [x for x in wajib if x not in d.columns]
                if hilang:
                    st.error(f"Kolom belum ada: {', '.join(hilang)}. Lihat template.")
                else:
                    d = d[wajib].copy()
                    d.columns = ["n"] + K
                    n0 = len(d)
                    for x in K:
                        d[x] = pd.to_numeric(d[x], errors="coerce")
                    d = d.dropna()
                    d = d[(d[K] > 0).all(axis=1)]
                    if d.empty:
                        st.error("Tidak ada baris valid. Pastikan semua kolom angka terisi dan lebih dari 0.")
                    else:
                        if len(d) < n0:
                            st.warning(f"{n0 - len(d)} baris dilewati karena kolom kosong, bukan angka, atau nol.")
                        st.button(("Ganti data dengan " if cara == CARA_GANTI else "Tambahkan ") + f"{len(d)} mobil dari CSV",
                                  on_click=terapkan_csv, args=(d, cara), type="primary")
            except Exception as e:  # noqa: BLE001
                st.error(f"File tidak bisa dibaca: {e}")


# ======================= LANGKAH 3: KEBUTUHAN =======================
def l3():
    st.subheader("Langkah 3. Ceritakan kebutuhan Anda")
    st.markdown("Jawab dengan bahasa sehari-hari. Aplikasi yang menerjemahkannya menjadi pengaturan perhitungan.")
    st.markdown("##### A. Syarat wajib")
    st.caption("Mobil yang tidak memenuhi syarat ini tidak ikut dinilai.")
    c1, c2, c3 = st.columns(3)
    c1.number_input("Anggaran maksimal (juta Rp)", key="max_h", min_value=0.0, step=50.0, help="Mobil dengan harga di atas ini tidak dinilai.")
    c2.number_input("Jarak minimal sekali isi daya (km)", key="min_j", min_value=0.0, step=10.0, help="Isi 0 bila tidak dibatasi.")
    c3.selectbox("Jumlah orang yang biasa naik", [0, 2, 4, 5, 6, 7], key="min_k", format_func=lambda v: "Tidak dibatasi" if v == 0 else f"Minimal {v} kursi")

    st.markdown("##### B. Pilih gaya pemakaian")
    st.radio("Mulai dari profil siap pakai (bisa disesuaikan di bagian C)", list(D.PRESET) + [KUSTOM], key="preset", horizontal=True, on_change=terapkan_preset)
    if ss.preset in D.PRESET:
        st.caption(D.PRESET[ss.preset][0])
    else:
        st.caption("Anda mengatur sendiri tingkat kepentingan di bagian C.")

    st.markdown("##### C. Seberapa penting tiap hal bagi Anda?")
    st.caption("**Abaikan**: tidak dipakai. **Biasa**: dipakai. **Penting**: aturan yang memuat hal ini mendapat bobot penuh, aturan lain sedikit lebih kecil.")
    cols = st.columns(3)
    for i, v in enumerate(K):
        with cols[i % 3].container(border=True):
            st.markdown(f"**{D.NAMA[v]}**")
            st.caption(D.ARTI[v])
            st.radio(D.TANYA[v], D.LEVEL, key=f"lv_{v}", horizontal=True, on_change=tandai_kustom)
    st.dataframe(pd.DataFrame([{"Kriteria": D.NAMA[v], "Pilihan Anda": ss[f"lv_{v}"], "Artinya": TEKS_LEVEL[ss[f"lv_{v}"]],
                                "Asal pengaturan": f"profil {ss.preset}" if ss.preset in D.PRESET else "diatur pengguna"} for v in K]),
                 hide_index=True, width="stretch")
    if len(cfg["off"]) == len(K):
        st.error("Semua kriteria diabaikan, jadi tidak ada yang bisa dinilai. Pilih minimal satu kriteria selain Abaikan.")

    with st.expander("D. Pengaturan lanjutan (opsional)"):
        st.markdown("**Bobot aturan non-prioritas (w)**")
        st.slider("w untuk aturan yang tidak memuat kriteria 'Penting'", 0.0, 1.0, key="lemah", step=0.05, help="Bawaan: 0,7. Makin kecil, makin sedikit pengaruh aturan itu.")
        st.markdown("**Batas kategori.** Ubah batas bawah, titik tengah, dan batas atas tiap kriteria. Grafik ikut berubah.")
        st.button("Kembalikan batas ke bawaan", on_click=reset_himpunan)
        for g in cfg["galat"]:
            st.error(g)
        for v in K:
            c1, c2, c3, c4 = st.columns([1, 1, 1, 3])
            c1.number_input(f"{D.NAMA[v]}: batas bawah", key=f"sp_{v}_0", step=D.STEP[v], format="%g")
            c2.number_input(f"{D.NAMA[v]}: titik tengah", key=f"sp_{v}_1", step=D.STEP[v], format="%g")
            c3.number_input(f"{D.NAMA[v]}: batas atas", key=f"sp_{v}_2", step=D.STEP[v], format="%g")
            lo, _, hi = cfg["titik"][v]
            c4.plotly_chart(fig_himpunan(cfg["S"][v], lo, hi, f"{D.NAMA[v]} ({D.SATUAN[v] or 'tahun'})", 200), width="stretch", key=f"fg_{v}")
        st.caption("Bawaan: " + "; ".join(f"{D.NAMA[v].lower()} {M.num(D.TITIK[v][0])} / {M.num(D.TITIK[v][1])} / {M.num(D.TITIK[v][2])}" for v in K) + ".")
        st.markdown("**Aturan jika-maka.** Hilangkan centang untuk menonaktifkan aturan. R1-R27 adalah aturan bawaan.")
        ar = semua_aturan()
        dfr = pd.DataFrame([{"Aktif": ss.rule_on.get(a["no"], True), "No": f"R{a['no']}", "Jika": M.teks_aturan(a["groups"]), "Maka": M.NAMA_OUT[a["out"]],
                             "Sumber": "diatur pengguna" if a["kustom"] else "bawaan"} for a in ar])
        st.data_editor(dfr, hide_index=True, disabled=["No", "Jika", "Maka", "Sumber"], key="tbl_aturan", on_change=sync_aturan, width="stretch", height=300)
        st.markdown("**Tambah aturan sendiri** (syarat digabung DAN)")
        with st.form("form_aturan", clear_on_submit=True):
            st.multiselect("Syarat", OPSI_KOND, key="f_kond", format_func=lambda s: f"{D.NAMA[s.split('.')[0]].lower()} {s.split('.')[1]}")
            st.selectbox("Maka hasilnya", list(M.OUT), key="f_out", format_func=M.NAMA_OUT.get)
            st.form_submit_button("Tambahkan aturan", on_click=tambah_aturan)
        if ss.rules_custom:
            st.button("Hapus semua aturan buatan saya", on_click=hapus_aturan_kustom)

    if not semua:
        st.error("Tidak ada mobil yang memenuhi syarat wajib. Naikkan anggaran atau kurangi syarat.")
    else:
        st.success(f"{len(semua)} dari {len(db)} mobil memenuhi syarat. Sementara ini yang teratas: **{semua[0]['c']['n']}** (skor {semua[0]['skor']:.1f}). Lihat selengkapnya di Langkah 4.")
        st.button("Lihat hasil ▶", on_click=ke, args=(4,), type="primary", key="to_hasil")
    t_ = [(n, s) for n, s in tolak.items() if s]
    if t_:
        with st.expander(f"Mobil yang tidak ikut dinilai ({len(t_)})"):
            for n, s in t_:
                st.write(f"- **{n}**: {', '.join(s)}")


# ======================= LANGKAH 4: HASIL =======================
def l4():
    st.subheader("Langkah 4. Hasil dan rekomendasi")
    if not semua:
        st.warning("Tidak ada mobil yang memenuhi syarat di Langkah 3.")
        return
    st.caption(f"Syarat Anda: anggaran sampai {M.rp(ss.max_h)}, jarak minimal {M.num(ss.min_j)} km, kursi {'tidak dibatasi' if ss.min_k == 0 else f'minimal {ss.min_k}'}. "
               "Skor 0-100: makin tinggi makin cocok.")
    best = semua[0]
    st.success(f"**{best['c']['n']}** direkomendasikan {M.kalimat(best)}")
    if len(semua) > 1 and abs(semua[0]["skor"] - semua[1]["skor"]) < 1:
        st.warning(f"Selisih skor peringkat 1 dan 2 hanya {abs(semua[0]['skor'] - semua[1]['skor']):.2f}. "
                   f"**{semua[0]['c']['n']}** dan **{semua[1]['c']['n']}** praktis setara, jadi pertimbangkan faktor lain seperti biaya perawatan dan ketersediaan pengisian daya.")
    for kol, r in zip(st.columns(min(3, len(semua))), semua[:3]):
        u, kk = M.alasan(r)
        kol.markdown(f'<div class="kartu {kelas(r["skor"])}"><span class="kecil">{["🥇", "🥈", "🥉"][r["rk"] - 1]} Peringkat {r["rk"]}</span>'
                     f'<h3>{html.escape(r["c"]["n"])}</h3><div class="skor">{r["skor"]:.1f}</div><div>{M.penilaian(r["skor"])}</div>'
                     f'<p class="kecil">✓ Unggul: {html.escape(", ".join(u) or "-")}<br>✗ Kurang: {html.escape(", ".join(kk) or "-")}</p></div>', unsafe_allow_html=True)
    st.write("")
    df_r = pd.DataFrame([{"#": r["rk"], "Mobil": r["c"]["n"], "Skor (0-100)": r["skor"], "Penilaian": M.penilaian(r["skor"]),
                          "Harga": M.rp(r["c"]["h"]), "Jarak": f"{M.num(r['c']['j'])} km", "Kursi": M.num(r["c"]["k"]),
                          "Unggul": ", ".join(M.alasan(r)[0]), "Kekurangan": ", ".join(M.alasan(r)[1])} for r in semua])
    st.dataframe(df_r, hide_index=True, width="stretch",
                 column_config={"Skor (0-100)": st.column_config.ProgressColumn("Skor (0-100)", min_value=0, max_value=100, format="%.1f")})
    st.download_button("Unduh hasil (CSV)", df_r.to_csv(index=False), "hasil_voltpilih.csv", "text/csv")
    fb = go.Figure(go.Bar(x=[r["skor"] for r in semua][::-1], y=[r["c"]["n"] for r in semua][::-1], orientation="h",
                          marker_color=[WARNA[kelas(r["skor"])] for r in semua][::-1], text=[f"{r['skor']:.1f}" for r in semua][::-1]))
    fb.update_layout(height=max(300, 28 * len(semua)), margin=dict(l=10, r=10, t=10, b=10), xaxis=dict(range=[0, 100], title="Skor"))
    st.plotly_chart(fb, width="stretch", key="fg_bar")
    st.caption("Warna batang: 🟢 sangat cocok, 🟡 cocok, 🔴 kurang cocok. Ingin tahu cara skor dihitung? Buka Langkah 5.")
    st.markdown("##### Bandingkan dua mobil")
    pil = st.multiselect("Pilih dua mobil", [r["c"]["n"] for r in semua], default=[r["c"]["n"] for r in semua[:2]], max_selections=2)
    if len(pil) == 2:
        for kol, n_ in zip(st.columns(2), pil):
            r_ = next(x for x in semua if x["c"]["n"] == n_)
            with kol:
                st.markdown(f"##### {n_}")
                st.metric(f"Skor (peringkat {r_['rk']})", f"{r_['skor']:.2f}", M.penilaian(r_["skor"]), delta_color="off")
                st.write(f"Direkomendasikan {M.kalimat(r_)}")
                st.dataframe(pd.DataFrame([{"Kriteria": D.NAMA[v], "Nilai": M.nilai_teks(r_["c"], v),
                                            "Kategori": "; ".join(f"{s_} {d:.0%}" for s_, d in r_["F"][v].items() if d > 0)} for v in K]),
                             hide_index=True, width="stretch")
                for a in M.aturan_terkuat(r_, 3):
                    st.markdown(f"- R{a['no']} (kekuatan {a['lamp']:.3f}): jika {a['txt']}, maka **{M.NAMA_OUT[a['out']]}**")
    else:
        st.info("Pilih tepat 2 mobil.")


# ======================= LANGKAH 5: CARA SKOR DIHITUNG =======================
def l5():
    st.subheader("Langkah 5. Cara skor dihitung")
    if not semua:
        st.warning("Belum ada mobil yang memenuhi syarat di Langkah 3.")
        return
    st.markdown("Pilih satu mobil, lalu ikuti tiap tahap. Setiap angka ditampilkan bersama **rumus**, **angka yang dimasukkan**, dan **hasilnya**.")
    nama = st.selectbox("Pilih mobil", [r["c"]["n"] for r in semua], key="mobil_rinci")
    r = next(x for x in semua if x["c"]["n"] == nama)
    c = r["c"]
    kuat = M.aturan_terkuat(r, 3)
    st.info(f"**Ringkasan:** skor {nama} adalah **{r['skor']:.1f}** dari 100 ({M.penilaian(r['skor'])}), peringkat {r['rk']} dari {len(semua)}. "
            + ("Aturan yang paling menentukan: " + "; ".join(f"R{a['no']} (jika {a['txt']}, maka {M.NAMA_OUT[a['out']]})" for a in kuat) + "." if kuat else ""))
    st.dataframe(pd.DataFrame([{"Kriteria": D.NAMA[v], "Nilai": M.nilai_teks(c, v)} for v in K]).set_index("Kriteria").T, width="stretch")
    st.caption("Sumber nilai: " + ("data bawaan aplikasi" if db.loc[db["n"] == nama, "Sumber"].iloc[0] == "Bawaan" else "data Anda") + ".")

    st.markdown("##### Tahap 1. Fuzzifikasi: angka diubah menjadi kategori")
    st.caption("Tiap angka dinilai terhadap tiga kategori (misalnya harga murah, menengah, mahal). Hasilnya derajat keanggotaan (μ) antara 0 dan 1: "
               "makin dekat ke 1, makin kuat masuk kategori itu. Titik a, b, c adalah batas kategori"
               + (" (sebagian sudah Anda ubah)." if any(tuple(cfg['titik'][v]) != tuple(float(x) for x in D.TITIK[v]) for v in K) else "."))
    semua_mu = st.checkbox("Tampilkan juga kategori yang μ-nya 0", key="mu0")
    rows = []
    for v in K:
        for s, p in cfg["S"][v].items():
            rumus, sub, mu = M.mf_jejak(c[v], p)
            if mu > 0 or semua_mu:
                rows.append({"Kriteria": D.NAMA[v], "Nilai x": M.nilai_teks(c, v), "Kategori": s, "Titik (a; b; c)": f"{M.num(p[0])}; {M.num(p[1])}; {M.num(p[2])}",
                             "Rumus": rumus, "Substitusi angka": sub, "μ": round(mu, 4)})
    if rows:
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch", column_config={"μ": st.column_config.NumberColumn(format="%.3f")})
    with st.expander("Lihat grafik kategori untuk satu kriteria"):
        vv = st.selectbox("Kriteria", K, format_func=lambda v: D.NAMA[v])
        lo, _, hi = cfg["titik"][vv]
        fg = fig_himpunan(cfg["S"][vv], lo, hi, f"{D.NAMA[vv]}: posisi nilai {M.num(c[vv])}")
        fg.add_vline(x=c[vv], line_dash="dash")
        st.plotly_chart(fg, width="stretch", key="fg4")

    st.markdown("##### Tahap 2. Inferensi: aturan jika-maka dicek satu per satu")
    st.caption("Kekuatan (λ) = nilai terkecil dari syarat yang digabung DAN (syarat ATAU memakai nilai terbesar). Kekuatan akhir λ′ = w × λ. "
               "w = 1 untuk aturan yang memuat kriteria 'Penting', selain itu " + M.num(cfg['lemah']) + ". Bila tidak ada kriteria 'Penting', semua w = 1.")
    hanya = st.checkbox("Hanya aturan yang menyala (λ′ > 0)", value=True, key="nyala")
    rr = [{"Aturan": f"R{a['no']}", "Jika": a["txt"], "Perhitungan λ": a["jejak"], LAM: a["lam"], "w": a["w"], LAMP: a["lamp"],
           "Maka": M.NAMA_OUT[a["out"]]} for a in r["aktif"] if (a["lamp"] > 0 or not hanya)]
    if rr:
        st.dataframe(pd.DataFrame(rr).sort_values(LAMP, ascending=False), hide_index=True, width="stretch", height=300,
                     column_config={LAMP: st.column_config.ProgressColumn(min_value=0, max_value=1, format="%.3f"), LAM: st.column_config.NumberColumn(format="%.3f"),
                                    "w": st.column_config.NumberColumn(format="%.2f")})
    else:
        st.info("Tidak ada aturan yang menyala untuk mobil ini.")

    st.markdown("##### Tahap 3. Agregasi: aturan dengan hasil sama digabung (diambil yang terkuat)")
    rows = []
    for k_ in M.OUT:
        kand = [a for a in r["aktif"] if a["out"] == k_]
        best = max(kand, key=lambda a: a["lamp"]) if kand else None
        rows.append({"Hasil": M.NAMA_OUT[k_], "Kekuatan = maks(λ′)": r["agg"][k_], "Aturan penentu": f"R{best['no']}" if best and best["lamp"] > 0 else "-"})
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch", column_config={"Kekuatan = maks(λ′)": st.column_config.NumberColumn(format="%.3f")})

    st.markdown("##### Tahap 4. Defuzzifikasi: titik berat area menjadi skor")
    st.caption("Tiap hasil (kurang cocok, cocok, sangat cocok) dipotong setinggi kekuatannya. Area gabungan (biru) dicari titik beratnya. Itulah skor Anda (garis putus-putus).")
    fg = go.Figure()
    for k_, col in zip(M.OUT, ["#d1453b", "#c98a06", "#0b8f7e"]):
        fg.add_scatter(x=M.Y, y=np.minimum(r["agg"][k_], M.mf(M.Y, M.OUT[k_])), name=f"{M.NAMA_OUT[k_]} ({r['agg'][k_]:.3f})", line=dict(color=col, dash="dot"))
    fg.add_scatter(x=M.Y, y=r["mu"], name="Gabungan", fill="tozeroy", line=dict(color="#0b5c73", width=3))
    fg.add_vline(x=r["skor"], line_dash="dash", annotation_text=f"Skor {r['skor']:.2f}")
    fg.update_layout(height=320, margin=dict(l=10, r=10, t=20, b=10), xaxis_title="Skor kecocokan", yaxis_title="Derajat", legend=dict(orientation="h"))
    st.plotly_chart(fg, width="stretch", key="fg_defuzz")
    st.latex(r"\text{Skor} = \frac{\sum y \cdot \mu(y) \cdot \Delta y}{\sum \mu(y) \cdot \Delta y}, \quad \Delta y = 0{,}01")

    st.markdown("##### Tahap 5. Skor akhir")
    st.success(f"Skor = {r['momen']:.2f} / {r['luas']:.2f} = **{r['skor']:.2f}** ({M.penilaian(r['skor'])}), peringkat **{r['rk']}** dari {len(semua)}. "
               "Batas penilaian: di atas 66,67 sangat cocok, 33,33 sampai 66,67 cocok, di bawah 33,33 kurang cocok.")


# ======================= LANGKAH 6: CEK & UNDUH =======================
def buat_excel():
    peng = [("Anggaran maksimal (juta Rp)", ss.max_h), ("Jarak minimal (km)", ss.min_j), ("Kursi minimal", ss.min_k or "tidak dibatasi"), ("Profil", ss.preset),
            ("Bobot aturan non-prioritas", cfg["lemah"])]
    peng += [(f"Kepentingan {D.NAMA[v]}", ss[f"lv_{v}"]) for v in K]
    peng += [(f"Batas kategori {D.NAMA[v]}", " / ".join(M.num(x) for x in cfg["titik"][v])) for v in K]
    peng += [("Aturan nonaktif", ", ".join(f"R{a['no']}" for a in semua_aturan() if not ss.rule_on.get(a["no"], True)) or "-")]
    fz, rl = [], []
    for r in semua:
        n = r["c"]["n"]
        for v in K:
            for s, p in cfg["S"][v].items():
                rumus, sub, mu = M.mf_jejak(r["c"][v], p)
                fz.append({"Mobil": n, "Kriteria": D.NAMA[v], "Nilai": r["c"][v], "Kategori": s, "Rumus": rumus, "Substitusi": sub, "μ": mu})
        for a in r["aktif"]:
            rl.append({"Mobil": n, "Aturan": f"R{a['no']}", "Jika": a["txt"], "Perhitungan λ": a["jejak"], "λ": a["lam"], "w": a["w"], "λ′": a["lamp"], "Maka": M.NAMA_OUT[a["out"]]})
    hasil = pd.DataFrame([{"Peringkat": r["rk"], "Mobil": r["c"]["n"], "Skor": r["skor"], "Penilaian": M.penilaian(r["skor"]).split(" ", 1)[1],
                           "Momen": r["momen"], "Luas": r["luas"]} for r in semua])
    buf = io.BytesIO()
    for eng in ("openpyxl", "xlsxwriter"):
        try:
            with pd.ExcelWriter(buf, engine=eng) as w:
                pd.DataFrame(peng, columns=["Pengaturan", "Nilai"]).astype(str).to_excel(w, sheet_name="Pengaturan", index=False)
                hasil.to_excel(w, sheet_name="Hasil", index=False)
                db.rename(columns={**COLS}).to_excel(w, sheet_name="Data mobil", index=False)
                pd.DataFrame(fz).to_excel(w, sheet_name="Fuzzifikasi", index=False)
                pd.DataFrame(rl).to_excel(w, sheet_name="Inferensi", index=False)
                pd.DataFrame(D.SUMBER, columns=["Komponen", "Sumber"]).to_excel(w, sheet_name="Sumber angka", index=False)
            return buf.getvalue()
        except ImportError:
            buf = io.BytesIO()
    return None


def buat_md(r):
    c = r["c"]
    t = f"# Laporan perhitungan VoltPilih: {c['n']}\n\nSkor **{r['skor']:.2f}** (peringkat {r['rk']} dari {len(semua)}).\n\n"
    t += "## 1. Data\n" + md_tabel(pd.DataFrame([{"Kriteria": D.NAMA[v], "Nilai": M.nilai_teks(c, v)} for v in K]))
    t += "\n## 2. Fuzzifikasi\n" + md_tabel(pd.DataFrame([{"Kriteria": D.NAMA[v], "Kategori": s, "Rumus": M.mf_jejak(c[v], p)[0], "Substitusi": M.mf_jejak(c[v], p)[1],
                                                           "μ": f"{M.mf_jejak(c[v], p)[2]:.3f}"} for v in K for s, p in cfg["S"][v].items() if M.mf_jejak(c[v], p)[2] > 0]))
    t += "\n## 3. Inferensi (aturan yang menyala)\n" + md_tabel(pd.DataFrame([{"Aturan": f"R{a['no']}", "Jika": a["txt"], "Perhitungan λ": a["jejak"], "λ": f"{a['lam']:.3f}",
                                                                              "w": f"{a['w']:.2f}", "λ′": f"{a['lamp']:.3f}", "Maka": M.NAMA_OUT[a["out"]]} for a in r["aktif"] if a["lamp"] > 0]))
    t += "\n## 4. Agregasi dan defuzzifikasi\n" + "".join(f"- {M.NAMA_OUT[k_]}: kekuatan {v_:.3f}\n" for k_, v_ in r["agg"].items())
    t += f"\nSkor = momen / luas = {r['momen']:.2f} / {r['luas']:.2f} = **{r['skor']:.2f}** ({M.penilaian(r['skor'])})\n"
    t += "\n## Asal-usul angka\n" + "".join(f"- **{a}**: {b}\n" for a, b in D.SUMBER)
    return t


def l6():
    st.subheader("Langkah 6. Cek hasil dan unduh laporan")
    if not semua:
        st.info("Belum ada hasil untuk diperiksa. Atur syarat di Langkah 3.")
        return
    st.markdown("##### A. Seberapa kuat rekomendasinya?")
    sens = {"Pengaturan Anda": {r["c"]["n"]: r["rk"] for r in semua}}
    for p, (_, lv) in D.PRESET.items():
        hp = skor_semua(lolos_df, bangun_cfg(lv))
        sens[p] = {x["c"]["n"]: x["rk"] for x in hp}
    sdf = pd.DataFrame(sens).loc[[r["c"]["n"] for r in semua]]
    sdf["Rentang"] = sdf.max(axis=1) - sdf.min(axis=1)
    top = semua[0]["c"]["n"]
    n_prof = len(D.PRESET)
    tetap = int((sdf.loc[top, list(D.PRESET)] == 1).sum())
    m1, m2, m3 = st.columns(3)
    m1.metric("Skor teratas", f"{semua[0]['skor']:.1f}", top, delta_color="off")
    if len(semua) > 1:
        m2.metric("Selisih dengan peringkat 2", f"{semua[0]['skor'] - semua[1]['skor']:.2f}", semua[1]["c"]["n"], delta_color="off")
    m3.metric("Tetap peringkat 1 di profil lain", f"{tetap} dari {n_prof}")
    st.caption("Selisih besar dan tetap unggul di banyak profil berarti rekomendasi kuat. Selisih tipis berarti beberapa mobil hampir setara, jadi pertimbangkan hal lain seperti perawatan dan stasiun pengisian.")
    st.markdown("##### B. Apakah peringkat berubah jika prioritas berubah?")
    st.dataframe(sdf, width="stretch")
    st.caption("Peringkat tiap mobil pada pengaturan Anda dan pada lima profil siap pakai (syarat wajib dan batas kategori tetap sama). "
               "Rentang kecil berarti pilihan aman untuk banyak kebutuhan. Mobil yang melonjak hanya di satu profil cocok untuk kebutuhan khusus.")
    st.markdown("##### C. Laporan")
    st.caption("Excel berisi pengaturan, hasil, fuzzifikasi, inferensi, dan asal-usul angka untuk semua mobil. Laporan Markdown merinci satu mobil langkah demi langkah.")
    xl = buat_excel()
    if xl:
        st.download_button("Unduh laporan lengkap (Excel)", xl, "laporan_voltpilih.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary")
    else:
        st.warning("Library Excel belum terpasang (pip install openpyxl). Gunakan laporan Markdown di bawah.")
    pm = st.selectbox("Mobil untuk laporan rinci", [r["c"]["n"] for r in semua], key="pm_laporan")
    st.download_button("Unduh laporan rinci mobil terpilih (Markdown)", buat_md(next(x for x in semua if x["c"]["n"] == pm)), "laporan_mobil.md", "text/markdown")


with body:
    {1: l1, 2: l2, 3: l3, 4: l4, 5: l5, 6: l6}[ss.step]()
    st.divider()
    n1, _, n3 = st.columns([1, 4, 1])
    if ss.step > 1:
        n1.button("◀ Kembali", key="prev", on_click=ke, args=(ss.step - 1,))
    if ss.step < 6:
        n3.button("Lanjut ▶", key="next", on_click=ke, args=(ss.step + 1,), type="primary")
    st.caption("Skor adalah alat bantu, bukan keputusan akhir. Biaya perawatan, ketersediaan stasiun pengisian, dan selera pribadi tidak dihitung.")
