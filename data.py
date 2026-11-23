"""VoltPilih, komponen BASIS DATA.
Semua konstanta, aturan, dan data contoh ada di sini, lengkap dengan asal-usulnya."""
import pandas as pd

# Urutan kriteria: h=harga, t=tahun, j=jarak, k=kursi, e=tenaga, b=baterai
K = ["h", "t", "j", "k", "e", "b"]
NAMA = {"h": "Harga", "t": "Tahun produksi", "j": "Jarak tempuh", "k": "Kursi", "e": "Tenaga", "b": "Baterai"}
SATUAN = {"h": "juta Rp", "t": "", "j": "km", "k": "orang", "e": "hp", "b": "kWh"}
ARTI = {
    "h": "Harga mobil. Makin murah makin baik.",
    "t": "Tahun pembuatan. Makin baru makin baik.",
    "j": "Jarak yang bisa ditempuh sekali isi daya penuh. Makin jauh makin baik.",
    "k": "Jumlah orang yang bisa naik. Makin banyak makin baik.",
    "e": "Tenaga mesin dalam hp. Makin besar makin baik.",
    "b": "Kapasitas baterai. Makin besar biasanya makin tahan lama di jalan.",
}
TANYA = {
    "h": "Seberapa penting harga yang murah?",
    "t": "Seberapa penting tahun produksi yang baru?",
    "j": "Seberapa penting jarak tempuh yang jauh?",
    "k": "Seberapa penting kursi yang banyak?",
    "e": "Seberapa penting tenaga yang besar?",
    "b": "Seberapa penting baterai yang besar?",
}
STEP = {"h": 50.0, "t": 1.0, "j": 10.0, "k": 0.5, "e": 10.0, "b": 5.0}

# Tingkat kepentingan yang dipilih pengguna untuk tiap kriteria.
LEVEL = ["Abaikan", "Biasa", "Penting"]

# Tiga himpunan fuzzy tiap kriteria, berurutan dari rendah ke tinggi.
LABEL = {"h": ("murah", "menengah", "mahal"), "t": ("lama", "menengah", "baru"), "j": ("dekat", "menengah", "jauh"),
         "k": ("sedikit", "menengah", "banyak"), "e": ("rendah", "menengah", "tinggi"), "b": ("kecil", "menengah", "besar")}
# Titik (batas bawah, titik tengah, batas atas). Himpunan: bahu kiri (lo,lo,mid), segitiga (lo,mid,hi), bahu kanan (mid,hi,hi).
TITIK = {"h": (200, 1850, 3500), "t": (2018, 2020, 2022), "j": (200, 400, 600),
         "k": (2, 3.5, 5), "e": (40, 220, 400), "b": (10, 65, 120)}

GOOD = {"murah", "baru", "jauh", "banyak", "tinggi", "besar"}
BAD = {"mahal", "lama", "dekat", "sedikit", "rendah", "kecil"}

# 27 aturan bawaan. "&" = DAN (min), "|" = ATAU (max). R1-R8 sangat cocok, R9-R20 cocok, R21-R27 kurang cocok.
RULES_TXT = """h.murah&(b.besar|b.menengah)&j.jauh
t.baru&(h.murah|h.menengah)&(b.besar|b.menengah)&(j.menengah|j.jauh)
h.menengah&k.banyak&(e.menengah|e.tinggi)&b.besar
h.mahal&t.baru&b.besar&j.jauh&e.tinggi
h.murah&k.banyak&e.menengah&b.menengah
h.menengah&t.baru&j.jauh
(h.murah|h.menengah)&t.baru&k.banyak
h.menengah&b.besar&j.jauh
h.murah&b.kecil&j.dekat
t.menengah&b.menengah&j.menengah
k.sedikit&h.murah&j.dekat
j.jauh&b.besar&e.menengah
h.menengah&k.banyak&e.tinggi
t.baru&h.menengah&b.menengah
h.mahal&b.besar&j.menengah
h.menengah&t.menengah&j.menengah
h.murah&k.menengah&e.menengah
t.menengah&(h.murah|h.menengah)&k.banyak
h.murah&j.menengah&b.menengah
t.baru&k.menengah&b.menengah
t.lama&(b.kecil|e.rendah)
h.mahal&b.kecil
h.mahal&j.dekat
k.sedikit&h.mahal
j.jauh&b.kecil
t.lama&(h.menengah|h.mahal)
e.rendah&k.banyak""".split("\n")

