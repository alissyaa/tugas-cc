"""Dashboard Efisiensi Energi Poliklinik USU.

Jalankan:  streamlit run app.py
"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Audit Energi Poliklinik USU", layout="wide")

# ------------------------------------------------------------------ warna & gaya
INK, MUTED, LINE = "#1B2420", "#5F6B66", "#E3E8E5"
GREEN, GREEN_SOFT, NAVY, AMBER = "#1F7A55", "#CFE6DA", "#24476B", "#C46A1C"
FONT = "Inter, 'Segoe UI', Arial, sans-serif"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"], .stMarkdown, .stText {{ font-family: {FONT}; }}
.block-container {{ padding-top: 3.2rem; padding-bottom: 3rem; max-width: 1320px; }}
h1, h2, h3 {{ font-family: {FONT}; color: {INK}; letter-spacing: -0.01em; }}
.hdr {{ border-bottom: 1px solid {LINE}; padding-bottom: 14px; margin-bottom: 22px; }}
.hdr .t {{ font-size: 28px; font-weight: 700; color: {INK}; }}
.hdr .s {{ font-size: 14px; color: {MUTED}; margin-top: 4px; }}
.kpi {{ background: #FFFFFF; border: 1px solid {LINE}; border-radius: 10px; padding: 16px 18px; min-height: 132px; }}
.kpi .l {{ font-size: 13px; color: {MUTED}; font-weight: 500; }}
.kpi .v {{ font-size: 26px; font-weight: 700; color: {INK}; margin-top: 6px; white-space: nowrap; }}
.kpi .d {{ font-size: 13px; color: {MUTED}; margin-top: 4px; }}
.kpi.hl {{ border-left: 4px solid {GREEN}; }}
.kpi.hl .v {{ color: {GREEN}; }}
.sec {{ font-size: 18px; font-weight: 600; color: {INK}; margin: 26px 0 6px; }}
.secd {{ font-size: 13.5px; color: {MUTED}; margin-bottom: 10px; }}
table.t {{ width: 100%; border-collapse: collapse; font-size: 14px; color: {INK}; }}
table.t th {{ text-align: left; font-weight: 600; color: {MUTED}; font-size: 12.5px;
             border-bottom: 2px solid {INK}; padding: 9px 10px; }}
table.t td {{ border-bottom: 1px solid {LINE}; padding: 9px 10px; vertical-align: top; }}
table.t .n {{ text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }}
table.t tr.tot td {{ font-weight: 700; border-top: 2px solid {INK}; border-bottom: none; background: #F6F8F7; }}
.box {{ background: #F6F8F7; border: 1px solid {LINE}; border-radius: 10px; padding: 16px 18px; font-size: 14.5px; line-height: 1.6; }}
section[data-testid="stSidebar"] {{ background: #F6F8F7; }}
button[data-baseweb="tab"] p {{ font-size: 15px; font-weight: 600; }}
button[data-baseweb="tab"][aria-selected="true"] p {{ color: {GREEN}; }}
div[data-baseweb="tab-highlight"] {{ background-color: {GREEN}; }}
.stTabs {{ margin-top: 18px; }}
</style>
""", unsafe_allow_html=True)


# ------------------------------------------------------------------ format angka Indonesia
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


# ------------------------------------------------------------------ data sumber
METER_AWAL, METER_AKHIR = 295_874, 299_144   # Laporan Penggunaan Energi Listrik USU, April 2024
KONSUMSI = METER_AKHIR - METER_AWAL
HARI_BULAN = 30

