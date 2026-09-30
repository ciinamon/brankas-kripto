// app.js — logika antarmuka. Semua operasi kripto terjadi di sisi server
// (core/crypto_core.py); berkas ini hanya mengirim/menampilkan data.

const $ = (id) => document.getElementById(id);

document.querySelectorAll(".tab").forEach((t) => {
  t.onclick = () => {
    document.querySelectorAll(".tab").forEach((x) => x.classList.remove("aktif"));
    t.classList.add("aktif");
    $("panel-teks").classList.toggle("tersembunyi", t.dataset.panel !== "teks");
    $("panel-berkas").classList.toggle("tersembunyi", t.dataset.panel !== "berkas");
  };
});

const fmt = () => document.querySelector("input[name=fmt]:checked").value;
const opsi = () => ({ alg: $("alg").value, kdf: $("kdf").value, sandi: $("sandi").value });

function lapor(panel, ok, teks) {
  const el = $("pesan-" + panel);
  el.className = "pesan " + (ok ? "sukses" : "gagal");
  el.textContent = teks;
}

function tampilkanInfo(panel, info) {
  const peta = {
    algoritma: "Algoritma", kdf: "KDF", cost: "Parameter biaya",
    salt_hex: "Salt (hex)", nonce_hex: "Nonce/IV (hex)",
    ukuran_cipherteks: "Cipherteks (byte)", ukuran_total: "Total kontainer (byte)",
  };
  $("info-" + panel).innerHTML = Object.entries(peta)
    .map(([k, label]) => `<div><b>${label}</b><br>${info[k]}</div>`).join("");
}

async function enkripsiTeks() {
  const r = await fetch("/api/teks/enkripsi", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ teks: $("plainteks").value, ...opsi() }),
  });
  const d = await r.json();
  if (!d.ok) return lapor("teks", false, d.pesan);
  $("cipherteks").value = fmt() === "hex" ? d.hex : d.base64;
  window._hasil = d;
  tampilkanInfo("teks", d.info);
  lapor("teks", true, `Berhasil dienkripsi dengan ${d.info.algoritma}. Salt & nonce baru dibangkitkan acak.`);
}

async function dekripsiTeks() {
  const r = await fetch("/api/teks/dekripsi", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ cipher: $("cipherteks").value, format: fmt(), sandi: $("sandi").value }),
  });
  const d = await r.json();
  if (!d.ok) { $("plainteks").value = ""; return lapor("teks", false, "DITOLAK — " + d.pesan); }
  $("plainteks").value = d.teks;
  tampilkanInfo("teks", d.info);
  lapor("teks", true, "Tag autentikasi terverifikasi. Plainteks pulih utuh.");
}

document.querySelectorAll("input[name=fmt]").forEach((r) => {
  r.onchange = () => { if (window._hasil) $("cipherteks").value = window._hasil[fmt()]; };
});

function salin() {
  navigator.clipboard.writeText($("cipherteks").value);
  lapor("teks", true, "Cipherteks disalin ke papan klip.");
}

async function prosesBerkas(mode) {
  const input = mode === "enkripsi" ? $("berkas-asli") : $("berkas-bkp");
  if (!input.files[0]) return lapor("berkas", false, "Pilih berkas dulu.");
  const fd = new FormData();
  fd.append("berkas", input.files[0]);
  fd.append("sandi", $("sandi").value);
  fd.append("alg", $("alg").value);
  fd.append("kdf", $("kdf").value);

  lapor("berkas", true, "Memproses…");
  const r = await fetch(`/api/berkas/${mode}`, { method: "POST", body: fd });
  if (!r.ok) { const d = await r.json(); return lapor("berkas", false, "DITOLAK — " + d.pesan); }

  const blob = await r.blob();
  const nama = (r.headers.get("Content-Disposition") || "").match(/filename="?([^";]+)"?/);
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = nama ? decodeURIComponent(nama[1]) : "hasil";
  a.click();
  URL.revokeObjectURL(a.href);
  lapor("berkas", true, `Berhasil. Berkas "${a.download}" (${blob.size.toLocaleString("id")} byte) diunduh.`);
}

async function infoBerkas() {
  if (!$("berkas-bkp").files[0]) return lapor("berkas", false, "Pilih berkas .bkp dulu.");
  const fd = new FormData();
  fd.append("berkas", $("berkas-bkp").files[0]);
  const d = await (await fetch("/api/berkas/info", { method: "POST", body: fd })).json();
  if (!d.ok) return lapor("berkas", false, d.pesan);
  tampilkanInfo("berkas", d.info);
  lapor("berkas", true, "Metadata terbaca tanpa kata sandi — isi tetap terenkripsi.");
}
