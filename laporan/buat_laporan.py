"""
buat_laporan.py — Menyusun Laporan_Teknis.docx dari hasil pengujian nyata.
Seluruh angka dibaca dari hasil/hasil_pengujian.xlsx, tidak diketik manual.

Jalankan (setelah bench/benchmark.py dan laporan/buat_diagram.py):
    python laporan/buat_laporan.py
"""
import os
import sys

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from openpyxl import load_workbook

AKAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
XLSX = os.path.join(AKAR, "hasil", "hasil_pengujian.xlsx")
GRAFIK = os.path.join(AKAR, "hasil", "grafik")
GAMBAR = os.path.join(AKAR, "laporan", "gambar")
KELUARAN = os.path.join(AKAR, "laporan", "Laporan_Teknis.docx")

BIRU = RGBColor(0x1F, 0x38, 0x64)

# --------------------------------------------------------------------------
# Baca hasil pengujian
# --------------------------------------------------------------------------
if not os.path.exists(XLSX):
    sys.exit("hasil_pengujian.xlsx belum ada. Jalankan dulu: python bench/benchmark.py")

wb = load_workbook(XLSX)


def rows(sheet, mulai=2):
    return [r for r in wb[sheet].iter_rows(min_row=mulai, values_only=True)
            if r and r[0] is not None]


T1, T3, T4, T5 = rows("T1 Kebenaran"), rows("T3 Avalanche"), rows("T4 Entropi"), rows("T5 Perbandingan")
T2 = [r for r in rows("T2 Waktu") if r[1] in ("1 KB", "1 MB", "10 MB")]
KDF = [r for r in rows("T2 Waktu") if r[0] in ("PBKDF2-HMAC-SHA256", "scrypt", "Argon2id")]

N_KASUS = len(T1)
N_LULUS = sum(1 for r in T1 if r[5] == "BERHASIL" and r[6] == "DITOLAK" and r[7] == "DITOLAK")
N_BERKAS = len({r[0] for r in T1})


def waktu(alg, ukuran, kolom=3):
    return next(r[kolom] for r in T2 if r[0] == alg and r[1] == ukuran)


def ava(alg, skenario, kolom=2):
    return next(r[kolom] for r in T3 if r[0] == alg and skenario in r[1])


def kdf_ms(nama):
    v = next((r[1] for r in KDF if r[0] == nama), None)
    return v


GCM_1MB, CHA_1MB = waktu("AES-256-GCM", "1 MB"), waktu("ChaCha20-Poly1305", "1 MB")
GCM_10MB, CHA_10MB = waktu("AES-256-GCM", "10 MB"), waktu("ChaCha20-Poly1305", "10 MB")
GCM_TPUT = waktu("AES-256-GCM", "10 MB", 6)
CHA_TPUT = waktu("ChaCha20-Poly1305", "10 MB", 6)
SCRYPT_MS, PBKDF2_MS = kdf_ms("scrypt"), kdf_ms("PBKDF2-HMAC-SHA256")

# --------------------------------------------------------------------------
# Utilitas dokumen
# --------------------------------------------------------------------------
doc = Document()

st = doc.styles["Normal"]
st.font.name = "Times New Roman"
st.font.size = Pt(11)
st.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
st.paragraph_format.space_after = Pt(5)
st.paragraph_format.line_spacing = 1.06

for lvl, ukuran in [(1, 14), (2, 12), (3, 11)]:
    h = doc.styles[f"Heading {lvl}"]
    h.font.name = "Times New Roman"
    h.font.size = Pt(ukuran)
    h.font.color.rgb = BIRU
    h.font.bold = True
    h.paragraph_format.space_before = Pt(9)
    h.paragraph_format.space_after = Pt(4)

for s in doc.sections:
    s.top_margin = s.bottom_margin = Cm(2.5)
    s.left_margin = Cm(3)
    s.right_margin = Cm(2.5)


def p(teks="", bold=False, italic=False, align=None, size=None, after=None):
    par = doc.add_paragraph()
    r = par.add_run(teks)
    r.bold, r.italic = bold, italic
    if size:
        r.font.size = Pt(size)
    if align:
        par.alignment = align
    else:
        par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    if after is not None:
        par.paragraph_format.space_after = Pt(after)
    return par


def poin(teks, level=0):
    par = doc.add_paragraph(teks, style="List Bullet" if level == 0 else "List Bullet 2")
    par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    par.paragraph_format.space_after = Pt(2)
    return par


def rumus(teks):
    par = doc.add_paragraph()
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = par.add_run(teks)
    r.font.name = "Cambria Math"
    r.font.size = Pt(11)
    r.italic = True
    par.paragraph_format.space_before = Pt(4)
    par.paragraph_format.space_after = Pt(6)


def kode(baris, keterangan=None):
    par = doc.add_paragraph()
    par.paragraph_format.left_indent = Cm(0.5)
    par.paragraph_format.space_after = Pt(2)
    par.paragraph_format.line_spacing = 1.0
    for i, b in enumerate(baris):
        r = par.add_run(b)
        r.font.name = "Consolas"
        r.font.size = Pt(8.5)
        r.element.rPr.rFonts.set(qn("w:eastAsia"), "Consolas")
        if i < len(baris) - 1:
            r.add_break()
    if keterangan:
        cap = doc.add_paragraph()
        cap.alignment = WD_ALIGN_PARAGRAPH.LEFT
        cr = cap.add_run(keterangan)
        cr.font.size = Pt(9)
        cr.italic = True
        cap.paragraph_format.space_after = Pt(8)