INVENTARIS_AWAL = pd.DataFrame(
    [["AC split 1 PK (ruang periksa, apotek, admin)", "AC", 10, 800],
     ["AC split 2 PK (ruang tunggu)", "AC", 1, 1600],
     ["Lampu TL 36 W + ballast (dalam)", "Lampu", 60, 40],
     ["Lampu koridor dan luar", "Lampu", 10, 20],
     ["Komputer (pendaftaran, dokter, apotek)", "Komputer", 10, 120],
     ["Kulkas obat dan vaksin", "Kulkas vaksin dan alat medis", 2, 150],
     ["Alat medis (dental unit dan autoklaf)", "Kulkas vaksin dan alat medis", 1, 1500],
     ["Dispenser air", "Dispenser, CCTV, dan router", 2, 100],
     ["CCTV dan router", "Dispenser, CCTV, dan router", 1, 60]],
    columns=["Peralatan", "Kelompok", "Jumlah", "Daya (W)"])

# ------------------------------------------------------------------ sidebar
with st.sidebar:
    st.markdown("### Parameter perhitungan")
    st.caption("Ubah nilai di bawah ini, seluruh angka dan grafik akan dihitung ulang.")
    with st.expander("Tarif dan emisi", expanded=True):
        tarif = st.number_input("Tarif listrik (Rp/kWh)", value=900, step=50,
                                help="Golongan sosial 3.500 VA sampai 200 kVA, Permen ESDM No. 7 Tahun 2024")
        emisi = st.number_input("Faktor emisi (kg CO2e/kWh)", value=0.80, step=0.05, format="%.2f")
    with st.expander("Jam operasional", expanded=True):
        hari_layanan = st.slider("Hari layanan per bulan", 15, 26, 22)
        jam_layanan = st.slider("Jam layanan per hari", 6, 12, 8)
        jam_ac_sebelum = st.slider("Jam AC dan lampu dalam menyala per hari (sebelum)", 8, 14, 10)
    with st.expander("Asumsi optimasi"):
        hemat_per_c = st.slider("Penghematan AC per kenaikan 1°C (%)", 0, 10, 6) / 100
        naik_suhu = st.slider("Kenaikan suhu AC (°C)", 0, 3, 1)
        led_dalam = st.number_input("Daya LED tube pengganti (W)", value=18, step=1)
        led_luar = st.number_input("Daya lampu LED luar pengganti (W)", value=10, step=1)
        hemat_pc = st.slider("Penghematan komputer dengan mode sleep (%)", 0, 60, 30) / 100
    with st.expander("Harga peralatan"):
        harga_led = st.number_input("LED tube (Rp/unit)", value=60_000, step=5_000)
        harga_led_luar = st.number_input("Lampu LED luar (Rp/unit)", value=35_000, step=5_000)
        harga_timer = st.number_input("Timer stopkontak (Rp/unit)", value=75_000, step=5_000)
    with st.expander("Inventaris peralatan"):
        inventaris = st.data_editor(INVENTARIS_AWAL[["Peralatan", "Jumlah", "Daya (W)"]], hide_index=True,
                                    disabled=["Peralatan"], key="inv")
        inventaris = INVENTARIS_AWAL[["Peralatan", "Kelompok"]].join(inventaris[["Jumlah", "Daya (W)"]])


# ------------------------------------------------------------------ perhitungan
def jam_sebelum(nama):
    if nama.startswith(("AC", "Lampu TL")):
        return jam_ac_sebelum * hari_layanan
    if nama.startswith("Lampu koridor"):
        return 12 * HARI_BULAN
    if nama.startswith("Komputer"):
        return jam_layanan * hari_layanan
    if nama.startswith("Alat medis"):
        return 4 * hari_layanan
    return 24 * HARI_BULAN


sb = inventaris.copy()
sb["Jam/bulan"] = sb["Peralatan"].map(jam_sebelum).astype(float)
sb["kWh estimasi"] = sb["Jumlah"] * sb["Daya (W)"] * sb["Jam/bulan"] / 1000
kalibrasi = KONSUMSI / sb["kWh estimasi"].sum() if sb["kWh estimasi"].sum() else 0
sb["kWh"] = sb["kWh estimasi"] * kalibrasi

