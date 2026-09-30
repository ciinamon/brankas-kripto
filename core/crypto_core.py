"""
crypto_core.py — Modul kripto inti Brankas Berkas Pribadi Terenkripsi.

Algoritma utama (AEAD / authenticated encryption):
  - AES-256-GCM            (NIST SP 800-38D)
  - ChaCha20-Poly1305      (RFC 8439)
Keduanya sekaligus menjamin KERAHASIAAN (confidentiality) dan
KEUTUHAN + KEASLIAN (integrity & authenticity) lewat authentication tag.
Karena itu cipherteks yang diubah satu byte pun akan DITOLAK saat dekripsi.

Turunan kunci (KDF) dari kata sandi:
  - PBKDF2-HMAC-SHA256, scrypt, atau Argon2id — semuanya dengan salt acak.
KDF wajib dipakai karena kata sandi manusia punya entropi rendah; KDF yang
lambat & boros memori membuat serangan brute-force jadi mahal.

CATATAN KEAMANAN:
  - Tidak ada kunci/kata sandi yang ditulis di kode sumber.
  - Semua nilai acak (salt, nonce, kunci sesi) memakai os.urandom, yaitu
    CSPRNG dari sistem operasi.
  - Mode ECB TIDAK dipakai. AES-CBC hanya disediakan di modul benchmark
    sebagai PEMBANDING, bukan fitur keamanan utama.
"""

from __future__ import annotations

import os
import struct
from dataclasses import dataclass

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM, ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

# ---------------------------------------------------------------------------
# Konstanta format kontainer
# ---------------------------------------------------------------------------
MAGIC = b"BKP1"          # penanda berkas Brankas Kripto versi 1
VERSION = 1

ALG_AES_GCM = 1
ALG_CHACHA20 = 2
ALG_NAMES = {ALG_AES_GCM: "AES-256-GCM", ALG_CHACHA20: "ChaCha20-Poly1305"}
ALG_IDS = {v: k for k, v in ALG_NAMES.items()}

KDF_PBKDF2 = 1
KDF_SCRYPT = 2
KDF_ARGON2 = 3
KDF_NAMES = {KDF_PBKDF2: "PBKDF2-HMAC-SHA256", KDF_SCRYPT: "scrypt", KDF_ARGON2: "Argon2id"}
KDF_IDS = {v: k for k, v in KDF_NAMES.items()}

KEY_LEN = 32             # 256 bit — sama untuk AES-256 dan ChaCha20
SALT_LEN = 16            # 128 bit
NONCE_LEN = 12           # 96 bit, ukuran nonce yang direkomendasikan untuk GCM & ChaCha20
TAG_LEN = 16             # 128 bit authentication tag

# Parameter biaya default (bisa dinaikkan sesuai kemampuan perangkat)
PBKDF2_ITERATIONS = 600_000      # rekomendasi OWASP 2023 untuk SHA-256
SCRYPT_N = 2 ** 15               # 32768
SCRYPT_R, SCRYPT_P = 8, 1
ARGON2_TIME_COST = 3
ARGON2_MEMORY_KIB = 64 * 1024    # 64 MiB

# Header: magic(4) ver(1) alg(1) kdf(1) cost(4) salt(16) nonce(12) = 39 byte
HEADER_FMT = ">4sBBBI16s12s"
HEADER_LEN = struct.calcsize(HEADER_FMT)


class CryptoError(Exception):
    """Kesalahan kripto yang aman ditampilkan ke pengguna."""


