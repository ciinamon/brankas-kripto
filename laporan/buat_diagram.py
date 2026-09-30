"""Menggambar diagram alur dan arsitektur untuk laporan.
Jalankan: python laporan/buat_diagram.py
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gambar")
os.makedirs(DIR, exist_ok=True)

BIRU, ORANYE, HIJAU, ABU, MERAH = "#4f9cf9", "#f0883e", "#3fb950", "#8b949e", "#f85149"


def kotak(ax, x, y, w, h, teks, warna, fs=8.2, teks_warna="white"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.012,rounding_size=0.02",
                                fc=warna, ec="none"))
    ax.text(x + w / 2, y + h / 2, teks, ha="center", va="center",
            fontsize=fs, color=teks_warna, weight="medium", linespacing=1.45)


def panah(ax, xy1, xy2, label=None, warna="#57606a"):
    ax.add_patch(FancyArrowPatch(xy1, xy2, arrowstyle="-|>", mutation_scale=11,
                                 lw=1.2, color=warna, shrinkA=2, shrinkB=2))
    if label:
        ax.text((xy1[0] + xy2[0]) / 2, (xy1[1] + xy2[1]) / 2 + .022, label,
                ha="center", fontsize=7, color="#57606a", style="italic")


def kanvas(w=9.2, h=3.4):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off"); ax.grid(False)
    return fig, ax


# --- Gambar 1: alur enkripsi ------------------------------------------------
fig, ax = kanvas()
kotak(ax, .01, .60, .15, .20, "Kata sandi\npengguna", ABU)
kotak(ax, .01, .26, .15, .20, "Salt acak\n16 byte\n(os.urandom)", HIJAU)
kotak(ax, .21, .43, .16, .20, "KDF\nscrypt / PBKDF2\n/ Argon2id", ORANYE)
kotak(ax, .42, .43, .15, .20, "Kunci 256 bit", BIRU)
kotak(ax, .63, .06, .16, .18, "Nonce acak\n12 byte", HIJAU)
kotak(ax, .63, .78, .16, .17, "Plainteks\n(teks / berkas)", ABU)
kotak(ax, .63, .40, .16, .22, "AEAD\nAES-256-GCM\natau ChaCha20", ORANYE)
kotak(ax, .86, .31, .13, .40,
      "Kontainer\n.bkp\n\nheader 39 B\n+ cipherteks\n+ tag 16 B", BIRU, fs=7.6)

panah(ax, (.16, .70), (.29, .63))
panah(ax, (.16, .36), (.29, .43))
panah(ax, (.37, .53), (.42, .53))
panah(ax, (.57, .52), (.63, .51))
panah(ax, (.71, .78), (.71, .62))
panah(ax, (.71, .24), (.71, .40))
panah(ax, (.79, .51), (.86, .51))
ax.text(.50, .18, "header dipakai sebagai AAD\nsehingga ikut dilindungi tag",
        ha="center", fontsize=7, color="#57606a", style="italic")
fig.tight_layout(); fig.savefig(os.path.join(DIR, "g31_alur_enkripsi.png"), dpi=180)
plt.close(fig)

# --- Gambar 2: alur dekripsi ------------------------------------------------
fig, ax = kanvas()
kotak(ax, .01, .42, .15, .22, "Kontainer\n.bkp", BIRU)
kotak(ax, .21, .42, .15, .22, "Baca header\nmagic, alg,\nkdf, salt, nonce", ABU)
kotak(ax, .41, .42, .15, .22, "Turunkan\nkunci dari\nsandi + salt", ORANYE)
kotak(ax, .61, .42, .16, .22, "Verifikasi tag\nlalu dekripsi", ORANYE)
kotak(ax, .82, .66, .17, .20, "Tag cocok\nPlainteks pulih", HIJAU)
kotak(ax, .82, .16, .17, .22, "Tag tidak cocok\nDITOLAK\n(sandi salah atau\ndata diubah)", MERAH, fs=7.6)
for a, b in [((.16, .53), (.21, .53)), ((.36, .53), (.41, .53)), ((.56, .53), (.61, .53))]:
    panah(ax, a, b)
panah(ax, (.77, .58), (.82, .72), warna=HIJAU)
panah(ax, (.77, .48), (.82, .32), warna=MERAH)
fig.tight_layout(); fig.savefig(os.path.join(DIR, "g32_alur_dekripsi.png"), dpi=180)
plt.close(fig)

# --- Gambar 3: arsitektur ---------------------------------------------------
fig, ax = kanvas(9.2, 3.6)
kotak(ax, .03, .20, .24, .58,
      "PERAMBAN\n\nindex.html\nstyle.css\napp.js\n\n(hanya tampilan,\ntanpa operasi kripto)", ABU, fs=7.8)
kotak(ax, .37, .20, .26, .58,
      "SERVER FLASK\napp/app.py\n\n/api/teks/enkripsi\n/api/teks/dekripsi\n"
      "/api/berkas/enkripsi\n/api/berkas/dekripsi", BIRU, fs=7.8)
kotak(ax, .72, .20, .25, .58,
      "MODUL KRIPTO\ncore/crypto_core.py\n\nderive_key()\nencrypt()\ndecrypt()\n"
      "hybrid_encrypt()", ORANYE, fs=7.8)
panah(ax, (.27, .56), (.37, .56), "HTTP JSON / multipart")
panah(ax, (.37, .40), (.27, .40), "hasil / galat")
panah(ax, (.63, .49), (.72, .49), "panggilan fungsi")
ax.text(.5, .09, "Kata sandi hanya hidup di memori proses server selama satu permintaan; "
                 "tidak ditulis ke disk, sesi, maupun log.",
        ha="center", fontsize=7.5, color="#57606a", style="italic")
fig.tight_layout(); fig.savefig(os.path.join(DIR, "g33_arsitektur.png"), dpi=180)
plt.close(fig)

print("Diagram dibuat di", DIR)
for f in sorted(os.listdir(DIR)):
    print("  ", f)