ss = sb[["Peralatan", "Kelompok", "Jumlah", "Daya (W)", "Jam/bulan"]].copy()
ss["Daya (W)"] = ss["Daya (W)"].astype(float)
ss["Optimasi"] = "Tetap"
ss["Investasi"] = 0.0
for i, r in ss.iterrows():
    n = r["Peralatan"]
    if n.startswith("AC"):
        ss.loc[i, ["Daya (W)", "Jam/bulan", "Optimasi"]] = [r["Daya (W)"] * (1 - hemat_per_c * naik_suhu),
                                                            jam_layanan * hari_layanan, "Usulan 1"]
    elif n.startswith("Lampu TL"):
        ss.loc[i, ["Daya (W)", "Optimasi", "Investasi"]] = [led_dalam, "Usulan 2", r["Jumlah"] * harga_led]
    elif n.startswith("Lampu koridor"):
        ss.loc[i, ["Daya (W)", "Optimasi", "Investasi"]] = [led_luar, "Usulan 2", r["Jumlah"] * harga_led_luar]
    elif n.startswith("Komputer"):
        ss.loc[i, ["Daya (W)", "Optimasi"]] = [r["Daya (W)"] * (1 - hemat_pc), "Usulan 3"]
    elif n.startswith("Dispenser"):
        ss.loc[i, ["Jam/bulan", "Optimasi", "Investasi"]] = [jam_layanan * hari_layanan, "Usulan 3",
                                                             r["Jumlah"] * harga_timer]
ss["kWh"] = ss["Jumlah"] * ss["Daya (W)"] * ss["Jam/bulan"] / 1000 * kalibrasi

hemat = {u: (sb["kWh"] - ss["kWh"])[ss["Optimasi"] == u].sum() for u in ["Usulan 1", "Usulan 2", "Usulan 3"]}
modal = {u: ss.loc[ss["Optimasi"] == u, "Investasi"].sum() for u in ["Usulan 1", "Usulan 2", "Usulan 3"]}
sesudah_kwh = ss["kWh"].sum()
hemat_kwh = KONSUMSI - sesudah_kwh
hemat_rp = hemat_kwh * tarif
investasi = ss["Investasi"].sum()
payback = investasi / hemat_rp if hemat_rp else 0

sken = pd.DataFrame({
    "Kondisi": ["Sebelum optimasi", "Setelah usulan 1", "Setelah usulan 1 dan 2", "Setelah usulan 1, 2, dan 3"],
    "kWh": [KONSUMSI, KONSUMSI - hemat["Usulan 1"], KONSUMSI - hemat["Usulan 1"] - hemat["Usulan 2"], sesudah_kwh]})
sken["Biaya"] = sken["kWh"] * tarif
sken["Emisi"] = sken["kWh"] * emisi

# ------------------------------------------------------------------ header
st.markdown(f"""
<div class="hdr">
  <div class="t">Dashboard Audit Energi Listrik Poliklinik USU</div>
  <div class="s">Data meter PLN April 2024 dari Laporan Penggunaan Energi Listrik USU (Poliklinik USU, pelanggan nomor 82,
  tarif S2, daya 33 kVA). Meter awal {num(METER_AWAL)} kWh, meter akhir {num(METER_AKHIR)} kWh.</div>
</div>""", unsafe_allow_html=True)


def kpi(col, label, value, desc, hl=False):
    col.markdown(f'<div class="kpi{" hl" if hl else ""}"><div class="l">{label}</div>'
                 f'<div class="v">{value}</div><div class="d">{desc}</div></div>', unsafe_allow_html=True)


