"""Bangkitkan berkas uji: teks, gambar PNG, PDF, dan berkas biner 1KB/1MB/10MB.
Jalankan: python data/buat_data_uji.py
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uji")
os.makedirs(DIR, exist_ok=True)


def tulis(nama, data, mode="wb"):
    with open(os.path.join(DIR, nama), mode) as f:
        f.write(data)
    print(f"  {nama:28} {len(data):>10,} byte")


def gambar_pola(w=512, h=512):
    """Gambar dengan area warna rata yang besar — sengaja, supaya kelemahan
    mode ECB (pola plainteks bocor ke cipherteks) terlihat jelas."""
    img = Image.new("RGB", (w, h), (245, 245, 245))
    d = ImageDraw.Draw(img)
    d.rectangle([40, 40, 472, 200], fill=(20, 90, 200))
    d.ellipse([120, 240, 392, 470], fill=(230, 70, 60))
    d.rectangle([40, 240, 100, 470], fill=(30, 30, 30))
    d.text((60, 100), "UNSIL - KEAMANAN INFORMASI", fill=(255, 255, 255))
    return img


print("Membuat berkas uji di", DIR)

# --- teks -------------------------------------------------------------------
tulis("01_teks_pendek.txt", "Halo dunia.".encode())
tulis("02_teks_indonesia.txt",
      ("Data pribadi: NIK 3207010101000001, rekening 1234567890. " * 200).encode())
tulis("03_json.json", b'{"nama":"Mahasiswa","npm":"237006001","nilai":[90,85,78]}')
tulis("04_kosong_1byte.bin", b"\x00")
tulis("05_unicode.txt", "Enkripsi émoji 🔐 dan aksara ᮞᮥᮔ᮪ᮓ.".encode())

# --- gambar & PDF -----------------------------------------------------------
img = gambar_pola()
img.save(os.path.join(DIR, "06_citra.png"))
print(f"  {'06_citra.png':28} {os.path.getsize(os.path.join(DIR,'06_citra.png')):>10,} byte")
def buat_pdf_minimal(baris):
    """PDF 1 halaman yang ditulis manual — tidak butuh pustaka tambahan,
    dan isinya mudah diubah 1 karakter untuk uji tamper saat demo."""
    isi = "BT /F1 13 Tf 60 760 Td 17 TL\n"
    for b in baris:
        isi += f"({b}) Tj T*\n"
    isi += "ET"
    objek = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        "/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        f"<< /Length {len(isi)} >>\nstream\n{isi}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out, offsets = b"%PDF-1.4\n", []
    for i, o in enumerate(objek, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n{o}\nendobj\n".encode("latin-1")
    xref = len(out)
    out += f"xref\n0 {len(objek)+1}\n0000000000 65535 f \n".encode()
    out += b"".join(f"{off:010d} 00000 n \n".encode() for off in offsets)
    out += (f"trailer\n<< /Size {len(objek)+1} /Root 1 0 R >>\n"
            f"startxref\n{xref}\n%%EOF\n").encode()
    return out


tulis("07_dokumen.pdf", buat_pdf_minimal([
    "SURAT KETERANGAN - DOKUMEN UJI",
    "",
    "Nama  : Mahasiswa Informatika",
    "NPM   : 237006001",
    "Prodi : Informatika, Fakultas Teknik",
    "",
    "Dokumen ini dipakai untuk menguji enkripsi AES-256-GCM",
    "dan ChaCha20-Poly1305 pada tugas Keamanan Informasi.",
]))

# --- biner untuk uji waktu --------------------------------------------------
rng = np.random.default_rng(42)
tulis("08_biner_1KB.bin", rng.bytes(1024))
tulis("09_biner_1MB.bin", rng.bytes(1024 * 1024))
tulis("10_biner_10MB.bin", rng.bytes(10 * 1024 * 1024))
# berkas berpola (entropi rendah) untuk perbandingan entropi
tulis("11_berpola_1MB.bin", b"AAAABBBB" * (1024 * 128))

print("Selesai —", len(os.listdir(DIR)), "berkas uji.")
