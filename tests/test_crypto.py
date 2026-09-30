"""Unit test fungsi inti (pustaka bawaan `unittest`, tanpa dependensi tambahan).

Jalankan dari akar proyek:
    python -m unittest discover -s tests -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import crypto_core as cc

PWD = "sandi-uji-yang-cukup-panjang"


class TestKebenaran(unittest.TestCase):
    """UT-01 — dekripsi harus mengembalikan plainteks yang persis sama."""

    def test_roundtrip_kedua_algoritma(self):
        data = b"Data rahasia: NIK 3207010101000001" * 10
        for alg in (cc.ALG_AES_GCM, cc.ALG_CHACHA20):
            with self.subTest(alg=cc.ALG_NAMES[alg]):
                blob = cc.encrypt(data, PWD, alg_id=alg)
                self.assertEqual(cc.decrypt(blob, PWD), data)

    def test_berkas_biner_besar_utuh(self):
        """UT-02 — data biner 512 KB tetap utuh byte per byte."""
        data = os.urandom(512 * 1024)
        blob = cc.encrypt(data, PWD, alg_id=cc.ALG_CHACHA20)
        self.assertEqual(cc.decrypt(blob, PWD), data)


class TestPenolakan(unittest.TestCase):
    """UT-03 & UT-04 — aplikasi wajib menolak sandi salah dan data yang diubah."""

    def test_sandi_salah_ditolak(self):
        blob = cc.encrypt(b"rahasia", PWD)
        with self.assertRaises(cc.CryptoError):
            cc.decrypt(blob, PWD + "x")

    def test_satu_bit_diubah_ditolak(self):
        blob = cc.encrypt(b"A" * 128, PWD)
        posisi = {
            "byte versi header": 4,
            "field cost": 8,
            "salt": 12,
            "nonce": 30,
            "awal cipherteks": cc.HEADER_LEN,
            "tag terakhir": len(blob) - 1,
        }
        for nama, pos in posisi.items():
            with self.subTest(bagian=nama):
                rusak = bytearray(blob)
                rusak[pos] ^= 0x01          # balik satu bit
                with self.assertRaises(cc.CryptoError):
                    cc.decrypt(bytes(rusak), PWD)


class TestKeacakan(unittest.TestCase):
    """UT-05 — salt & nonce wajib acak di setiap enkripsi (anti nonce-reuse)."""

    def test_cipherteks_tidak_pernah_berulang(self):
        a = cc.encrypt(b"sama", PWD)
        b = cc.encrypt(b"sama", PWD)
        self.assertNotEqual(a, b)
        self.assertNotEqual(cc.Header.unpack(a).nonce, cc.Header.unpack(b).nonce)
        self.assertNotEqual(cc.Header.unpack(a).salt, cc.Header.unpack(b).salt)
        self.assertEqual(cc.decrypt(a, PWD), cc.decrypt(b, PWD))


class TestKDF(unittest.TestCase):
    """UT-06 — KDF deterministik untuk salt yang sama, berbeda untuk salt lain."""

    def test_kunci_terikat_salt(self):
        for kdf in (cc.KDF_PBKDF2, cc.KDF_SCRYPT):
            with self.subTest(kdf=cc.KDF_NAMES[kdf]):
                salt = os.urandom(cc.SALT_LEN)
                k1, _ = cc.derive_key(PWD, salt, kdf)
                k2, _ = cc.derive_key(PWD, salt, kdf)
                k3, _ = cc.derive_key(PWD, os.urandom(cc.SALT_LEN), kdf)
                self.assertEqual(k1, k2)
                self.assertEqual(len(k1), 32)      # 256 bit
                self.assertNotEqual(k1, k3)


class TestMetadata(unittest.TestCase):
    """UT-07 — metadata kontainer terbaca tanpa kata sandi."""

    def test_describe(self):
        blob = cc.encrypt(b"x" * 100, PWD, alg_id=cc.ALG_CHACHA20,
                          kdf_id=cc.KDF_PBKDF2)
        info = cc.describe(blob)
        self.assertEqual(info["algoritma"], "ChaCha20-Poly1305")
        self.assertEqual(info["kdf"], "PBKDF2-HMAC-SHA256")
        self.assertEqual(info["ukuran_cipherteks"], 100)

    def test_berkas_asing_ditolak(self):
        with self.assertRaises(cc.CryptoError):
            cc.decrypt(b"ini bukan berkas brankas sama sekali", PWD)


class TestHibrida(unittest.TestCase):
    """UT-08 (pengayaan) — kunci sesi AES dibungkus RSA-OAEP."""

    @classmethod
    def setUpClass(cls):
        cls.priv, cls.pub = cc.generate_rsa_keypair(2048, password="lindungi-kunci")

    def test_roundtrip_hibrida(self):
        data = b"kunci sesi dibungkus RSA-OAEP" * 50
        blob = cc.hybrid_encrypt(data, self.pub)
        self.assertEqual(cc.hybrid_decrypt(blob, self.priv, "lindungi-kunci"), data)

    def test_hibrida_diubah_ditolak(self):
        blob = bytearray(cc.hybrid_encrypt(b"pesan", self.pub))
        blob[-1] ^= 0x01
        with self.assertRaises(cc.CryptoError):
            cc.hybrid_decrypt(bytes(blob), self.priv, "lindungi-kunci")


if __name__ == "__main__":
    unittest.main(verbosity=2)