k = st.columns(4)
kpi(k[0], "Pemakaian listrik per bulan", f"{num(KONSUMSI)} kWh", f"Menjadi {num(sesudah_kwh)} kWh setelah optimasi")
kpi(k[1], "Biaya listrik per bulan", rp(KONSUMSI * tarif), f"Menjadi {rp(sesudah_kwh * tarif)} setelah optimasi")
kpi(k[2], "Emisi karbon per bulan", f"{num(KONSUMSI * emisi)} kg CO2e", f"Menjadi {num(sesudah_kwh * emisi)} kg CO2e setelah optimasi")
kpi(k[3], "Penurunan pemakaian listrik", pct(hemat_kwh / KONSUMSI), f"Hemat {num(hemat_kwh)} kWh per bulan", hl=True)
st.write("")
k = st.columns(4)
kpi(k[0], "Hemat biaya per tahun", rp(hemat_rp * 12), f"{rp(hemat_rp)} per bulan", hl=True)
kpi(k[1], "Emisi berkurang per tahun", f"{num(hemat_kwh * emisi * 12 / 1000, 1)} ton CO2e", f"{num(hemat_kwh * emisi)} kg CO2e per bulan", hl=True)
kpi(k[2], "Total biaya investasi", rp(investasi), "Lampu LED dan timer dispenser")
kpi(k[3], "Waktu balik modal", f"{num(payback, 1)} bulan", "Investasi dibagi hemat biaya per bulan")

tab1, tab2, tab3, tab4 = st.tabs(["Ringkasan", "Tabel perhitungan", "Metodologi", "Diskusi"])

BASE = dict(template="plotly_white", font=dict(family=FONT, size=13, color=INK), showlegend=False,
            margin=dict(l=10, r=20, t=56, b=10), height=380, title_font=dict(size=16, color=INK),
            hoverlabel=dict(font_family=FONT))

with tab1:
    c1, c2 = st.columns(2)
    labels = ["Sebelum", "Usulan 1", "Usulan 1 + 2", "Usulan 1 + 2 + 3"]
    fig = go.Figure(go.Bar(x=labels, y=sken["Biaya"], marker_color=[AMBER, GREEN, GREEN, GREEN],
                           text=[rp(v) for v in sken["Biaya"]], textposition="outside", cliponaxis=False,
                           hovertext=[rp(v) for v in sken["Biaya"]], hoverinfo="x+text"))
    fig.update_layout(title="Biaya listrik per bulan", **BASE)
    fig.update_yaxes(visible=False, range=[0, sken["Biaya"].max() * 1.2])
    c1.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    fig = go.Figure(go.Bar(x=labels, y=sken["Emisi"], marker_color=[AMBER, NAVY, NAVY, NAVY],
                           text=[f"{num(v)} kg" for v in sken["Emisi"]], textposition="outside", cliponaxis=False,
                           hovertext=[f"{num(v)} kg CO2e" for v in sken["Emisi"]], hoverinfo="x+text"))
    fig.update_layout(title="Emisi karbon per bulan (kg CO2e)", **BASE)
    fig.update_yaxes(visible=False, range=[0, sken["Emisi"].max() * 1.2])
    c2.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    c3, c4 = st.columns(2)
    grp = sb.groupby("Kelompok", as_index=False)["kWh"].sum().sort_values("kWh")
    fig = go.Figure(go.Bar(y=grp["Kelompok"], x=grp["kWh"], orientation="h",
                           marker_color=[GREEN if g == "AC" else "#9DB8AA" for g in grp["Kelompok"]],
                           text=[f"{num(v)} kWh ({pct(v / KONSUMSI)})" for v in grp["kWh"]],
                           textposition="outside", cliponaxis=False, hoverinfo="skip"))
    fig.update_layout(title="Pemakaian listrik per jenis alat (sebelum optimasi)", **BASE)
    fig.update_xaxes(visible=False, range=[0, grp["kWh"].max() * 1.5])
    fig.update_yaxes(showgrid=False, ticksuffix="  ")
    c3.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    fig = go.Figure(go.Waterfall(
        x=["Sebelum", "Usulan 1<br>AC", "Usulan 2<br>LED", "Usulan 3<br>Alat", "Sesudah"],
        y=[KONSUMSI, -hemat["Usulan 1"], -hemat["Usulan 2"], -hemat["Usulan 3"], 0],
        measure=["absolute", "relative", "relative", "relative", "total"],
        text=[num(KONSUMSI), f"-{num(hemat['Usulan 1'])}", f"-{num(hemat['Usulan 2'])}",
              f"-{num(hemat['Usulan 3'])}", num(sesudah_kwh)],
        textposition="outside", cliponaxis=False, hoverinfo="skip",
        decreasing=dict(marker_color=GREEN), increasing=dict(marker_color=AMBER),
        totals=dict(marker_color=NAVY), connector=dict(line=dict(color="#B7C2BD", width=1))))
    fig.update_layout(title="Penghematan dari setiap usulan (kWh per bulan)", **BASE)
    fig.update_yaxes(visible=False, range=[0, KONSUMSI * 1.15])
    c4.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    st.markdown('<div class="sec">Rincian tiga usulan optimasi</div>', unsafe_allow_html=True)
    rinci = pd.DataFrame({
        "Usulan": ["1. Mengatur suhu AC menjadi 25°C dan menyalakan AC hanya pada jam layanan",
                   "2. Mengganti lampu TL dan lampu luar dengan lampu LED",
                   "3. Mode sleep pada komputer dan timer pada dispenser"],
        "Hemat kWh/bulan": [num(hemat[u]) for u in hemat],
        "Hemat biaya/bulan": [rp(hemat[u] * tarif) for u in hemat],
        "Biaya investasi": [rp(modal[u]) for u in modal],
    })
    rinci.loc[len(rinci)] = ["Total", num(hemat_kwh), rp(hemat_rp), rp(investasi)]
    html_table(rinci, ["Hemat kWh/bulan", "Hemat biaya/bulan", "Biaya investasi"], total_last=True)

