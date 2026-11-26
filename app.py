"""Dashboard Audit Energi Listrik Poliklinik USU.

Jalankan:  python -m streamlit run app.py
"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Audit Energi Poliklinik USU", layout="wide")

INK, MUTED, LINE = "#1B2420", "#5F6B66", "#E3E8E5"
GREEN, NAVY, AMBER, SOFT = "#1F7A55", "#24476B", "#C46A1C", "#9DB8AA"
FONT = "Inter, 'Segoe UI', Arial, sans-serif"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"], .stMarkdown {{ font-family: {FONT}; }}
.block-container {{ padding-top: 3.2rem; padding-bottom: 3rem; max-width: 1200px; }}
.hdr {{ border-bottom: 1px solid {LINE}; padding-bottom: 14px; margin-bottom: 22px; }}
.hdr .t {{ font-size: 28px; font-weight: 700; color: {INK}; }}
.hdr .s {{ font-size: 14px; color: {MUTED}; margin-top: 4px; }}
.kpi {{ background: #FFFFFF; border: 1px solid {LINE}; border-radius: 10px; padding: 16px 18px; min-height: 118px; }}
.kpi .l {{ font-size: 13px; color: {MUTED}; font-weight: 500; }}
.kpi .v {{ font-size: 26px; font-weight: 700; color: {INK}; margin-top: 6px; white-space: nowrap; }}
.kpi .d {{ font-size: 13px; color: {MUTED}; margin-top: 4px; }}
.kpi.hl {{ border-left: 4px solid {GREEN}; }}
.kpi.hl .v {{ color: {GREEN}; }}
.sec {{ font-size: 18px; font-weight: 600; color: {INK}; margin: 30px 0 8px; }}
table.t {{ width: 100%; border-collapse: collapse; font-size: 14px; color: {INK}; }}
table.t th {{ text-align: left; font-weight: 600; color: {MUTED}; font-size: 13px;
             border-bottom: 2px solid {INK}; padding: 9px 10px; }}
table.t td {{ border-bottom: 1px solid {LINE}; padding: 9px 10px; }}
table.t .n {{ text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }}
table.t tr.tot td {{ font-weight: 700; border-top: 2px solid {INK}; border-bottom: none; background: #F6F8F7; }}
.foot {{ font-size: 13px; color: {MUTED}; margin-top: 28px; border-top: 1px solid {LINE}; padding-top: 12px; }}
</style>
""", unsafe_allow_html=True)


def num(x, d=0):
    return f"{x:,.{d}f}".replace(",", "#").replace(".", ",").replace("#", ".")


def rp(x):
    return f"Rp {num(x)}"


def pct(x, d=1):
    return f"{num(x * 100, d)}%"


def html_table(df, num_cols, total_last=False):
    head = "".join(f'<th class="{"n" if c in num_cols else ""}">{c}</th>' for c in df.columns)
    body = ""
    for i, (_, r) in enumerate(df.iterrows()):
        cls = ' class="tot"' if total_last and i == len(df) - 1 else ""
        body += f"<tr{cls}>" + "".join(
            f'<td class="{"n" if c in num_cols else ""}">{r[c]}</td>' for c in df.columns) + "</tr>"
    st.markdown(f'<table class="t"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>',
                unsafe_allow_html=True)


# ------------------------------------------------------------------ data dan parameter
METER_AWAL, METER_AKHIR = 295_874, 299_144   # Laporan Penggunaan Energi Listrik USU, April 2024
KONSUMSI = METER_AKHIR - METER_AWAL          # 3.270 kWh
TARIF = 900            # Rp/kWh, golongan sosial 3.500 VA sampai 200 kVA (Permen ESDM No. 7 Tahun 2024)
EMISI = 0.8            # kg CO2e per kWh
HARI_LAYANAN, JAM_LAYANAN, JAM_SEBELUM, HARI_BULAN = 22, 8, 10, 30