# Profil siap pakai. Isi: (penjelasan, tingkat kepentingan tiap kriteria)
def _lv(**penting):
    return {v: penting.get(v, "Biasa") for v in K}


PRESET = {
    "Seimbang": ("Semua kriteria dianggap sama penting. Cocok bila Anda belum yakin.", _lv()),
    "Hemat": ("Mengutamakan harga yang terjangkau.", _lv(h="Penting")),
    "Performa": ("Mengutamakan tenaga, jarak tempuh, dan baterai.", _lv(e="Penting", j="Penting", b="Penting")),
    "Keluarga": ("Mengutamakan jumlah kursi untuk penumpang.", _lv(k="Penting")),
    "Perjalanan jauh": ("Mengutamakan jarak tempuh dan baterai besar.", _lv(j="Penting", b="Penting")),
}

# Data contoh 22 mobil. Kolom: nama,harga(juta Rp),tahun,jarak(km),kursi,tenaga(hp),baterai(kWh)
DATA = """BMW i3 120 Ah,2600,2018,310,4,170,42
BMW i3s 120 Ah,2800,2018,285,4,184,42
BMW iX3,1100,2021,460,5,286,80
BMW iX xDrive40,2000,2021,400,5,326,76
BMW iX xDrive50,2400,2021,600,5,503,111
Hyundai IONIQ 5 SS,748,2021,400,5,170,58
Hyundai IONIQ 5 SLR,789,2021,362,5,235,58
Hyundai IONIQ 5 PS,809,2021,485,5,218,73
Hyundai IONIQ 5 PLR,859,2021,462,5,306,73
Hyundai Kona EV 39 kWh,750,2018,305,5,136,39
Hyundai Kona EV 64 kWh,800,2018,484,5,204,64
Tesla Model 3 SR+,1500,2018,448,5,325,54
Tesla Model 3 Long Range,2850,2018,580,5,441,79
Tesla Model 3 Performance,3000,2018,567,5,513,79
Tesla Model Y Long Range AWD,2000,2020,531,5,384,78
Tesla Model Y Performance,2300,2020,487,5,393,78
Wuling Air ev SR,238,2022,200,4,40,17
Wuling Air ev LR,311,2022,300,4,40,26
Toyota BZ4X,1190,2022,510,5,201,71
Nissan Leaf,738,2018,400,5,150,40
Mini Electric,1046,2020,270,4,181,32
KIA EV6 GT,1299,2021,410,5,321,77"""
BASE = pd.DataFrame([ln.split(",") for ln in DATA.split("\n")], columns=["n"] + K)
BASE[K] = BASE[K].astype(float)

# Asal-usul setiap komponen angka (ditampilkan di aplikasi dan laporan).
SUMBER = [
    ("Data mobil", "Data contoh bawaan aplikasi (22 model). Harga dan spesifikasi bisa berbeda dari kondisi pasar saat ini, jadi ubah di Langkah 2 bila perlu."),
    ("Batas kategori (murah, menengah, mahal, dst.)", "Nilai bawaan aplikasi. Bisa Anda ubah di Langkah 3, bagian Pengaturan lanjutan."),
    ("27 aturan jika-maka", "Aturan bawaan aplikasi: R1-R8 menghasilkan 'sangat cocok', R9-R20 'cocok', R21-R27 'kurang cocok'. Bisa dinonaktifkan atau ditambah."),
    ("Cara menggabungkan syarat", "DAN memakai nilai terkecil, ATAU memakai nilai terbesar. Hasil aturan yang sama digabung dengan nilai terbesar."),
    ("Bobot aturan (1 dan 0,7)", "Aturan yang memuat kriteria 'Penting' berbobot 1, aturan lain 0,7. Bila tidak ada kriteria 'Penting', semua aturan berbobot 1. Angka 0,7 bisa diubah."),
    ("Skor akhir", "Titik berat (centroid) area hasil gabungan aturan, dihitung per 0,01 pada skala 0-100."),
    ("Batas penilaian", "Di atas 66,67 = sangat cocok, 33,33 sampai 66,67 = cocok, di bawah 33,33 = kurang cocok."),
    ("Syarat wajib, tingkat kepentingan, batas kategori yang diubah", "Diatur oleh Anda di Langkah 3. Aplikasi menandainya 'diatur pengguna'."),
]
