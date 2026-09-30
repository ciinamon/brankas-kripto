# Brankas Berkas Pribadi Terenkripsi

Aplikasi web untuk mengenkripsi dan mendekripsi teks maupun berkas memakai
algoritma kriptografi modern **AES-256-GCM** dan **ChaCha20-Poly1305**, dengan
kunci yang diturunkan dari kata sandi memakai **scrypt / PBKDF2 / Argon2id**.

Tugas Proyek Aplikasi Kriptografi — Topik A (Enkripsi, Algoritma Modern)
Mata kuliah Keamanan Informasi, Program Studi Informatika, Universitas Siliwangi
Dosen pengampu: Ir. Alam Rahmatulloh, S.T., M.T., MCE., IPM.

## Anggota Kelompok

| Nama | NPM | Kontribusi |
|---|---|---|
| _(isi nama)_ | _(isi NPM)_ | _(mis. modul kripto inti & unit test)_ |
| _(isi nama)_ | _(isi NPM)_ | _(mis. antarmuka web & integrasi)_ |
| _(isi nama)_ | _(isi NPM)_ | _(mis. skrip pengujian & laporan)_ |

- Repositori: _(tautan GitHub)_
- Video demo: _(tautan YouTube)_

## Fitur

**Fitur wajib**

- Enkripsi simetri modern AES-256-GCM dan ChaCha20-Poly1305 untuk teks dan berkas
- Kunci diturunkan dari kata sandi memakai scrypt (default), PBKDF2-HMAC-SHA256,
  atau Argon2id, dengan salt acak 128 bit
- Nonce 96 bit dibangkitkan acak untuk setiap enkripsi dan disimpan bersama cipherteks
- Cipherteks dapat ditampilkan dan disalin dalam format Base64 maupun heksadesimal
- Dekripsi ditolak bila kata sandi salah atau cipherteks/header telah diubah
  (verifikasi authentication tag gagal)

**Fitur pengayaan**

- Enkripsi hibrida: kunci sesi AES-256 dibungkus RSA-OAEP (SHA-256), kunci privat
  disimpan terenkripsi
- Demonstrasi visual kelemahan mode ECB dibanding mode aman pada citra

## Kebutuhan Sistem

- Python 3.10 atau lebih baru
- Paket: `cryptography`, `flask`, `numpy`, `matplotlib`, `openpyxl`, `pillow`
- Opsional: `argon2-cffi` (hanya jika ingin memakai KDF Argon2id)

## Instalasi

```bash
git clone <URL-REPO-ANDA>
cd brankas-kripto

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

## Cara Menjalankan

**1. Aplikasi web**

```bash
python app/app.py
```

Buka http://127.0.0.1:5000

**2. Unit test** (tanpa dependensi tambahan, memakai `unittest` bawaan)

```bash
python -m unittest discover -s tests -v
```

**3. Membuat data uji lalu menjalankan seluruh pengujian**

```bash
python data/buat_data_uji.py     # membuat 11 berkas uji di data/uji/
python bench/benchmark.py        # menulis hasil/hasil_pengujian.xlsx + hasil/grafik/*.png
```

## Contoh Penggunaan

**Lewat antarmuka web**

1. Isi kata sandi, pilih algoritma dan KDF.
2. Tab **Teks** — ketik pesan, tekan *Enkripsi*. Cipherteks muncul dalam Base64
   (bisa diganti ke heksadesimal). Tekan *Dekripsi* untuk memulihkannya.
3. Tab **Berkas** — pilih berkas, tekan *Enkripsi & unduh*. Hasilnya berkas `.bkp`.
   Untuk memulihkan, pilih berkas `.bkp` lalu tekan *Dekripsi & unduh*.
4. Tombol *Lihat metadata* membaca header kontainer tanpa kata sandi; isi berkas
   tetap terenkripsi.

**Lewat Python**

```python
from core import crypto_core as cc

blob = cc.encrypt(b"NIK 3207010101000001", "sandi-yang-kuat",
                  alg_id=cc.ALG_AES_GCM, kdf_id=cc.KDF_SCRYPT)
print(cc.describe(blob))
print(cc.decrypt(blob, "sandi-yang-kuat"))       # -> b'NIK 3207010101000001'
cc.decrypt(blob, "sandi-salah")                  # -> CryptoError
```

## Format Kontainer `.bkp`

Total header 39 byte, seluruhnya dipakai sebagai *Additional Authenticated Data*
sehingga ikut dilindungi authentication tag.

| Offset | Ukuran | Isi |
|---|---|---|
| 0 | 4 | Magic `BKP1` |
| 4 | 1 | Versi format |
| 5 | 1 | ID algoritma (1 = AES-256-GCM, 2 = ChaCha20-Poly1305) |
| 6 | 1 | ID KDF (1 = PBKDF2, 2 = scrypt, 3 = Argon2id) |
| 7 | 4 | Parameter biaya KDF |
| 11 | 16 | Salt acak |
| 27 | 12 | Nonce acak |
| 39 | n | Cipherteks |
| 39+n | 16 | Authentication tag |

Khusus berkas, nama berkas asli ikut dienkripsi: plainteks disusun sebagai
`panjang_nama (2 byte) || nama || isi`.

## Struktur Proyek

```
brankas-kripto/
├── core/crypto_core.py       modul kripto inti (tanpa ketergantungan Flask)
├── app/
│   ├── app.py                server Flask dan endpoint API
│   ├── templates/index.html  antarmuka
│   └── static/               style.css, app.js
├── tests/test_crypto.py      10 unit test
├── data/buat_data_uji.py     pembangkit 11 berkas uji
├── bench/benchmark.py        seluruh pengujian wajib -> XLSX + grafik
└── hasil/                    hasil_pengujian.xlsx dan grafik/
```

## Catatan Keamanan

- Tidak ada kunci, kata sandi, atau kunci privat yang ditulis di dalam kode sumber
  maupun disimpan di repositori.
- Seluruh nilai acak (kunci sesi, salt, nonce) dibangkitkan dengan `os.urandom`,
  yaitu CSPRNG milik sistem operasi.
- Mode ECB dan algoritma usang (MD5, SHA-1, DES, RC4) **tidak** dipakai sebagai
  fitur keamanan utama. AES-CBC dan AES-ECB hanya muncul di `bench/benchmark.py`
  sebagai pembanding untuk keperluan analisis.
- Pesan galat dekripsi sengaja disamakan untuk kasus "sandi salah" dan
  "data diubah" agar tidak membocorkan informasi kepada penyerang.
- Kunci privat RSA pada fitur hibrida disimpan dalam PKCS#8 terenkripsi.

## Batasan

- Aplikasi ini dibuat untuk keperluan pembelajaran, belum diaudit untuk produksi.
- Server Flask bawaan hanya untuk pengembangan; gunakan WSGI produksi bila dipakai
  lebih lanjut.
- Seluruh berkas diproses di memori, sehingga ukuran unggahan dibatasi 64 MB.

## Lisensi

MIT