# Jumlah dan daya alat: perkiraan kelompok untuk klinik kampus
# kolom: peralatan, jenis, jumlah, daya (W), jam/bulan sebelum, usulan, daya sesudah (W), jam/bulan sesudah
ALAT = [
    ["AC split 1 PK", "AC", 10, 800, JAM_SEBELUM * HARI_LAYANAN, "Usulan 1", 800 * 0.94, JAM_LAYANAN * HARI_LAYANAN],
    ["AC split 2 PK", "AC", 1, 1600, JAM_SEBELUM * HARI_LAYANAN, "Usulan 1", 1600 * 0.94, JAM_LAYANAN * HARI_LAYANAN],
    ["Lampu TL 36 W (dalam)", "Lampu", 60, 40, JAM_SEBELUM * HARI_LAYANAN, "Usulan 2", 18, JAM_SEBELUM * HARI_LAYANAN],
    ["Lampu koridor dan luar", "Lampu", 10, 20, 12 * HARI_BULAN, "Usulan 2", 10, 12 * HARI_BULAN],
    ["Komputer", "Komputer", 10, 120, JAM_LAYANAN * HARI_LAYANAN, "Usulan 3", 120 * 0.7, JAM_LAYANAN * HARI_LAYANAN],
    ["Kulkas obat dan vaksin", "Kulkas vaksin dan alat medis", 2, 150, 24 * HARI_BULAN, "-", 150, 24 * HARI_BULAN],
    ["Alat medis (dental unit dan autoklaf)", "Kulkas vaksin dan alat medis", 1, 1500, 4 * HARI_LAYANAN, "-", 1500, 4 * HARI_LAYANAN],
    ["Dispenser air", "Dispenser, CCTV, dan router", 2, 100, 24 * HARI_BULAN, "Usulan 3", 100, JAM_LAYANAN * HARI_LAYANAN],
    ["CCTV dan router", "Dispenser, CCTV, dan router", 1, 60, 24 * HARI_BULAN, "-", 60, 24 * HARI_BULAN],
]
df = pd.DataFrame(ALAT, columns=["Peralatan", "Jenis", "Jumlah", "Daya", "Jam", "Usulan", "Daya2", "Jam2"])
df["kWh_est"] = df["Jumlah"] * df["Daya"] * df["Jam"] / 1000
kalibrasi = KONSUMSI / df["kWh_est"].sum()          # total disamakan dengan angka meter
df["kWh"] = df["kWh_est"] * kalibrasi
df["kWh2"] = df["Jumlah"] * df["Daya2"] * df["Jam2"] / 1000 * kalibrasi

hemat = {u: (df["kWh"] - df["kWh2"])[df["Usulan"] == u].sum() for u in ["Usulan 1", "Usulan 2", "Usulan 3"]}
sesudah = df["kWh2"].sum()
kondisi = pd.DataFrame({
    "Kondisi": ["Sebelum optimasi", "Setelah usulan 1", "Setelah usulan 1 dan 2", "Setelah usulan 1, 2, dan 3"],
    "kWh": [KONSUMSI, KONSUMSI - hemat["Usulan 1"], KONSUMSI - hemat["Usulan 1"] - hemat["Usulan 2"], sesudah]})
kondisi["Biaya"] = kondisi["kWh"] * TARIF
kondisi["Emisi"] = kondisi["kWh"] * EMISI

# ------------------------------------------------------------------ tampilan
st.markdown(f"""
<div class="hdr">
  <div class="t">Dashboard Audit Energi Listrik Poliklinik USU</div>
  <div class="s">Sumber data: Laporan Penggunaan Energi Listrik USU April 2024, Poliklinik USU (nomor 82, tarif S2, daya 33 kVA).
  Meter awal {num(METER_AWAL)} kWh, meter akhir {num(METER_AKHIR)} kWh.</div>
</div>""", unsafe_allow_html=True)


def kpi(col, label, value, desc, hl=False):
    col.markdown(f'<div class="kpi{" hl" if hl else ""}"><div class="l">{label}</div>'
                 f'<div class="v">{value}</div><div class="d">{desc}</div></div>', unsafe_allow_html=True)


k = st.columns(4)
kpi(k[0], "Pemakaian listrik April 2024", f"{num(KONSUMSI)} kWh", f"Setelah optimasi: {num(sesudah)} kWh")
kpi(k[1], "Biaya listrik per bulan", rp(KONSUMSI * TARIF), f"Setelah optimasi: {rp(sesudah * TARIF)}")
kpi(k[2], "Emisi karbon per bulan", f"{num(KONSUMSI * EMISI)} kg CO2e", f"Setelah optimasi: {num(sesudah * EMISI)} kg CO2e")
kpi(k[3], "Penurunan setelah optimasi", pct(1 - sesudah / KONSUMSI),
    f"Hemat {rp((KONSUMSI - sesudah) * TARIF)} per bulan", hl=True)

BASE = dict(template="plotly_white", font=dict(family=FONT, size=13, color=INK), showlegend=False,
            margin=dict(l=10, r=20, t=50, b=10), height=360, title_font=dict(size=16, color=INK))
NOBAR = {"displayModeBar": False}