# ---------------------------------------------------------------------------
# 1. Turunan kunci dari kata sandi
# ---------------------------------------------------------------------------
def derive_key(password: str, salt: bytes, kdf_id: int = KDF_SCRYPT,
               cost: int | None = None) -> tuple[bytes, int]:
    """Turunkan kunci 256-bit dari kata sandi + salt.

    Mengembalikan (kunci, cost) agar nilai cost bisa ikut disimpan di header
    dan dekripsi memakai parameter yang persis sama.
    """
    pwd = password.encode("utf-8")

    if kdf_id == KDF_PBKDF2:
        cost = cost or PBKDF2_ITERATIONS
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=KEY_LEN,
                         salt=salt, iterations=cost)
        return kdf.derive(pwd), cost

    if kdf_id == KDF_SCRYPT:
        cost = cost or SCRYPT_N
        kdf = Scrypt(salt=salt, length=KEY_LEN, n=cost, r=SCRYPT_R, p=SCRYPT_P)
        return kdf.derive(pwd), cost

    if kdf_id == KDF_ARGON2:
        cost = cost or ARGON2_TIME_COST
        try:
            from argon2.low_level import Type, hash_secret_raw
        except ImportError as exc:  # pragma: no cover
            raise CryptoError("Argon2id butuh paket argon2-cffi") from exc
        key = hash_secret_raw(secret=pwd, salt=salt, time_cost=cost,
                              memory_cost=ARGON2_MEMORY_KIB, parallelism=4,
                              hash_len=KEY_LEN, type=Type.ID)
        return key, cost

    raise CryptoError(f"KDF tidak dikenal: {kdf_id}")


# ---------------------------------------------------------------------------
# 2. Pembungkus AEAD
# ---------------------------------------------------------------------------
def _aead(alg_id: int, key: bytes):
    if alg_id == ALG_AES_GCM:
        return AESGCM(key)
    if alg_id == ALG_CHACHA20:
        return ChaCha20Poly1305(key)
    raise CryptoError(f"Algoritma tidak dikenal: {alg_id}")


@dataclass
class Header:
    version: int
    alg_id: int
    kdf_id: int
    cost: int
    salt: bytes
    nonce: bytes

    def pack(self) -> bytes:
        return struct.pack(HEADER_FMT, MAGIC, self.version, self.alg_id,
                           self.kdf_id, self.cost, self.salt, self.nonce)

    @staticmethod
    def unpack(blob: bytes) -> "Header":
        if len(blob) < HEADER_LEN:
            raise CryptoError("Cipherteks terlalu pendek / bukan berkas BKP1")
        magic, ver, alg, kdf, cost, salt, nonce = struct.unpack(
            HEADER_FMT, blob[:HEADER_LEN])
        if magic != MAGIC:
            raise CryptoError("Format berkas tidak dikenali (magic salah)")
        return Header(ver, alg, kdf, cost, salt, nonce)


def encrypt(data: bytes, password: str, alg_id: int = ALG_AES_GCM,
            kdf_id: int = KDF_SCRYPT) -> bytes:
    """Enkripsi bytes -> kontainer (header || cipherteks || tag).

    Salt dan nonce DIBANGKITKAN ACAK setiap pemanggilan, jadi mengenkripsi
    plainteks yang sama dua kali menghasilkan cipherteks yang berbeda.
    Header dipakai sebagai AAD sehingga ikut terlindungi tag; mengubah
    byte header pun akan membuat dekripsi gagal.
    """
    if not password:
        raise CryptoError("Kata sandi tidak boleh kosong")

    salt = os.urandom(SALT_LEN)
    nonce = os.urandom(NONCE_LEN)
    key, cost = derive_key(password, salt, kdf_id)

    header = Header(VERSION, alg_id, kdf_id, cost, salt, nonce)
    aad = header.pack()
    ct = _aead(alg_id, key).encrypt(nonce, data, aad)
    return aad + ct


def decrypt(blob: bytes, password: str) -> bytes:
    """Dekripsi kontainer. Melempar CryptoError bila sandi salah ATAU
    cipherteks/header telah diubah (verifikasi tag gagal)."""
    h = Header.unpack(blob)
    try:
        # Seluruh alur diturunkan-lalu-dekripsi dibungkus: header yang diubah
        # bisa menghasilkan parameter KDF tidak valid, dan itu pun harus
        # berakhir sebagai penolakan yang rapi, bukan crash.
        key, _ = derive_key(password, h.salt, h.kdf_id, h.cost)
        return _aead(h.alg_id, key).decrypt(h.nonce, blob[HEADER_LEN:],
                                            blob[:HEADER_LEN])
    except Exception as exc:
        # Pesan sengaja disamakan untuk kedua kasus agar tidak membocorkan
        # informasi ke penyerang (apakah sandi benar tapi data rusak, dsb).
        raise CryptoError(
            "Dekripsi gagal: kata sandi salah atau data telah diubah") from exc