with tab2:
    st.markdown('<div class="sec">Tabel 1. Pemakaian listrik sebelum optimasi</div>'
                f'<div class="secd">Total estimasi {num(sb["kWh estimasi"].sum(), 1)} kWh disesuaikan dengan angka meter '
                f'{num(KONSUMSI)} kWh menggunakan faktor kalibrasi {num(kalibrasi, 3)}.</div>', unsafe_allow_html=True)
    t1 = pd.DataFrame({
        "Peralatan": sb["Peralatan"], "Jumlah": sb["Jumlah"].map(num), "Daya (W)": sb["Daya (W)"].map(num),
        "Jam/bulan": sb["Jam/bulan"].map(num), "kWh estimasi": sb["kWh estimasi"].map(lambda v: num(v, 1)),
        "kWh terkalibrasi": sb["kWh"].map(lambda v: num(v, 1)),
        "Persentase": (sb["kWh"] / KONSUMSI).map(pct)})
    t1.loc[len(t1)] = ["Total", "", "", "", num(sb["kWh estimasi"].sum(), 1), num(sb["kWh"].sum(), 1), "100%"]
    html_table(t1, ["Jumlah", "Daya (W)", "Jam/bulan", "kWh estimasi", "kWh terkalibrasi", "Persentase"], total_last=True)

    st.markdown('<div class="sec">Tabel 2. Pemakaian listrik setelah optimasi</div>'
                '<div class="secd">Kulkas vaksin, alat medis, serta CCTV dan router tidak diubah.</div>',
                unsafe_allow_html=True)
    t2 = pd.DataFrame({
        "Peralatan": ss["Peralatan"], "Usulan": ss["Optimasi"], "Jumlah": ss["Jumlah"].map(num),
        "Daya (W)": ss["Daya (W)"].map(num), "Jam/bulan": ss["Jam/bulan"].map(num),
        "kWh terkalibrasi": ss["kWh"].map(lambda v: num(v, 1)), "Investasi": ss["Investasi"].map(rp)})
    t2.loc[len(t2)] = ["Total", "", "", "", "", num(sesudah_kwh, 1), rp(investasi)]
    html_table(t2, ["Jumlah", "Daya (W)", "Jam/bulan", "kWh terkalibrasi", "Investasi"], total_last=True)

    st.markdown('<div class="sec">Tabel 3. Perbandingan sebelum dan sesudah</div>', unsafe_allow_html=True)
    t3 = pd.DataFrame({
        "Kondisi": sken["Kondisi"], "kWh/bulan": sken["kWh"].map(num), "Biaya/bulan": sken["Biaya"].map(rp),
        "Emisi (kg CO2e)": sken["Emisi"].map(num), "Penurunan": (1 - sken["kWh"] / KONSUMSI).map(pct)})
    html_table(t3, ["kWh/bulan", "Biaya/bulan", "Emisi (kg CO2e)", "Penurunan"])