st.markdown('<div class="sec">Pemakaian listrik per jenis alat</div>', unsafe_allow_html=True)
grp = df.groupby("Jenis", as_index=False)["kWh"].sum().sort_values("kWh")
fig = go.Figure(go.Bar(y=grp["Jenis"], x=grp["kWh"], orientation="h",
                       marker_color=[GREEN if g == "AC" else SOFT for g in grp["Jenis"]],
                       text=[f"{num(v)} kWh ({pct(v / KONSUMSI)})" for v in grp["kWh"]],
                       textposition="outside", cliponaxis=False, hoverinfo="skip"))
fig.update_layout(**{**BASE, "height": 300, "margin": dict(l=10, r=20, t=10, b=10)})
fig.update_xaxes(visible=False, range=[0, grp["kWh"].max() * 1.35])
fig.update_yaxes(showgrid=False, ticksuffix="  ")
st.plotly_chart(fig, width="stretch", config=NOBAR)

st.markdown('<div class="sec">Perbandingan sebelum dan sesudah optimasi</div>', unsafe_allow_html=True)
labels = ["Sebelum", "Usulan 1", "Usulan 1 + 2", "Usulan 1 + 2 + 3"]
c1, c2 = st.columns(2)
fig = go.Figure(go.Bar(x=labels, y=kondisi["Biaya"], marker_color=[AMBER, GREEN, GREEN, GREEN],
                       text=[rp(v) for v in kondisi["Biaya"]], textposition="outside", cliponaxis=False,
                       hoverinfo="skip"))
fig.update_layout(title="Biaya listrik per bulan", **BASE)
fig.update_yaxes(visible=False, range=[0, kondisi["Biaya"].max() * 1.2])
c1.plotly_chart(fig, width="stretch", config=NOBAR)
fig = go.Figure(go.Bar(x=labels, y=kondisi["Emisi"], marker_color=[AMBER, NAVY, NAVY, NAVY],
                       text=[f"{num(v)} kg" for v in kondisi["Emisi"]], textposition="outside", cliponaxis=False,
                       hoverinfo="skip"))
fig.update_layout(title="Emisi karbon per bulan (kg CO2e)", **BASE)
fig.update_yaxes(visible=False, range=[0, kondisi["Emisi"].max() * 1.2])
c2.plotly_chart(fig, width="stretch", config=NOBAR)

html_table(pd.DataFrame({
    "Kondisi": kondisi["Kondisi"], "Pemakaian (kWh/bulan)": kondisi["kWh"].map(num),
    "Biaya (Rp/bulan)": kondisi["Biaya"].map(rp), "Emisi (kg CO2e/bulan)": kondisi["Emisi"].map(num),
    "Penurunan": (1 - kondisi["kWh"] / KONSUMSI).map(pct)}),
    ["Pemakaian (kWh/bulan)", "Biaya (Rp/bulan)", "Emisi (kg CO2e/bulan)", "Penurunan"])

st.markdown('<div class="sec">Tiga usulan optimasi</div>', unsafe_allow_html=True)
usulan = pd.DataFrame({
    "Usulan": ["1. Menaikkan suhu AC dari 24°C ke 25°C dan menyalakan AC hanya pada jam layanan (08.00 sampai 16.00)",
               "2. Mengganti lampu TL 36 W dengan LED 18 W dan lampu luar 20 W dengan LED 10 W",
               "3. Mengaktifkan mode sleep pada komputer dan memasang timer pada dispenser"],
    "Hemat (kWh/bulan)": [num(hemat[u]) for u in hemat],
    "Hemat biaya (Rp/bulan)": [rp(hemat[u] * TARIF) for u in hemat],
    "Emisi berkurang (kg CO2e/bulan)": [num(hemat[u] * EMISI) for u in hemat]})
usulan.loc[len(usulan)] = ["Total", num(KONSUMSI - sesudah), rp((KONSUMSI - sesudah) * TARIF),
                           num((KONSUMSI - sesudah) * EMISI)]
html_table(usulan, ["Hemat (kWh/bulan)", "Hemat biaya (Rp/bulan)", "Emisi berkurang (kg CO2e/bulan)"], total_last=True)

st.markdown(f'<div class="foot">Biaya = kWh × tarif Rp {num(TARIF)}/kWh. Emisi = kWh × {num(EMISI, 1)} kg CO2e/kWh. '
            'Jumlah dan daya alat merupakan perkiraan kelompok, dengan total pemakaian disamakan dengan angka meter. '
            'Kulkas vaksin, alat medis, serta CCTV dan router tidak termasuk usulan optimasi.</div>',
            unsafe_allow_html=True)