def describe(blob: bytes) -> dict:
    """Baca metadata kontainer tanpa perlu kata sandi."""
    h = Header.unpack(blob)
    return {
        "versi": h.version,
        "algoritma": ALG_NAMES.get(h.alg_id, "?"),
        "kdf": KDF_NAMES.get(h.kdf_id, "?"),
        "cost": h.cost,
        "salt_hex": h.salt.hex(),
        "nonce_hex": h.nonce.hex(),
        "ukuran_total": len(blob),
        "ukuran_cipherteks": len(blob) - HEADER_LEN - TAG_LEN,
    }


# ---------------------------------------------------------------------------
# 3. FITUR PENGAYAAN — enkripsi hibrida (RSA-OAEP membungkus kunci sesi)
# ---------------------------------------------------------------------------
# Alur: data dienkripsi AES-256-GCM dengan kunci sesi acak 256-bit; kunci
# sesi itu lalu dibungkus RSA-OAEP memakai kunci publik penerima. Hanya
# pemilik kunci privat yang bisa membuka kunci sesi, lalu membuka data.
# Ini pola nyata yang dipakai TLS, PGP, dan S/MIME.

HYB_MAGIC = b"BKH1"


def generate_rsa_keypair(bits: int = 3072, password: str | None = None
                         ) -> tuple[bytes, bytes]:
    """Bangkitkan pasangan kunci RSA. Kunci privat DISIMPAN TERENKRIPSI
    bila password diberikan (wajib untuk penyimpanan di disk)."""
    priv = rsa.generate_private_key(public_exponent=65537, key_size=bits)
    enc = (serialization.BestAvailableEncryption(password.encode())
           if password else serialization.NoEncryption())
    pem_priv = priv.private_bytes(serialization.Encoding.PEM,
                                  serialization.PrivateFormat.PKCS8, enc)
    pem_pub = priv.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo)
    return pem_priv, pem_pub


_OAEP = padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()),
                     algorithm=hashes.SHA256(), label=None)


def hybrid_encrypt(data: bytes, public_pem: bytes) -> bytes:
    """Kontainer hibrida: HYB_MAGIC | len(wrapped) | wrapped_key | nonce | ct."""
    pub = serialization.load_pem_public_key(public_pem)
    session_key = os.urandom(KEY_LEN)
    nonce = os.urandom(NONCE_LEN)
    ct = AESGCM(session_key).encrypt(nonce, data, HYB_MAGIC)
    wrapped = pub.encrypt(session_key, _OAEP)
    return HYB_MAGIC + struct.pack(">H", len(wrapped)) + wrapped + nonce + ct


def hybrid_decrypt(blob: bytes, private_pem: bytes,
                   key_password: str | None = None) -> bytes:
    if blob[:4] != HYB_MAGIC:
        raise CryptoError("Bukan kontainer hibrida BKH1")
    priv = serialization.load_pem_private_key(
        private_pem, password=key_password.encode() if key_password else None)
    (wlen,) = struct.unpack(">H", blob[4:6])
    wrapped = blob[6:6 + wlen]
    nonce = blob[6 + wlen:6 + wlen + NONCE_LEN]
    ct = blob[6 + wlen + NONCE_LEN:]
    try:
        session_key = priv.decrypt(wrapped, _OAEP)
        return AESGCM(session_key).decrypt(nonce, ct, HYB_MAGIC)
    except Exception as exc:
        raise CryptoError("Dekripsi hibrida gagal: kunci salah atau data diubah") from exc


# ---------------------------------------------------------------------------
# 4. Pembungkus berkas — nama berkas asli ikut dienkripsi
# ---------------------------------------------------------------------------
def pack_file(filename: str, data: bytes) -> bytes:
    """Gabungkan nama berkas + isi jadi satu plainteks sebelum dienkripsi,
    supaya nama berkas asli juga rahasia dan ikut dilindungi tag."""
    name = filename.encode("utf-8")[:255]
    return struct.pack(">H", len(name)) + name + data


def unpack_file(plain: bytes) -> tuple[str, bytes]:
    (nlen,) = struct.unpack(">H", plain[:2])
    return plain[2:2 + nlen].decode("utf-8", "replace"), plain[2 + nlen:]