with tab3:
    a, b = st.columns(2)
    a.markdown('<div class="sec">Rumus</div><div class="box">'
               'kWh = jumlah alat × daya (W) × jam pemakaian ÷ 1.000<br>'
               'Faktor kalibrasi = kWh meter ÷ total kWh estimasi<br>'
               'Biaya = kWh × tarif listrik<br>'
               'Emisi = kWh × faktor emisi<br>'
               'Waktu balik modal = total investasi ÷ hemat biaya per bulan</div>', unsafe_allow_html=True)
    b.markdown('<div class="sec">Langkah perhitungan</div><div class="box">'
               '1. Total pemakaian diambil dari data meter PLN Poliklinik USU bulan April 2024.<br>'
               '2. Pemakaian setiap alat dihitung dari perkiraan jumlah alat, daya, dan jam pemakaian.<br>'
               '3. Hasil perkiraan disesuaikan dengan faktor kalibrasi agar totalnya sama dengan angka meter.<br>'
               '4. Nilai per tahun dihitung dari nilai per bulan dikali 12.</div>', unsafe_allow_html=True)
    st.markdown('<div class="sec">Parameter yang digunakan</div>', unsafe_allow_html=True)
    html_table(pd.DataFrame({
        "Parameter": ["Tarif listrik", "Faktor emisi", "Hari layanan per bulan", "Jam layanan per hari",
                      "Jam AC dan lampu dalam menyala per hari (sebelum)", "Penghematan AC per kenaikan 1°C",
                      "Kenaikan suhu AC", "Penghematan komputer dengan mode sleep"],
        "Nilai": [f"{rp(tarif)}/kWh", f"{num(emisi, 2)} kg CO2e/kWh", f"{hari_layanan} hari", f"{jam_layanan} jam",
                  f"{jam_ac_sebelum} jam", pct(hemat_per_c, 0), f"{naik_suhu}°C", pct(hemat_pc, 0)]}), ["Nilai"])

with tab4:
    st.markdown('<div class="sec">Kapan penghematan biaya justru merugikan pengguna?</div>', unsafe_allow_html=True)
    html_table(pd.DataFrame({
        "No": ["1", "2", "3", "4"],
        "Risiko bagi pengguna": [
            "Suhu AC terlalu tinggi membuat pasien yang sedang sakit tidak nyaman.",
            "Lampu terlalu redup membuat dokter kurang teliti saat memeriksa pasien.",
            "AC dan lampu yang mati otomatis mengganggu pasien yang datang di luar jam layanan.",
            "Mematikan kulkas vaksin atau alat medis membahayakan keselamatan pasien."],
        "Cara mencegahnya": [
            "Suhu hanya dinaikkan menjadi 25°C, dan ruang tindakan tidak ikut diubah.",
            "Lampu LED yang dipilih memiliki tingkat terang yang sama dengan lampu lama.",
            "Petugas tetap bisa menyalakan AC dan lampu secara manual.",
            "Kulkas vaksin dan alat medis tetap menyala 24 jam dan tidak termasuk usulan optimasi."]}), [])