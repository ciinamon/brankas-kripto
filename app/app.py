"""
app.py — Antarmuka web Brankas Berkas Pribadi Terenkripsi (Flask).

Jalankan:  python app.py    lalu buka http://127.0.0.1:5000

Catatan keamanan antarmuka:
  - Kata sandi hanya dipakai sesaat di memori untuk menurunkan kunci,
    tidak pernah disimpan ke disk, session, maupun log.
  - Semua operasi kripto didelegasikan ke core/crypto_core.py.
"""
import base64
import io
import os
import sys

from flask import Flask, jsonify, render_template, request, send_file

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import crypto_core as cc

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024 * 1024   # batas unggah 64 MB


def _params(src):
    """Ambil pilihan algoritma & KDF dari form, dengan default aman."""
    alg = cc.ALG_IDS.get(src.get("alg", "AES-256-GCM"), cc.ALG_AES_GCM)
    kdf = cc.KDF_IDS.get(src.get("kdf", "scrypt"), cc.KDF_SCRYPT)
    return alg, kdf


@app.route("/")
def index():
    return render_template("index.html",
                           algoritma=list(cc.ALG_NAMES.values()),
                           kdf=list(cc.KDF_NAMES.values()))


# --- Teks -------------------------------------------------------------------
@app.post("/api/teks/enkripsi")
def enkripsi_teks():
    d = request.get_json(force=True)
    alg, kdf = _params(d)
    try:
        blob = cc.encrypt(d["teks"].encode("utf-8"), d["sandi"],
                          alg_id=alg, kdf_id=kdf)
    except cc.CryptoError as e:
        return jsonify(ok=False, pesan=str(e)), 400
    return jsonify(ok=True,
                   base64=base64.b64encode(blob).decode(),
                   hex=blob.hex(),
                   info=cc.describe(blob))


@app.post("/api/teks/dekripsi")
def dekripsi_teks():
    d = request.get_json(force=True)
    try:
        raw = d["cipher"].strip()
        blob = bytes.fromhex(raw) if d.get("format") == "hex" else base64.b64decode(raw)
        plain = cc.decrypt(blob, d["sandi"])
        return jsonify(ok=True, teks=plain.decode("utf-8", "replace"),
                       info=cc.describe(blob))
    except cc.CryptoError as e:
        return jsonify(ok=False, pesan=str(e)), 400
    except Exception:
        return jsonify(ok=False, pesan="Cipherteks tidak valid / bukan format BKP1"), 400


# --- Berkas -----------------------------------------------------------------
@app.post("/api/berkas/enkripsi")
def enkripsi_berkas():
    f = request.files.get("berkas")
    if not f or not f.filename:
        return jsonify(ok=False, pesan="Berkas belum dipilih"), 400
    alg, kdf = _params(request.form)
    data = cc.pack_file(f.filename, f.read())
    try:
        blob = cc.encrypt(data, request.form.get("sandi", ""), alg_id=alg, kdf_id=kdf)
    except cc.CryptoError as e:
        return jsonify(ok=False, pesan=str(e)), 400
    return send_file(io.BytesIO(blob), as_attachment=True,
                     download_name=f.filename + ".bkp",
                     mimetype="application/octet-stream")


@app.post("/api/berkas/dekripsi")
def dekripsi_berkas():
    f = request.files.get("berkas")
    if not f:
        return jsonify(ok=False, pesan="Berkas belum dipilih"), 400
    try:
        nama, isi = cc.unpack_file(cc.decrypt(f.read(), request.form.get("sandi", "")))
    except cc.CryptoError as e:
        return jsonify(ok=False, pesan=str(e)), 400
    except Exception:
        return jsonify(ok=False, pesan="Berkas rusak atau bukan kontainer BKP1"), 400
    return send_file(io.BytesIO(isi), as_attachment=True,
                     download_name=nama or "hasil-dekripsi",
                     mimetype="application/octet-stream")


@app.post("/api/berkas/info")
def info_berkas():
    """Baca metadata kontainer tanpa kata sandi (untuk ditampilkan saat demo)."""
    f = request.files.get("berkas")
    try:
        return jsonify(ok=True, info=cc.describe(f.read()))
    except Exception as e:
        return jsonify(ok=False, pesan=str(e)), 400


if __name__ == "__main__":
    app.run(debug=True, port=5000)