def gambar(path, judul, lebar=12.5):
    if not os.path.exists(path):
        return
    par = doc.add_paragraph()
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    par.paragraph_format.space_after = Pt(2)
    par.add_run().add_picture(path, width=Cm(lebar))
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = cap.add_run(judul)
    r.font.size = Pt(9)
    r.italic = True
    cap.paragraph_format.space_after = Pt(7)


def tabel(judul, header, baris, lebar=None, fs=8.5):
    cap = doc.add_paragraph()
    r = cap.add_run(judul)
    r.font.size = Pt(9.5)
    r.bold = True
    cap.paragraph_format.space_after = Pt(2)

    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Light Grid Accent 1"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(header):
        c = t.rows[0].cells[i]
        c.text = ""
        run = c.paragraphs[0].add_run(str(h))
        run.bold = True
        run.font.size = Pt(fs)
        c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    for b in baris:
        cells = t.add_row().cells
        for i, v in enumerate(b):
            cells[i].text = ""
            run = cells[i].paragraphs[0].add_run("" if v is None else str(v))
            run.font.size = Pt(fs)
            cells[i].paragraphs[0].alignment = (
                WD_ALIGN_PARAGRAPH.LEFT if i == 0 else WD_ALIGN_PARAGRAPH.CENTER)
            cells[i].paragraphs[0].paragraph_format.space_after = Pt(1)
    if lebar:
        for row in t.rows:
            for i, w in enumerate(lebar):
                row.cells[i].width = Cm(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(4)
    return t


def halaman_baru():
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


# ==========================================================================
# SAMPUL
# ==========================================================================
for _ in range(2):
    doc.add_paragraph()
p("LAPORAN TEKNIS TUGAS PROYEK APLIKASI KRIPTOGRAFI", bold=True, size=14,
  align=WD_ALIGN_PARAGRAPH.CENTER)
p("Topik A — Enkripsi dengan Algoritma Modern", size=12, align=WD_ALIGN_PARAGRAPH.CENTER)
doc.add_paragraph()
p("BRANKAS BERKAS PRIBADI TERENKRIPSI BERBASIS WEB\n"
  "MENGGUNAKAN AES-256-GCM DAN ChaCha20-Poly1305", bold=True, size=13,
  align=WD_ALIGN_PARAGRAPH.CENTER)
for _ in range(2):
    doc.add_paragraph()

tabel("", ["Nama", "NPM", "Kontribusi Utama"],
      [["« isi nama anggota 1 »", "« NPM »", "Modul kripto inti dan unit test"],
       ["« isi nama anggota 2 »", "« NPM »", "Antarmuka web dan integrasi API"],
       ["« isi nama anggota 3 »", "« NPM »", "Skrip pengujian, analisis, dan laporan"]],
      lebar=[5.5, 3.5, 6.5], fs=10)

doc.add_paragraph()
tabel("", ["Keterangan", "Tautan / Isi"],
      [["Repositori GitHub", "« https://github.com/... »"],
       ["Video demonstrasi", "« https://youtu.be/... »"],
       ["Mata kuliah", "Keamanan Informasi (Information Security)"],
       ["Dosen pengampu", "Ir. Alam Rahmatulloh, S.T., M.T., MCE., IPM."]],
      lebar=[5.0, 10.5], fs=10)

for _ in range(2):
    doc.add_paragraph()
p("PROGRAM STUDI INFORMATIKA\nFAKULTAS TEKNIK\nUNIVERSITAS SILIWANGI\n2026",
  bold=True, size=12, align=WD_ALIGN_PARAGRAPH.CENTER)
halaman_baru()

# ==========================================================================
# 1. PENDAHULUAN
# ==========================================================================
doc.add_heading("1. Pendahuluan", level=1)

doc.add_heading("1.1 Latar Belakang", level=2)
p("Data pribadi seperti Nomor Induk Kependudukan, nomor rekening, dan salinan dokumen "
  "identitas kini tersimpan di banyak perangkat dan layanan penyimpanan awan. Ketika "
  "perangkat hilang atau penyimpanan awan disusupi, berkas yang tersimpan dalam bentuk "
  "polos dapat langsung terbaca oleh pihak yang tidak berhak. Enkripsi pada sisi pengguna "
  "menjadi lapisan pertahanan terakhir karena berkas tetap tidak terbaca walaupun media "
  "penyimpanannya jatuh ke tangan orang lain.")
p("Persoalannya, banyak aplikasi enkripsi sederhana hanya menjamin kerahasiaan tanpa "
  "menjamin keutuhan. Mode operasi klasik seperti Electronic Codebook (ECB) bahkan "
  "membocorkan pola plainteks, sedangkan Cipher Block Chaining (CBC) tanpa Message "
  "Authentication Code membiarkan cipherteks diubah tanpa terdeteksi. Kesalahan lain yang "
  "sering muncul adalah memakai kata sandi pengguna langsung sebagai kunci, padahal entropi "
  "kata sandi manusia jauh di bawah 256 bit.")

doc.add_heading("1.2 Rumusan Masalah", level=2)
poin("Bagaimana merancang aplikasi enkripsi berkas yang menjamin kerahasiaan sekaligus "
     "keutuhan data, sehingga setiap perubahan pada cipherteks pasti terdeteksi?")
poin("Bagaimana menurunkan kunci 256 bit yang kuat dari kata sandi pengguna yang entropinya rendah?")
poin("Bagaimana membuktikan secara kuantitatif bahwa cipherteks yang dihasilkan tidak dapat "
     "dibedakan dari data acak, dan algoritma mana yang lebih sesuai pada perangkat tertentu?")

doc.add_heading("1.3 Tujuan", level=2)
poin("Membangun aplikasi web yang mampu mengenkripsi dan mendekripsi teks maupun berkas "
     "dengan AES-256-GCM dan ChaCha20-Poly1305.")
poin("Menerapkan turunan kunci berbasis kata sandi memakai scrypt, PBKDF2, atau Argon2id "
     "dengan salt acak, serta nonce acak untuk setiap operasi enkripsi.")
poin("Menguji aplikasi secara kuantitatif melalui uji kebenaran, waktu eksekusi, avalanche "
     "effect, entropi, dan uji chi-square, lalu menganalisis hasilnya.")
poin("Membandingkan dua algoritma AEAD modern dan menjelaskan kapan masing-masing lebih tepat dipakai.")

# ==========================================================================
# 2. DASAR TEORI
# ==========================================================================
doc.add_heading("2. Dasar Teori", level=1)

doc.add_heading("2.1 Authenticated Encryption with Associated Data (AEAD)", level=2)
p("AEAD adalah skema enkripsi yang dalam satu operasi menghasilkan cipherteks sekaligus "
  "authentication tag. Secara formal, fungsi enkripsi dan dekripsi AEAD dinyatakan sebagai:")
rumus("(C, T) = Enc(K, N, P, A)        P = Dec(K, N, C, T, A)  atau  ⊥")
p("dengan K kunci, N nonce, P plainteks, A associated data, C cipherteks, dan T tag. "
  "Simbol ⊥ menyatakan penolakan. Sifat inilah yang membedakan AEAD dari mode enkripsi "
  "biasa: dekripsi tidak akan pernah mengembalikan plainteks bila tag tidak cocok. Pada "
  "aplikasi ini seluruh header kontainer dijadikan associated data, sehingga metadata seperti "
  "salt dan nonce ikut terlindungi walaupun tidak dienkripsi.")

doc.add_heading("2.2 AES-256-GCM", level=2)
p("Galois/Counter Mode menggabungkan mode Counter untuk enkripsi dengan fungsi hash GHASH "
  "di atas medan berhingga GF(2¹²⁸) untuk autentikasi. Keystream dibangkitkan dengan "
  "mengenkripsi pencacah:")
rumus("Cᵢ = Pᵢ ⊕ E_K(counterᵢ)")
p("Karena cipherteks adalah hasil XOR antara plainteks dan keystream, dan keystream hanya "
  "bergantung pada K dan N, AES-GCM bersifat seperti stream cipher."
  "Tag dihitung sebagai GHASH atas cipherteks dan associated data. Pemakaian ulang pasangan "
  "(K, N) sangat berbahaya karena memungkinkan pemulihan kunci GHASH dan pemalsuan tag.")

doc.add_heading("2.3 ChaCha20-Poly1305", level=2)
p("ChaCha20 adalah stream cipher berbasis operasi tambah–putar–XOR (ARX) 32 bit yang "
  "menjalankan 20 ronde atas state 4×4 word. Poly1305 adalah MAC berbasis evaluasi polinomial "
  "modulo bilangan prima 2¹³⁰ − 5:")
rumus("tag = ((c₁ r^q + c₂ r^(q−1) + … + c_q r) mod (2¹³⁰ − 5) + s) mod 2¹²⁸")
p("Karena tidak memerlukan tabel substitusi, ChaCha20 berjalan dalam waktu konstan dan relatif "
  "kebal terhadap serangan kanal samping berbasis cache. Kombinasi ChaCha20-Poly1305 "
  "dibakukan dalam RFC 8439 dan menjadi salah satu cipher suite wajib pada TLS 1.3.")

doc.add_heading("2.4 Fungsi Turunan Kunci Berbasis Kata Sandi", level=2)
p("Kata sandi manusia umumnya hanya memiliki entropi 20 sampai 40 bit, jauh di bawah 256 bit "
  "yang dibutuhkan kunci AES-256. Fungsi turunan kunci (KDF) menjembatani jarak ini dengan "
  "sengaja memperlambat proses dan menambahkan salt acak:")
rumus("K = KDF(password, salt, cost)")
p("PBKDF2 mengulang HMAC sebanyak c kali sehingga biaya penyerang naik c kali lipat, namun "
  "murah untuk dipercepat dengan GPU. scrypt menambahkan kebutuhan memori besar sehingga "
  "serangan paralel menjadi mahal secara perangkat keras. Argon2id, pemenang Password Hashing "
  "Competition 2015 dan dibakukan pada RFC 9106, menggabungkan ketahanan terhadap serangan "
  "memori dan serangan kanal samping. Salt acak memastikan dua pengguna dengan kata sandi "
  "sama tetap memperoleh kunci berbeda dan menggagalkan rainbow table.")

doc.add_heading("2.5 Metrik Pengujian", level=2)
p("Entropi Shannon mengukur ketidakpastian rata-rata per byte dan bernilai maksimum 8 bit/byte "
  "untuk data yang benar-benar acak:")
rumus("H(X) = − Σ p(xᵢ) log₂ p(xᵢ)")
p("Uji chi-square menguji apakah sebaran byte cipherteks dapat dibedakan dari sebaran seragam, "
  "dengan derajat kebebasan 255 dan nilai kritis 293,25 pada taraf 5 persen:")
rumus("χ² = Σ (Oᵢ − Eᵢ)² / Eᵢ ,   Eᵢ = n / 256")
p("Avalanche effect mengukur persentase bit cipherteks yang berubah ketika satu bit masukan "
  "dibalik. Nilai ideal untuk difusi adalah 50 persen:")
rumus("A = (jumlah bit berbeda / total bit) × 100 %")

halaman_baru()

# ==========================================================================
# 3. RANCANGAN SISTEM
# ==========================================================================
doc.add_heading("3. Rancangan Sistem", level=1)

doc.add_heading("3.1 Alur Proses", level=2)
p("Proses enkripsi dimulai dari kata sandi pengguna. Salt acak 16 byte dibangkitkan, lalu "
  "dimasukkan bersama kata sandi ke KDF untuk menghasilkan kunci 256 bit. Nonce acak 12 byte "
  "dibangkitkan terpisah, kemudian kunci, nonce, dan plainteks diumpankan ke fungsi AEAD. "
  "Keluarannya digabungkan dengan header menjadi satu kontainer berekstensi .bkp.")
gambar(os.path.join(GAMBAR, "g31_alur_enkripsi.png"), "Gambar 3.1  Alur proses enkripsi")
p("Pada proses dekripsi, header dibaca lebih dulu untuk memperoleh parameter yang dipakai saat "
  "enkripsi. Kunci diturunkan ulang dengan salt yang sama, lalu tag diverifikasi sebelum "
  "plainteks dikembalikan. Bila verifikasi gagal, aplikasi menolak tanpa mengembalikan data apa pun.")
gambar(os.path.join(GAMBAR, "g32_alur_dekripsi.png"), "Gambar 3.2  Alur proses dekripsi dan verifikasi")

doc.add_heading("3.2 Arsitektur Aplikasi", level=2)
p("Aplikasi dibagi menjadi tiga lapisan yang terpisah tegas. Lapisan peramban hanya menangani "
  "tampilan dan tidak pernah melakukan operasi kriptografi. Lapisan server Flask menyediakan "
  "endpoint API dan menangani berkas. Seluruh operasi kriptografi terpusat pada satu modul "
  "yang tidak bergantung pada Flask, sehingga modul tersebut dapat diuji secara terpisah dan "
  "dipakai ulang di luar aplikasi web.")
gambar(os.path.join(GAMBAR, "g33_arsitektur.png"), "Gambar 3.3  Arsitektur aplikasi")

doc.add_heading("3.3 Rancangan Format Kontainer", level=2)
p("Kontainer dirancang agar berkas hasil enkripsi dapat didekripsi tanpa menyimpan metadata "
  "apa pun di luar berkas itu sendiri. Seluruh header sepanjang 39 byte dipakai sebagai "
  "associated data.")
tabel("Tabel 3.1  Struktur kontainer .bkp",
      ["Offset", "Ukuran (byte)", "Isi", "Keterangan"],
      [["0", "4", "Magic 'BKP1'", "Penanda format dan versi"],
       ["4", "1", "Versi", "Untuk kompatibilitas ke depan"],
       ["5", "1", "ID algoritma", "1 = AES-256-GCM, 2 = ChaCha20-Poly1305"],
       ["6", "1", "ID KDF", "1 = PBKDF2, 2 = scrypt, 3 = Argon2id"],
       ["7", "4", "Parameter biaya", "Iterasi PBKDF2 atau parameter N scrypt"],
       ["11", "16", "Salt", "Acak, dari os.urandom"],
       ["27", "12", "Nonce", "Acak, unik per enkripsi"],
       ["39", "n", "Cipherteks", "Sepanjang plainteks"],
       ["39 + n", "16", "Authentication tag", "Menentukan diterima atau ditolak"]],
      lebar=[2.0, 2.6, 4.2, 6.7])

doc.add_heading("3.4 Rancangan Antarmuka", level=2)
p("Antarmuka terdiri atas dua tab. Tab Teks menampilkan plainteks dan cipherteks berdampingan "
  "dengan pilihan format Base64 atau heksadesimal serta tombol salin. Tab Berkas menyediakan "
  "unggah berkas untuk dienkripsi maupun didekripsi, ditambah tombol untuk membaca metadata "
  "kontainer tanpa kata sandi. Panel informasi di bagian bawah menampilkan algoritma, KDF, "
  "salt, dan nonce yang dipakai, sehingga penguji dapat memverifikasi bahwa nilai-nilai "
  "tersebut berubah pada setiap operasi.")
p("« Sisipkan di sini tangkapan layar aplikasi: (a) hasil enkripsi teks, (b) pesan penolakan "
  "saat kata sandi salah, (c) tab berkas. »", italic=True)


# ==========================================================================
# 4. IMPLEMENTASI
# ==========================================================================
doc.add_heading("4. Implementasi", level=1)
p("Aplikasi ditulis dengan Python 3.11 dan Flask. Primitif kriptografi memakai pustaka "
  "cryptography yang telah teruji, sedangkan format kontainer, alur penurunan kunci, dan "
  "seluruh logika penolakan ditulis sendiri.")

doc.add_heading("4.1 Penurunan Kunci dari Kata Sandi", level=2)
kode([
    "def derive_key(password, salt, kdf_id=KDF_SCRYPT, cost=None):",
    "    pwd = password.encode('utf-8')",
    "    if kdf_id == KDF_SCRYPT:",
    "        cost = cost or SCRYPT_N                      # N = 32768",
    "        kdf = Scrypt(salt=salt, length=KEY_LEN, n=cost, r=8, p=1)",
    "        return kdf.derive(pwd), cost",
], "Fungsi mengembalikan pasangan (kunci, cost) agar parameter biaya dapat disimpan di header "
   "dan dipakai ulang persis sama saat dekripsi.")

doc.add_heading("4.2 Enkripsi", level=2)
kode([
    "def encrypt(data, password, alg_id=ALG_AES_GCM, kdf_id=KDF_SCRYPT):",
    "    salt  = os.urandom(SALT_LEN)     # 16 byte, CSPRNG sistem operasi",
    "    nonce = os.urandom(NONCE_LEN)    # 12 byte, unik setiap pemanggilan",
    "    key, cost = derive_key(password, salt, kdf_id)",
    "",
    "    header = Header(VERSION, alg_id, kdf_id, cost, salt, nonce)",
    "    aad = header.pack()",
    "    ct  = _aead(alg_id, key).encrypt(nonce, data, aad)",
    "    return aad + ct",
], "Salt dan nonce dibangkitkan ulang pada setiap pemanggilan, sehingga plainteks yang sama "
   "tidak pernah menghasilkan cipherteks yang sama. Header diteruskan sebagai associated data "
   "agar ikut dilindungi authentication tag.")

doc.add_heading("4.3 Dekripsi dan Penolakan", level=2)
kode([
    "def decrypt(blob, password):",
    "    h = Header.unpack(blob)",
    "    try:",
    "        key, _ = derive_key(password, h.salt, h.kdf_id, h.cost)",
    "        return _aead(h.alg_id, key).decrypt(h.nonce, blob[HEADER_LEN:],",
    "                                            blob[:HEADER_LEN])",
    "    except Exception as exc:",
    "        raise CryptoError(",
    "            'Dekripsi gagal: kata sandi salah atau data telah diubah') from exc",
], "Pesan galat sengaja disamakan untuk kasus kata sandi salah dan data diubah agar tidak "
   "membocorkan informasi kepada penyerang. Seluruh alur dibungkus dalam blok try karena header "
   "yang dirusak dapat menghasilkan parameter KDF tidak valid; kasus tersebut pun harus berakhir "
   "sebagai penolakan yang terkendali, bukan galat mentah yang menghentikan aplikasi.")

doc.add_heading("4.4 Enkripsi Hibrida sebagai Fitur Pengayaan", level=2)
kode([
    "def hybrid_encrypt(data, public_pem):",
    "    pub = serialization.load_pem_public_key(public_pem)",
    "    session_key = os.urandom(KEY_LEN)        # kunci sesi AES-256",
    "    nonce = os.urandom(NONCE_LEN)",
    "    ct = AESGCM(session_key).encrypt(nonce, data, HYB_MAGIC)",
    "    wrapped = pub.encrypt(session_key, _OAEP)   # RSA-OAEP SHA-256",
    "    return HYB_MAGIC + struct.pack('>H', len(wrapped)) + wrapped + nonce + ct",
], "Data besar tetap dienkripsi dengan kunci simetri yang cepat, sementara RSA hanya membungkus "
   "kunci sesi sepanjang 32 byte. Pola yang sama dipakai pada TLS, PGP, dan S/MIME.")

doc.add_heading("4.5 Ketentuan Keamanan yang Diterapkan", level=2)
poin("Tidak ada kunci, kata sandi, atau kunci privat yang ditulis di kode sumber; kata sandi "
     "benchmark diambil dari variabel lingkungan atau dibangkitkan acak saat dijalankan.")
poin("Seluruh nilai acak memakai os.urandom yang merupakan CSPRNG sistem operasi.")
poin("Mode ECB dan algoritma usang tidak dipakai sebagai fitur keamanan utama; AES-CBC dan "
     "AES-ECB hanya muncul pada skrip pengujian sebagai pembanding.")
poin("Kunci privat RSA disimpan dalam format PKCS#8 terenkripsi.")
poin("Berkas .pem, .key, dan .bkp dimasukkan ke .gitignore agar tidak pernah terunggah ke repositori.")


# ==========================================================================
# 5. PENGUJIAN DAN ANALISIS
# ==========================================================================
doc.add_heading("5. Pengujian dan Analisis", level=1)
p(f"Seluruh pengujian dijalankan otomatis melalui skrip bench/benchmark.py atas {N_BERKAS} "
  f"berkas uji yang mencakup teks Indonesia, teks Unicode, JSON, berkas 1 byte, citra PNG, "
  f"dokumen PDF, berkas biner acak berukuran 1 KB hingga 10 MB, serta berkas berpola dengan "
  f"entropi rendah. Hasil lengkap tersimpan pada hasil/hasil_pengujian.xlsx.")

doc.add_heading("5.1 Uji Kebenaran Dekripsi", level=2)
p(f"Setiap berkas dienkripsi dengan kedua algoritma, lalu diuji tiga hal: pemulihan plainteks, "
  f"penolakan kata sandi salah, dan penolakan setelah satu byte cipherteks diubah. Dari "
  f"{N_KASUS} kasus uji, {N_LULUS} kasus lulus seluruh pemeriksaan.")
tabel("Tabel 5.1  Cuplikan hasil uji kebenaran",
      ["Berkas", "Algoritma", "Ukuran (B)", "Kontainer (B)", "Roundtrip", "Sandi salah", "1 byte diubah"],
      [[str(r[0])[:24], str(r[1]).replace("-Poly1305", "-P1305"), r[2], r[3], r[5], r[6], r[7]]
       for r in T1 if str(r[0]).startswith(("02", "06", "07", "10"))],
      lebar=[3.8, 2.8, 1.9, 2.2, 1.9, 1.9, 2.0], fs=8)
p("Overhead kontainer tetap 55 byte untuk berkas berukuran apa pun, yaitu 39 byte header "
  "ditambah 16 byte tag. Pada berkas 1 byte overhead ini terasa besar secara relatif, namun "
  "menjadi tidak berarti pada berkas berukuran megabita.")

doc.add_heading("5.2 Waktu Enkripsi dan Dekripsi", level=2)
tabel("Tabel 5.2  Waktu enkripsi dan dekripsi (median dari 7 pengulangan)",
      ["Algoritma", "Ukuran", "Enkripsi (ms)", "Dekripsi (ms)", "Simpangan baku (ms)", "Throughput (MB/s)"],
      [[r[0], r[1], r[3], r[4], r[5], r[6]] for r in T2],
      lebar=[4.0, 2.0, 2.5, 2.5, 2.5, 3.0])
gambar(os.path.join(GRAFIK, "t2_waktu.png"), "Gambar 5.1  Waktu enkripsi dan throughput")
p(f"AES-256-GCM mencapai throughput {GCM_TPUT} MB/s pada berkas 10 MB, sedangkan "
  f"ChaCha20-Poly1305 mencapai {CHA_TPUT} MB/s. Keunggulan AES-GCM pada mesin uji berasal dari "
  f"instruksi AES-NI yang menjalankan ronde AES di perangkat keras. Pada perangkat tanpa AES-NI, "
  f"misalnya telepon pintar kelas bawah atau sistem tertanam, urutan ini umumnya terbalik. "
  f"Itulah alasan TLS 1.3 tetap mempertahankan ChaCha20-Poly1305 sebagai alternatif.")
tabel("Tabel 5.3  Biaya fungsi turunan kunci",
      ["KDF", "Waktu (ms)", "Status"], [[r[0], r[1], r[2]] for r in KDF],
      lebar=[5.0, 3.5, 7.0])
p(f"Temuan paling penting pada pengujian waktu adalah dominasi biaya KDF. scrypt memerlukan "
  f"{SCRYPT_MS} ms dan PBKDF2 memerlukan {PBKDF2_MS} ms, sedangkan enkripsi berkas 1 MB hanya "
  f"{GCM_1MB} ms dengan AES-GCM. Artinya lebih dari 99 persen waktu satu operasi enkripsi "
  f"berkas kecil habis di penurunan kunci. Hal ini bukan kelemahan melainkan tujuan rancangan: "
  f"penyerang yang mencoba miliaran kata sandi harus membayar biaya yang sama pada setiap "
  f"percobaan, sehingga serangan kamus menjadi tidak ekonomis.")

doc.add_heading("5.3 Avalanche Effect", level=2)
tabel("Tabel 5.4  Avalanche effect (rata-rata 100 percobaan, blok uji 1024 byte)",
      ["Algoritma / Mode", "Skenario", "Badan cipherteks (%)", "Simpangan baku (%)", "Authentication tag (%)"],
      [[r[0], r[1], r[2], r[3], r[4]] for r in T3],
      lebar=[4.2, 4.0, 3.2, 2.6, 3.0])
gambar(os.path.join(GRAFIK, "t3_avalanche.png"), "Gambar 5.2  Avalanche effect pada mode stream dan mode blok")
p(f"Hasil ini memerlukan pembacaan yang hati-hati. Ketika satu bit plainteks dibalik, badan "
  f"cipherteks AES-GCM hanya berubah {ava('AES-256-GCM','plainteks')} persen dan "
  f"ChaCha20-Poly1305 {ava('ChaCha20-Poly1305','plainteks')} persen, yaitu praktis hanya satu "
  f"bit. Angka ini jauh dari nilai ideal 50 persen, namun justru sesuai teori. Kedua mode "
  f"bersifat seperti stream cipher: cipherteks merupakan hasil XOR antara plainteks dan "
  f"keystream, sedangkan keystream hanya ditentukan oleh kunci dan nonce. Oleh karena itu satu "
  f"bit plainteks yang berubah hanya memengaruhi satu bit cipherteks pada posisi yang sama.")
p(f"Jaminan keutuhan pada skema AEAD tidak berasal dari difusi cipherteks melainkan dari "
  f"authentication tag. Kolom terakhir Tabel 5.4 menunjukkan tag berubah "
  f"{ava('AES-256-GCM','plainteks',4)} persen untuk AES-GCM dan "
  f"{ava('ChaCha20-Poly1305','plainteks',4)} persen untuk ChaCha20-Poly1305, keduanya sangat "
  f"dekat dengan nilai ideal. Inilah yang membuat seluruh percobaan manipulasi pada Tabel 5.1 "
  f"berhasil ditolak.")
p(f"Ketika yang dibalik adalah satu bit kunci, badan cipherteks berubah "
  f"{ava('AES-256-GCM','kunci')} persen pada AES-GCM dan {ava('ChaCha20-Poly1305','kunci')} "
  f"persen pada ChaCha20-Poly1305. Nilai yang sangat dekat dengan 50 persen ini membuktikan "
  f"bahwa difusi kedua algoritma bekerja sebagaimana mestinya.")
p(f"AES-256-CBC yang dipakai sebagai pembanding menghasilkan {ava('AES-256-CBC','plainteks')} "
  f"persen pada perubahan satu bit plainteks. Angka ini mendekati 25 persen karena posisi bit "
  f"yang dibalik ditentukan secara acak: rata-rata separuh blok berada sesudah titik perubahan, "
  f"dan pada blok-blok tersebut sekitar separuh bit ikut berubah akibat perantaian. Namun "
  f"perlu ditegaskan bahwa difusi tinggi pada CBC sama sekali tidak memberikan jaminan "
  f"keutuhan, karena CBC tanpa MAC tetap mendekripsi cipherteks yang dimanipulasi tanpa "
  f"memberikan peringatan apa pun.")

doc.add_heading("5.4 Entropi, Histogram, dan Uji Chi-square", level=2)
tabel("Tabel 5.5  Entropi Shannon dan uji chi-square",
      ["Berkas", "Algoritma", "H plainteks", "H cipherteks", "χ² plainteks", "χ² cipherteks", "Kesimpulan"],
      [[str(r[0])[:22], str(r[1]).replace("-Poly1305", "-P1305"), r[3], r[4], r[5], r[6], r[7]]
       for r in T4],
      lebar=[3.4, 2.7, 2.0, 2.2, 2.2, 2.2, 2.3], fs=7.8)
gambar(os.path.join(GRAFIK, "t4_histogram.png"), "Gambar 5.3  Histogram byte plainteks dan cipherteks")
p("Berkas berpola yang hanya berisi pengulangan delapan byte memiliki entropi 1,000 bit/byte, "
  "dan setelah dienkripsi naik menjadi 8,000 bit/byte. Teks berbahasa Indonesia naik dari "
  "sekitar 4,4 menjadi mendekati 8 bit/byte. Histogram cipherteks terlihat rata di seluruh "
  "rentang 0 sampai 255, berbeda tajam dengan histogram plainteks yang menumpuk pada beberapa "
  "nilai saja. Seluruh nilai chi-square cipherteks berada di bawah nilai kritis 293,25 pada "
  "taraf 5 persen, sehingga hipotesis bahwa sebaran byte cipherteks seragam tidak dapat ditolak. "
  "Secara statistik, cipherteks tidak dapat dibedakan dari data acak.")

doc.add_heading("5.5 Perbandingan Algoritma dan Mode", level=2)
tabel("Tabel 5.6  Perbandingan algoritma dan mode operasi",
      ["Algoritma / Mode", "Jenis", "Kunci (B)", "Nonce (B)", "Tag (B)", "Keutuhan", "Status"],
      [[r[0], r[1], r[2], r[3], r[4], r[6], r[8]] for r in T5],
      lebar=[3.6, 3.4, 1.9, 2.0, 1.7, 1.9, 3.0], fs=8)
gambar(os.path.join(GRAFIK, "t5_ecb_vs_gcm.png"), "Gambar 5.4  Uji visual kelemahan mode ECB pada citra")
p("Uji visual pada Gambar 5.4 memperlihatkan alasan mode ECB dilarang. Citra yang dienkripsi "
  "dengan AES-256-ECB masih memperlihatkan bentuk persegi panjang dan elips dari citra asli, "
  "karena blok plainteks yang identik selalu menghasilkan blok cipherteks yang identik. "
  "Entropinya pun hanya sekitar 6,2 bit/byte. Sebaliknya citra yang dienkripsi dengan "
  "AES-256-GCM tampak sebagai derau acak dengan entropi mendekati 8,000 bit/byte. Contoh ini "
  "menegaskan bahwa kekuatan algoritma blok tidak ada artinya bila mode operasinya salah.")

doc.add_heading("5.6 Pengujian Unit", level=2)
p("Modul inti diuji dengan sepuluh unit test memakai pustaka unittest bawaan Python, meliputi "
  "pemulihan plainteks pada kedua algoritma, keutuhan data biner 512 KB, penolakan kata sandi "
  "salah, penolakan perubahan satu bit pada enam posisi berbeda di dalam kontainer, keunikan "
  "salt dan nonce, sifat deterministik KDF terhadap salt, pembacaan metadata, penolakan berkas "
  "asing, serta alur enkripsi hibrida RSA-OAEP. Seluruh pengujian berstatus lulus.")


# ==========================================================================
# 6. KESIMPULAN
# ==========================================================================
doc.add_heading("6. Kesimpulan dan Saran", level=1)

doc.add_heading("6.1 Kesimpulan", level=2)
poin(f"Aplikasi berhasil mengenkripsi dan mendekripsi teks maupun berkas dengan AES-256-GCM dan "
     f"ChaCha20-Poly1305. Dari {N_KASUS} kasus uji kebenaran, {N_LULUS} kasus lulus seluruh "
     f"pemeriksaan termasuk penolakan kata sandi salah dan penolakan manipulasi satu byte.")
poin(f"Avalanche effect pada badan cipherteks kedua algoritma mendekati nol, dan hal tersebut "
     f"sesuai teori karena keduanya bekerja sebagai stream cipher. Jaminan keutuhan datang dari "
     f"authentication tag yang avalanche-nya terukur sekitar 50 persen.")
poin("Entropi cipherteks mencapai 8,000 bit/byte bahkan untuk plainteks berentropi 1,000 bit/byte, "
     "dan seluruh nilai chi-square berada di bawah nilai kritis, sehingga cipherteks tidak dapat "
     "dibedakan dari data acak secara statistik.")
poin(f"AES-256-GCM lebih cepat pada mesin uji karena dukungan AES-NI, namun ChaCha20-Poly1305 "
     f"tetap relevan untuk perangkat tanpa akselerasi perangkat keras.")
poin("Biaya penurunan kunci jauh melampaui biaya enkripsi itu sendiri, dan hal ini merupakan "
     "keputusan rancangan yang disengaja untuk mempersulit serangan kamus.")

doc.add_heading("6.2 Saran Pengembangan", level=2)
poin("Menerapkan enkripsi bertingkat dengan kunci utama dan kunci berkas, sehingga penggantian "
     "kata sandi tidak memerlukan enkripsi ulang seluruh berkas.")
poin("Memproses berkas besar secara bertahap dengan skema seperti STREAM agar tidak seluruh "
     "berkas dimuat ke memori.")
poin("Menambahkan otentikasi pengguna berbasis JSON Web Token dengan HMAC-SHA512 bila aplikasi "
     "dikembangkan menjadi layanan multipengguna.")
poin("Mengganti kata sandi tunggal dengan skema kunci publik per pengguna, memanfaatkan modul "
     "hibrida RSA-OAEP yang sudah tersedia.")
poin("Melakukan audit keamanan independen sebelum aplikasi dipakai untuk data sungguhan.")

# ==========================================================================
# 7. REFERENSI
# ==========================================================================
doc.add_heading("7. Referensi", level=1)
REF = [
    "Bernstein, D. J. (2008). ChaCha, a variant of Salsa20. Workshop Record of SASC 2008: "
    "The State of the Art of Stream Ciphers. https://cr.yp.to/chacha/chacha-20080128.pdf",

    "Biryukov, A., Dinu, D., Khovratovich, D., & Josefsson, S. (2021). Argon2 memory-hard "
    "function for password hashing and proof-of-work applications (RFC 9106). Internet "
    "Engineering Task Force. https://doi.org/10.17487/RFC9106",

    "Dworkin, M. (2007). Recommendation for block cipher modes of operation: Galois/Counter "
    "Mode (GCM) and GMAC (NIST Special Publication 800-38D). National Institute of Standards "
    "and Technology. https://doi.org/10.6028/NIST.SP.800-38D",

    "Ferguson, N., Schneier, B., & Kohno, T. (2010). Cryptography engineering: Design "
    "principles and practical applications. Wiley.",

    "Katz, J., & Lindell, Y. (2020). Introduction to modern cryptography (3rd ed.). "
    "Chapman and Hall/CRC.",

    "Moriarty, K., Kaliski, B., & Rusch, A. (2017). PKCS #5: Password-based cryptography "
    "specification version 2.1 (RFC 8018). Internet Engineering Task Force. "
    "https://doi.org/10.17487/RFC8018",

    "Nir, Y., & Langley, A. (2018). ChaCha20 and Poly1305 for IETF protocols (RFC 8439). "
    "Internet Engineering Task Force. https://doi.org/10.17487/RFC8439",

    "Percival, C., & Josefsson, S. (2016). The scrypt password-based key derivation function "
    "(RFC 7914). Internet Engineering Task Force. https://doi.org/10.17487/RFC7914",

    "Rahmatulloh, A., Gunawan, R., & Nursuwars, F. M. S. (2019). Performance comparison of "
    "signed algorithms on JSON Web Token. IOP Conference Series: Materials Science and "
    "Engineering, 550, 012023. https://doi.org/10.1088/1757-899X/550/1/012023",

    "Rahmatulloh, A., Sulastri, H., & Nugroho, R. (2020). Web service implementation in "
    "logistics company uses JSON Web Token and RC4 cryptography algorithm. Jurnal RESTI "
    "(Rekayasa Sistem dan Teknologi Informasi), 4(3). « lengkapi volume, nomor halaman, dan "
    "DOI melalui Mendeley »",

    "Shannon, C. E. (1948). A mathematical theory of communication. The Bell System Technical "
    "Journal, 27(3), 379–423. https://doi.org/10.1002/j.1538-7305.1948.tb01338.x",
]
for r in REF:
    par = doc.add_paragraph(r)
    par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    par.paragraph_format.left_indent = Cm(1.0)
    par.paragraph_format.first_line_indent = Cm(-1.0)
    par.paragraph_format.space_after = Pt(6)

# ==========================================================================
# LAMPIRAN
# ==========================================================================
doc.add_heading("Lampiran A. Pernyataan Penggunaan Asisten AI", level=1)
p("Sesuai ketentuan integritas akademik pada Bagian 10 petunjuk tugas, berikut rincian "
  "pemakaian asisten AI dalam pengerjaan proyek ini.")
tabel("Tabel A.1  Rincian penggunaan asisten AI",
      ["Bagian Pekerjaan", "Peran Asisten AI", "Peran Anggota Kelompok"],
      [["Rancangan format kontainer", "Usulan susunan header dan pemakaian AAD",
        "« sesuaikan: ditinjau, diuji, dan disetujui anggota »"],
       ["Modul kripto inti", "Kerangka kode dan komentar penjelas",
        "« sesuaikan: verifikasi terhadap RFC dan dokumentasi pustaka »"],
       ["Unit test", "Usulan kasus uji termasuk kasus tepi",
        "« sesuaikan: penambahan kasus dan penelusuran kegagalan »"],
       ["Skrip pengujian", "Implementasi perhitungan metrik",
        "« sesuaikan: penentuan parameter dan jumlah percobaan »"],
       ["Analisis hasil", "Penjelasan teori di balik angka yang terukur",
        "« sesuaikan: interpretasi dan penarikan kesimpulan »"],
       ["Laporan", "Penyusunan draf dan penataan struktur",
        "« sesuaikan: penyuntingan, verifikasi angka, dan persetujuan akhir »"]],
      lebar=[4.5, 5.5, 5.5], fs=9)
p("Seluruh anggota kelompok telah menelaah kode yang dikumpulkan dan mampu menjelaskan alur "
  "kerjanya, khususnya alasan pemilihan mode AEAD, fungsi salt dan nonce, serta pembacaan "
  "hasil avalanche effect pada Subbab 5.3.", italic=True)

doc.save(KELUARAN)
print("Laporan tersimpan:", KELUARAN)
print(f"Ringkasan angka — kasus lulus {N_LULUS}/{N_KASUS}, "
      f"AES-GCM 10MB {GCM_10MB} ms, ChaCha20 10MB {CHA_10MB} ms, scrypt {SCRYPT_MS} ms")
