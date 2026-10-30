"""Intumwa: district early-warning system for Rwanda's crop farmers and livestock keepers.

Vulnerability comes from the NISR Agriculture Household Survey 2024.
Hazard comes from a rainfall file (data/rainfall_anomaly.csv) or from a clearly labelled scenario.
"""
import os
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import zlib
import html
import apis
from i18n import TR
import streamlit as st

DARK_CSS = '<style>\n.stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {background:#0E1A13 !important; color:#E6EEE8;}\nsection[data-testid="stSidebar"], section[data-testid="stSidebar"] > div {background:#13241A !important; border-color:#24392C !important;}\n.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp p, .stApp li, .stApp label, .stApp summary,\n[data-testid="stMarkdownContainer"], [data-testid="stCaptionContainer"], [data-testid="stMetricValue"],\n[data-testid="stMetricLabel"], .stTabs [data-baseweb="tab"] p {color:#E6EEE8 !important;}\n.h2, .h3, .kpi-v, .rank-b b, .eq b {color:#E6EEE8 !important;}\n.muted, .kpi-l, .kpi-s, .rank-s, .phone-h, .phone-m, .side-sub, .foot, .eq span {color:#9FB3A6 !important;}\n.side-brand {color:#7FD9A8 !important;}\n.kpi, .step, .eq > div, .phone, [data-testid="stMetric"] {background:#1B2E23 !important; border-color:#2B4636 !important;}\n.bubble {background:#243A2D !important; border-color:#2B4636 !important; color:#E6EEE8 !important;}\n.rank {border-bottom-color:#24392C !important;}\n.rank-n {background:#24392C !important; color:#9BE0B8 !important;}\n.bar {background:#24392C !important;}\n.driver {background:#1F3A2B !important; color:#9BE0B8 !important;}\n.callout {background:#3A2F10 !important; border-color:#6B5516 !important; color:#F2DDA0 !important;}\n.good {background:#12301F !important; border-color:#1E5434 !important; color:#9BE0B8 !important;}\n.stTabs [data-baseweb="tab"] {background:#1B2E23 !important;}\n.stTabs [aria-selected="true"] {background:#0B5D3B !important;}\n.stApp input, .stApp textarea, [data-baseweb="select"] > div, [data-baseweb="input"], [data-baseweb="base-input"] {background:#1B2E23 !important; color:#E6EEE8 !important; border-color:#2B4636 !important;}\n[data-baseweb="popover"], [data-baseweb="popover"] ul, [data-baseweb="menu"] {background:#1B2E23 !important; color:#E6EEE8 !important;}\n[data-baseweb="popover"] li, [data-baseweb="popover"] [role="option"] {background:#1B2E23 !important; color:#E6EEE8 !important;}\n[data-baseweb="tag"] {background:#2B4636 !important;}\nbutton[data-testid="stBaseButton-secondary"], .stDownloadButton button {background:#1B2E23 !important; color:#E6EEE8 !important; border-color:#2B4636 !important;}\n[data-testid="stExpander"] details {background:#13241A !important; border-color:#2B4636 !important;}\n[data-testid="stForm"] {border-color:#2B4636 !important;}\n</style>'

st.set_page_config(page_title="Intumwa: early warning for Rwandan farmers", page_icon="🌾", layout="wide")
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# ---------- data ----------
@st.cache_data
def load():
    vuln = pd.read_csv(f"{DATA}/district_vulnerability.csv")
    cent = pd.read_csv(f"{DATA}/district_centroids.csv")
    yields = pd.read_csv(f"{DATA}/district_yields.csv")
    return vuln.merge(cent, on="district"), yields

df, yields = load()

@st.cache_data
def load_report():
    """Province-level tables transcribed from the NISR AHS 2024 report (Tables 26, 27, 50, 51, 53)."""
    return (pd.read_csv(f"{DATA}/ahs_report_milk_monthly.csv"), pd.read_csv(f"{DATA}/ahs_report_climate_info.csv"),
            pd.read_csv(f"{DATA}/ahs_report_shares.csv"))

milk, climate, shares = load_report()

@st.cache_data
def load_bench():
    return pd.read_csv(f"{DATA}/ahs_report_province_benchmarks.csv")

bench = load_bench()

NORMALS = apis.load_normals(f"{DATA}/rainfall_normals.csv")

@st.cache_data(ttl=3600, show_spinner="Fetching live rainfall (Open-Meteo)...")
def live_rain():
    return apis.fetch_open_meteo(pd.read_csv(f"{DATA}/district_centroids.csv")[["district", "lat", "lon"]], NORMALS)

@st.cache_data(ttl=6 * 3600, show_spinner=False)
def nisr_catalog():
    return apis.fetch_nisr_catalog()
RAIN_FILE = f"{DATA}/rainfall_anomaly.csv"
has_rain = os.path.exists(RAIN_FILE)
districts = sorted(df["district"])

# the seven AHS indicators behind the vulnerability index: column -> (English, Kinyarwanda)
DRIVERS = {
    "poverty_rate": ("poverty", "ubukene"),
    "extreme_poverty_rate": ("extreme poverty", "ubukene bukabije"),
    "no_extension": ("no extension advice", "kutagira inama"),
    "no_account": ("no bank or mobile-money account", "kutagira konti"),
    "no_improved_seed": ("no improved seed", "imbuto gakondo"),
    "small_farm_lt_half_ha": ("land under 0.5 ha", "ubutaka buto"),
    "no_cooperative": ("not in a cooperative", "kutagira koperative"),
}
TIER_RW = {"Low": "Ibyago bike", "Elevated": "Ibyago biringaniye", "High": "Ibyago byinshi"}
TIER_COLOR = {"Low": "#2E8B57", "Elevated": "#E8A317", "High": "#C0392B", "Insufficient data": "#9AA5A0"}
PALETTE = ["#0B6B45", "#E8A317", "#5B7F95", "#C0392B", "#8E6C8A", "#2E8B57", "#9AA5A0", "#B5651D", "#3D6E8F", "#7A9E3B", "#A0527C"]
px.defaults.color_discrete_sequence = PALETTE

st.markdown("""<style>
.block-container {padding-top: 1.3rem; padding-bottom: 3rem; max-width: 1320px;}
header[data-testid="stHeader"] {background: transparent;}
.hero {background: linear-gradient(120deg,#0B5D3B 0%,#0F7A4C 55%,#17935B 100%); border-radius: 18px; padding: 24px 30px; color:#fff; display:flex; justify-content:space-between; align-items:center; gap:24px; flex-wrap:wrap; box-shadow:0 8px 24px rgba(11,93,59,.18); margin-bottom: 16px;}
.brand {font-size: 2.4rem; font-weight: 800; letter-spacing:-0.02em; line-height:1.1;}
.tag {font-size:1.05rem; font-weight:500; opacity:.96; margin-top:4px;}
.sub {font-size:.9rem; opacity:.8; margin-top:2px;}
.hero-r {display:flex; gap:8px; flex-wrap:wrap; justify-content:flex-end; max-width:540px;}
.chip {display:inline-block; padding:5px 12px; border-radius:999px; font-size:.78rem; font-weight:600;}
.chip-w {background:rgba(255,255,255,.16); border:1px solid rgba(255,255,255,.3); color:#fff;}
.chip-a {background:#FFE08A; color:#5a3d00;}
.kpi {min-height:118px; border-radius:14px; padding:14px 16px; background:#fff; border:1px solid #E1EAE4; box-shadow:0 1px 2px rgba(20,35,27,.05); border-left:5px solid #9AA5A0; height:100%;}
.kpi-high {border-left-color:#C0392B;} .kpi-elev {border-left-color:#E8A317;} .kpi-neutral {border-left-color:#0B6B45;}
.kpi-l {font-size:.72rem; color:#5B6B62; font-weight:700; text-transform:uppercase; letter-spacing:.05em;}
.kpi-v {font-size:2.1rem; font-weight:800; line-height:1.15; color:#14231B;}
.kpi-s {font-size:.8rem; color:#6B7B72;}
.h2 {font-size:1.4rem; font-weight:700; color:#14231B; margin:.3rem 0 .1rem;}
.h3 {font-size:1.05rem; font-weight:700; margin:.1rem 0 .5rem;}
.muted {color:#5B6B62; font-size:.9rem; margin-bottom:.7rem;}
.rank {display:flex; gap:10px; padding:8px 0; border-bottom:1px solid #EDF2EE;}
.rank-n {width:24px; height:24px; border-radius:50%; background:#EAF3EE; color:#0B5D3B; font-weight:700; font-size:.8rem; display:flex; align-items:center; justify-content:center; flex:none; margin-top:2px;}
.rank-b {flex:1; min-width:0;}
.rank-t {display:flex; justify-content:space-between; align-items:center;}
.pill {color:#fff; font-size:.68rem; font-weight:700; padding:2px 9px; border-radius:999px;}
.bar {height:6px; background:#EDF2EE; border-radius:99px; margin:5px 0 3px; overflow:hidden;}
.bar > div {height:100%; border-radius:99px;}
.rank-s {font-size:.74rem; color:#6B7B72;}
.phone {background:#F2F6F3; border:1px solid #DDE7E0; border-radius:22px; padding:14px 16px 12px; min-height:200px;}
.phone-h {font-size:.72rem; font-weight:700; text-transform:uppercase; letter-spacing:.06em; color:#5B6B62; margin-bottom:10px;}
.bubble {background:#fff; border:1px solid #DDE7E0; border-radius:4px 16px 16px 16px; padding:12px 14px; font-size:.95rem; line-height:1.45; box-shadow:0 1px 2px rgba(20,35,27,.05);}
.phone-m {font-size:.72rem; color:#6B7B72; margin-top:8px;}
.eq {display:flex; align-items:stretch; gap:10px; margin-bottom:12px;}
.eq > div {flex:1; background:#fff; border:1px solid #E1EAE4; border-radius:14px; padding:10px 12px; display:flex; flex-direction:column;}
.eq > i {flex:none; align-self:center; font-style:normal; font-weight:700; color:#6B7B72;}
.eq span {font-size:.7rem; text-transform:uppercase; letter-spacing:.05em; color:#5B6B62; font-weight:700;}
.eq b {font-size:1.7rem; font-weight:800;}
.eq em {font-style:normal; align-self:flex-start; color:#fff; font-size:.68rem; font-weight:700; padding:2px 9px; border-radius:99px; margin-top:2px;}
.ussd {background:#10241A; color:#B6F2CE; font-family:Consolas,'Courier New',monospace; border-radius:18px; padding:18px 20px; font-size:.95rem; line-height:1.5; white-space:pre-wrap; min-height:190px; border:6px solid #1C3A2B;}
.driver {display:inline-block; background:#EAF3EE; color:#0B5D3B; font-weight:600; font-size:.8rem; padding:4px 11px; border-radius:99px; margin:2px 6px 2px 0;}
.callout {background:#FFF8E1; border:1px solid #F3DFA0; border-radius:12px; padding:10px 14px; font-size:.9rem; color:#5a4300; margin:6px 0 10px;}
.good {background:#E8F5EC; border:1px solid #BFE0CB; border-radius:12px; padding:10px 14px; font-size:.9rem; color:#0B5D3B; margin:6px 0 10px;}
.step {min-height:170px; background:#fff; border:1px solid #E1EAE4; border-radius:14px; padding:12px 14px; height:100%;}
.step b {color:#0B5D3B;}
[data-testid="stMetric"] {background:#fff; border:1px solid #E1EAE4; border-radius:14px; padding:12px 14px; box-shadow:0 1px 2px rgba(20,35,27,.05);}
.stTabs [data-baseweb="tab-list"] {gap:6px; border-bottom:none; flex-wrap:wrap;}
.stTabs [data-baseweb="tab"] {background:#F2F6F3; border-radius:10px; padding:8px 14px; height:auto;}
.stTabs [aria-selected="true"] {background:#0B5D3B;}
.stTabs [aria-selected="true"] p {color:#fff !important;}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] {display:none;}
section[data-testid="stSidebar"] {background:#F2F6F3; border-right:1px solid #E1EAE4;}
.side-brand {font-size:1.6rem; font-weight:800; color:#0B5D3B; line-height:1.1;}
.side-sub {font-size:.8rem; color:#5B6B62; margin-bottom:.8rem;}
.foot {margin-top:2.2rem; padding-top:1rem; border-top:1px solid #E1EAE4; color:#6B7B72; font-size:.8rem; line-height:1.5;}
</style>""", unsafe_allow_html=True)

# ---------- sidebar: hazard input ----------
_brand = st.sidebar.empty()
UI_LANG = st.sidebar.radio("Language / Ururimi", ["English", "Kinyarwanda"], horizontal=True, key="ui_lang")

def T(s):
    """Translate an interface string when Kinyarwanda is selected. Unknown strings stay in English."""
    return TR.get(s, s) if UI_LANG == "Kinyarwanda" else s

DARK = st.sidebar.radio(T("Theme"), ["Light", "Dark"], horizontal=True, format_func=T, key="ui_theme") == "Dark"
_brand.markdown(f'<div class="side-brand">Intumwa</div><div class="side-sub">{T("Control panel: choose the weather hazard to explore")}</div>', unsafe_allow_html=True)
if DARK:
    st.markdown(DARK_CSS, unsafe_allow_html=True)

def show_chart(target, fig, **kw):
    """Draw a Plotly chart; in dark mode use a dark template with a transparent background."""
    if DARK:
        fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        try:
            return target.plotly_chart(fig, theme=None, **kw)
        except TypeError:   # this Streamlit version has no theme argument
            pass
    return target.plotly_chart(fig, **kw)

hazard_type = st.sidebar.radio(T("Hazard type"), ["Drought", "Heavy rain"], horizontal=True, format_func=T, key="hazard_type")

live_df, live_status = None, None
sources = ["Scenario"] + (["Rainfall data file"] if has_rain else []) + (["Live forecast (Open-Meteo)"] if NORMALS is not None else [])
if len(sources) > 1:
    source = st.sidebar.radio(T("Hazard input"), sources, format_func=T, key="hazard_source", help="Scenario = you set the rainfall change. Live = real rainfall of the last 30 days "
                              "plus the 14-day forecast, compared with the 1991-2020 normal.")
else:
    source = "Scenario"
    st.sidebar.info("Scenario mode. Run fetch_rainfall.py once (needs internet) to unlock real rainfall and the live forecast.")
if source.startswith("Live"):
    live_df, live_status = live_rain()
    if live_df is None or "anomaly_pct" not in live_df:
        st.sidebar.error(live_status["message"] + ". Showing the scenario instead.")
        source = "Scenario"

if source == "Scenario":
    severity = st.sidebar.slider(T("Scenario: rainfall change vs normal (%)"), 0, 60, 30, key="scen_sev")
    affected = st.sidebar.multiselect(T("Affected districts (empty = all)"), districts, key="scen_aff")
    sign = -1 if hazard_type == "Drought" else 1
    df["rain_change_pct"] = np.where(df["district"].isin(affected) | (len(affected) == 0), sign * severity, 0)
    st.sidebar.warning(T("SCENARIO: a simulated input, not a forecast."))
elif source.startswith("Live"):
    df = df.merge(live_df[["district", "anomaly_pct"]], on="district", how="left")
    df["rain_change_pct"] = df["anomaly_pct"].fillna(0)
    st.sidebar.success(f"LIVE rainfall from Open-Meteo, updated {live_status['fetched_at']}: {live_status['window']} vs the 1991-2020 normal.")
    if int(live_df["anomaly_pct"].isna().sum()):
        st.sidebar.caption(f"{int(live_df['anomaly_pct'].isna().sum())} districts had too much missing data and are treated as normal.")
else:
    rain = pd.read_csv(RAIN_FILE)
    df = df.merge(rain[["district", "rain_anom_ahsyear_pct"]].rename(columns={"rain_anom_ahsyear_pct": "anomaly_pct"}), on="district", how="left")
    df["rain_change_pct"] = df["anomaly_pct"].fillna(0)

st.sidebar.markdown("---")
st.sidebar.markdown(f"**{T('Livestock disease control')}**")
RVF6 = ["Rulindo", "Burera", "Gicumbi", "Kirehe", "Kayonza", "Rwamagana"]
EAST = df.loc[df["province"] == "East", "district"].tolist()
preset = st.sidebar.selectbox(T("Rift Valley fever notice"), ["None", "26 June 2026 notice (6 districts)", "Later: whole Eastern Province + the 6"], format_func=T, key="rvf_preset")
default_r = [] if preset.startswith("None") else (RVF6 if "(6 districts)" in preset else sorted(set(RVF6) | set(EAST)))
default_r = [d for d in default_r if d in districts]
restricted = st.sidebar.multiselect(T("Districts under animal-movement restriction"), districts, default=default_r,
                                    key=f"restr_{preset}")
st.sidebar.caption("The preset follows the project brief (RAB notices, June 2026). Intumwa does not know current restrictions: "
                   "check the latest RAB notice before relying on this.")

# ---------- risk score ----------
# hazard: 0 at normal rainfall, 100 at a 50% deficit (drought) or 50% excess (heavy rain)
change = -df["rain_change_pct"] if hazard_type == "Drought" else df["rain_change_pct"]
df["hazard"] = (change / 50).clip(0, 1) * 100
df["risk"] = (df["hazard"] / 100 * df["vulnerability_index"]).round(1)
def tier_of(risk):
    """Low < 15, Elevated 15-29.9, High >= 30 (matches README)."""
    return pd.cut(risk, [-1, 15, 30, 1000], labels=["Low", "Elevated", "High"], right=False).astype(str)

df["tier"] = tier_of(df["risk"])
# fewer than 30 survey households: the index is too noisy to assign a tier
df.loc[df["n_households"] < 30, "tier"] = "Insufficient data"

# livestock risk: hazard x average of vulnerability and cattle exposure (share of households keeping cattle,
# rescaled 0-100 across districts). A transparent heuristic: no disease or herd-size data is used.
ce = df["keeps_cattle"]
df["cattle_exposure"] = ((ce - ce.min()) / (ce.max() - ce.min()) * 100).round(1)
df["livestock_risk"] = (df["hazard"] / 100 * (df["vulnerability_index"] + df["cattle_exposure"]) / 2).round(1)
df["livestock_tier"] = tier_of(df["livestock_risk"])
df.loc[df["n_households"] < 30, "livestock_tier"] = "Insufficient data"
df["animal_restriction"] = df["district"].isin(restricted)

# top two reasons per district: the indicators where the district is worst relative to the others
cols = list(DRIVERS)
scaled = (df[cols] - df[cols].min()) / (df[cols].max() - df[cols].min())
reason_cols = [c for c in cols if c != "extreme_poverty_rate"]   # it repeats poverty_rate
df["top_drivers"] = scaled[reason_cols].apply(lambda r: list(r.sort_values(ascending=False).index[:2]), axis=1)

# ---------- messages ----------
def sms(row, lang):
    """Build the alert text for one district row. Kinyarwanda texts need review by a native speaker."""
    d, tier = row["district"], row["tier"]
    why_en = DRIVERS[row["top_drivers"][0]][0]      # SMS carries the single biggest reason; the dashboard shows two
    why_rw = DRIVERS[row["top_drivers"][0]][1]
    parts = []
    if tier == "Insufficient data":
        rw = f"Intumwa ({d}): Amakuru y'ubushakashatsi kuri aka karere ni make, nta cyiciro cy'ibyago gitangwa."
        en = f"Intumwa ({d}): Too few survey households here to assign a risk tier."
    elif tier == "Low":
        rw = f"Intumwa ({d}): Nta byago bikomeye ubu. Komeza ukurikirane."
        en = f"Intumwa ({d}): No major risk now. Keep monitoring."
    elif hazard_type == "Drought":
        rw = f"Intumwa ({d}): {TIER_RW[tier]}. Ibimenyetso by'izuba ryinshi. Bika amazi n'ubwatsi."
        en = f"Intumwa ({d}): {tier} risk. Signs of a dry spell. Store water and fodder."
    else:
        rw = f"Intumwa ({d}): {TIER_RW[tier]}. Ibimenyetso by'imvura nyinshi. Sarura vuba, wumishe ibigori, ucukure inzira z'amazi."
        en = f"Intumwa ({d}): {tier} risk. Signs of heavy rain. Harvest early, dry maize, dig drainage."
    parts.append(rw if lang == "Kinyarwanda" else en)
    if row["animal_restriction"]:
        parts.append("Hari akato k'amatungo: ntugurishe cyangwa ngo wimure inka, ukingize, umenyeshe veterineri."
                     if lang == "Kinyarwanda" else
                     "Animal movement restriction: do not sell or move cattle, vaccinate, tell your vet.")
    if tier in ("Elevated", "High"):
        parts.append(f"Impamvu: {why_rw}." if lang == "Kinyarwanda" else f"Why: {why_en}.")
    return " ".join(parts)

def sms_livestock(row, lang):
    """Alert text for livestock keepers. Kinyarwanda texts need review by a native speaker."""
    d, tier = row["district"], row["livestock_tier"]
    if tier == "Insufficient data":
        rw = f"Intumwa ({d}): Amakuru y'ubushakashatsi ni make, nta cyiciro cy'ibyago by'amatungo gitangwa."
        en = f"Intumwa ({d}): Too few survey households to assign a livestock risk tier."
    elif tier == "Low":
        rw = f"Intumwa ({d}): Nta byago bikomeye ku matungo ubu. Komeza ukurikirane."
        en = f"Intumwa ({d}): No major livestock risk now. Keep monitoring."
    elif hazard_type == "Drought":
        rw = f"Intumwa ({d}): {TIER_RW[tier]} ku matungo. Izuba ryinshi rishobora kugabanya ubwatsi n'amazi. Bika ubwatsi, ushake amazi. Amata ashobora kugabanuka."
        en = f"Intumwa ({d}): {tier} livestock risk. A dry spell can cut pasture and water. Store fodder, secure water; expect lower milk."
    else:
        rw = f"Intumwa ({d}): {TIER_RW[tier]} ku matungo. Imvura nyinshi ishobora kongera indwara zituruka ku mibu. Wirinde imibu, umenyeshe veterineri inka zirwaye."
        en = f"Intumwa ({d}): {tier} livestock risk. Heavy rain can raise mosquito-borne disease (e.g. RVF). Control mosquitoes, report sick animals to your vet."
    out = [rw if lang == "Kinyarwanda" else en]
    if row["animal_restriction"]:
        out.append("Hari akato k'amatungo: ntugurishe cyangwa ngo wimure inka, ukingize, umenyeshe veterineri."
                   if lang == "Kinyarwanda" else
                   "Animal movement restriction: do not sell or move cattle, vaccinate, tell your vet.")
    return " ".join(out)

USSD = {
    "Kinyarwanda": {
        "menu": "Intumwa\n1 Ibyago mu karere\n2 Iburira ry'ibihingwa\n3 Iburira ry'amatungo\n0 Sohoka",
        "risk": "Akarere: {d}\nIbihingwa: {t}\nAmatungo: {lt}\n(Ibyago {r} / {lr})\n* Subira inyuma",
        "bye": "Murakoze. Intumwa.", "bad": "Itegeko ritazwi.\n* Subira inyuma",
    },
    "English": {
        "menu": "Intumwa\n1 Risk in my district\n2 Crop alert\n3 Livestock alert\n0 Exit",
        "risk": "District: {d}\nCrops: {t}\nLivestock: {lt}\n(Risk {r} / {lr})\n* Back",
        "bye": "Thank you. Intumwa.", "bad": "Unknown option.\n* Back",
    },
}

def ussd_screen(row, lang, screen):
    """Return the text of one USSD screen. screen is 'menu', '1', '2', '3' or '0'."""
    u = USSD[lang]
    if screen == "menu":
        return u["menu"]
    if screen == "1":
        return u["risk"].format(d=row["district"], t=row["tier"], lt=row["livestock_tier"],
                                r=row["risk"], lr=row["livestock_risk"])
    if screen == "2":
        return sms(row, lang) + "\n* " + ("Subira inyuma" if lang == "Kinyarwanda" else "Back")
    if screen == "3":
        return sms_livestock(row, lang) + "\n* " + ("Subira inyuma" if lang == "Kinyarwanda" else "Back")
    if screen == "0":
        return u["bye"]
    return u["bad"]

# ---------- layout ----------
def kpi(label, value, sub="", tone="neutral"):
    return (f'<div class="kpi kpi-{tone}"><div class="kpi-l">{label}</div><div class="kpi-v">{value}</div>'
            f'<div class="kpi-s">{sub}</div></div>')

n_high = int((df["tier"] == "High").sum())
n_elev = int((df["tier"] == "Elevated").sum())
hh_exposed = int(df.loc[df["tier"].isin(["High", "Elevated"]), "est_households"].sum())
hh_all = int(df["est_households"].sum())
l_high = int((df["livestock_tier"] == "High").sum())
if source == "Scenario":
    src_chip = f"{T('Simulated scenario')}: {T('dry spell') if hazard_type == 'Drought' else T('heavy rain')}, {severity}% {T('change')}"
elif source.startswith("Live"):
    src_chip = f"LIVE rainfall, Open-Meteo: last 30 days + 14-day forecast (updated {live_status['fetched_at']})"
else:
    src_chip = T("Hazard: NASA POWER rainfall, survey year Sept 2023 to Aug 2024")

_hero_sub = T("District early warning for Rwanda's crop farmers and livestock keepers")
_chip1, _chip2, _chip3 = T("NISR Agriculture Household Survey 2024"), T("30 districts"), T("Kinyarwanda SMS and USSD")
st.markdown(
    '<div class="hero"><div><div class="brand">Intumwa</div>'
    '<div class="tag">Sisitemu yo kuburira hakiri kare ku buhinzi n\'ubworozi</div>'
    f'<div class="sub">{_hero_sub}</div></div>'
    f'<div class="hero-r"><span class="chip chip-w">{_chip1}</span>'
    f'<span class="chip chip-w">{_chip2}</span><span class="chip chip-w">{_chip3}</span>'
    f'<span class="chip chip-a">{html.escape(src_chip)}</span></div></div>', unsafe_allow_html=True)

kc = st.columns(4)
kc[0].markdown(kpi(T("High-risk districts"), n_high, T("risk score of 30 or more"), "high"), unsafe_allow_html=True)
kc[1].markdown(kpi(T("Elevated districts"), n_elev, T("risk score of 15 to 30"), "elev"), unsafe_allow_html=True)
kc[2].markdown(kpi(T("Farming households exposed"), f"{hh_exposed / 1e6:.2f} M",
                   f"{T('in High or Elevated districts, of')} {hh_all / 1e6:.2f} M"), unsafe_allow_html=True)
kc[3].markdown(kpi(T("Livestock High-risk"), l_high,
                   f"{int(df['animal_restriction'].sum())} {T('under movement restriction')}"), unsafe_allow_html=True)
st.write("")

t_map, t_alerts, t_crop, t_live, t_inst, t_ana, t_field, t_method = st.tabs(
    [T(x) for x in ["Risk map", "Alerts (SMS)", "Crop context", "Livestock", "Institutions", "Analytics & forecast",
                    "USSD and field reports", "Method & validation"]])
t_ussd = t_report = t_field

# --- 1. risk map ---
with t_map:
    left, right = st.columns([2.2, 1], gap="large")
    with left:
        st.markdown(f'<div class="h2">{T("Where is the risk highest?")}</div><div class="muted">'
                    f'{T("Risk = weather hazard x how vulnerable the farmers are. Bubble size shows vulnerability; colour shows the risk tier.")}</div>', unsafe_allow_html=True)
        style = st.radio("Basemap", ["Street map", "Plain (works offline)"], horizontal=True, label_visibility="collapsed",
                         format_func=T, key="basemap")
        top = df[df["tier"] != "Insufficient data"].sort_values("risk", ascending=False).head(10)
        label = df["district"].where(df["district"].isin(top["district"].head(8)) | (style != "Street map"), "")
        fig = px.scatter_map(df.assign(label=label), lat="lat", lon="lon", color="tier", size="vulnerability_index",
                             size_max=26, zoom=7.2, center={"lat": -1.95, "lon": 29.9}, height=560, text="label",
                             color_discrete_map=TIER_COLOR,
                             category_orders={"tier": ["High", "Elevated", "Low", "Insufficient data"]},
                             hover_name="district",
                             hover_data={"risk": True, "hazard": ":.0f", "vulnerability_index": True,
                                         "lat": False, "lon": False, "tier": False, "label": False})
        fig.update_traces(textposition="top center")
        fig.update_layout(map_style="open-street-map" if style == "Street map" else "white-bg",
                          margin=dict(l=0, r=0, t=0, b=0), legend=dict(title="", orientation="h", y=1.04, x=0))
        show_chart(st, fig, width="stretch")
        st.caption("Circle positions are approximate district centres. Grey = too few survey households to score (these districts are left out of the top 10). "
                   "Vulnerability is estimated from AHS 2024 household data.")
    with right:
        rows = ""
        for i, r in enumerate(top.itertuples(), 1):
            col = TIER_COLOR[r.tier]
            rows += (f'<div class="rank"><div class="rank-n">{i}</div><div class="rank-b"><div class="rank-t"><b>{r.district}</b>'
                     f'<span class="pill" style="background:{col}">{T(r.tier)}</span></div>'
                     f'<div class="bar"><div style="width:{min(r.risk / 70 * 100, 100):.0f}%;background:{col}"></div></div>'
                     f'<div class="rank-s">{T("risk")} {r.risk:.1f} &middot; {T("hazard")} {r.hazard:.0f} &middot; {T("vulnerability")} {r.vulnerability_index:.0f}</div>'
                     '</div></div>')
        st.markdown(f'<div class="h3">{T("Top 10 districts right now")}</div>{rows}', unsafe_allow_html=True)
    with st.expander(T("Full table (all 30 districts)")):
        st.dataframe(df.sort_values("risk", ascending=False)[["district", "province", "tier", "risk", "hazard",
                                                              "vulnerability_index", "n_households"]],
                     hide_index=True, width="stretch",
                     column_config={"risk": st.column_config.ProgressColumn("Risk", min_value=0, max_value=70, format="%.1f"),
                                    "hazard": st.column_config.NumberColumn("Hazard", format="%.0f"),
                                    "vulnerability_index": st.column_config.NumberColumn("Vulnerability", format="%.1f"),
                                    "n_households": st.column_config.NumberColumn("Survey households")})

    if live_df is not None and source.startswith("Live"):
        with st.expander("Live rainfall behind these scores (Open-Meteo)", expanded=False):
            lt = live_df.merge(df[["district", "tier"]], on="district").sort_values("anomaly_pct")
            st.dataframe(lt[["district", "tier", "rain_past_mm", "rain_ahead_mm", "expected_mm", "anomaly_pct", "wettest_day_ahead_mm", "dry_run_ahead_days"]],
                         hide_index=True, width="stretch",
                         column_config={"rain_past_mm": "Last 30 days (mm)", "rain_ahead_mm": "Next 14 days forecast (mm)", "expected_mm": "Normal for the 44 days (mm)",
                                        "anomaly_pct": st.column_config.NumberColumn("Change vs normal (%)", format="%+.0f"),
                                        "wettest_day_ahead_mm": "Wettest forecast day (mm)", "dry_run_ahead_days": "Longest dry run ahead (days)"})
            st.caption("Rainfall beyond about 7 days ahead is uncertain: treat the forecast part as an outlook, not a promise.")

# --- 2. alerts ---
with t_alerts:
    st.markdown(f'<div class="h2">{T("Alert preview")}</div><div class="muted">'
                f'{T("What a farmer would receive on a basic phone. Sending is simulated.")}</div>', unsafe_allow_html=True)
    order = df.assign(thin=df["tier"] == "Insufficient data").sort_values(["thin", "risk"], ascending=[True, False])["district"].tolist()
    pick = st.selectbox(T("District"), order, key="alert_pick")
    row = df[df["district"] == pick].iloc[0]
    tcol = TIER_COLOR[row["tier"]]
    left, right = st.columns([1.5, 1], gap="large")
    with left:
        c1, c2 = st.columns(2)
        for col, lang in ((c1, "Kinyarwanda"), (c2, "English")):
            text = sms(row, lang)
            n = len(text)
            extra = " &middot; over 160: would split into 2 SMS" if n > 160 else ""
            col.markdown(f'<div class="phone"><div class="phone-h">{lang}</div><div class="bubble">{html.escape(text)}</div>'
                         f'<div class="phone-m">{n} {T("characters")}{extra}</div></div>', unsafe_allow_html=True)
    with right:
        st.markdown(f'<div class="eq"><div><span>{T("Hazard")}</span><b>{row["hazard"]:.0f}%</b></div><i>&times;</i>'
                    f'<div><span>{T("Vulnerability")}</span><b>{row["vulnerability_index"]:.0f}</b></div><i>=</i>'
                    f'<div style="border:2px solid {tcol}"><span>{T("Risk")}</span><b>{row["risk"]:.1f}</b>'
                    f'<em style="background:{tcol}">{T(row["tier"])}</em></div></div>', unsafe_allow_html=True)
        chips = "".join(f'<span class="driver">{html.escape(DRIVERS[c][0])}</span>' for c in row["top_drivers"])
        st.markdown(f'<div class="h3">{T("Why this district")}</div><div class="muted">'
                    f'{T("The two weaknesses where it is worst compared with other districts:")}</div>{chips}', unsafe_allow_html=True)
    if row["n_households"] < 30:
        st.warning(f"Only {row['n_households']} survey households in this district, so no risk tier is assigned.")
    if "sent" not in st.session_state:
        st.session_state["sent"] = []
    b1, b2 = st.columns([1, 1])
    if b1.button(T("Send (simulated)"), type="primary"):
        st.session_state["sent"].append({"district": pick, "tier": row["tier"], "message": sms(row, "Kinyarwanda")})
    batch = df[df["tier"] == "High"].copy()
    if len(batch):
        batch["message_rw"] = batch.apply(lambda r: sms(r, "Kinyarwanda"), axis=1)
        b2.download_button(T("Download all High-tier alerts (CSV)"),
                           batch[["district", "tier", "risk", "message_rw"]].to_csv(index=False),
                           file_name="intumwa_alerts.csv")
    if st.session_state["sent"]:
        st.markdown(f"**{T('Simulated outbox')}**")
        st.dataframe(pd.DataFrame(st.session_state["sent"]), hide_index=True, width="stretch")

# --- 3. crop context ---
with t_crop:
    st.subheader(T("Crop yields in the AHS 2024 (context for crop risk)"))
    crop = st.selectbox(T("Crop"), sorted(yields["crop"].unique()), key="crop_ctx")
    cy = yields[yields["crop"] == crop].merge(df[["district", "tier"]], on="district")
    nat = cy["median_yield_kg_ha"].median()
    fig2 = px.bar(cy.sort_values("median_yield_kg_ha"), x="median_yield_kg_ha", y="district", orientation="h",
                  color="tier", color_discrete_map=TIER_COLOR, height=620,
                  labels={"median_yield_kg_ha": "Median yield (kg/ha)"})
    fig2.add_vline(x=nat, line_dash="dash", annotation_text="median of districts")
    show_chart(st, fig2, width="stretch")
    st.caption("Median of plot-level yields (extreme 2% trimmed). Bars are coloured by current risk tier. "
               "Districts with few plots are less reliable.")
    rain_cols = pd.read_csv(RAIN_FILE).columns if has_rain else []
    rcol = next((c for c in ("rain_anom_ahsyear_pct", "rain_anom_2024_pct") if c in rain_cols), None)
    if rcol:
        from scipy.stats import spearmanr
        t = cy.merge(pd.read_csv(RAIN_FILE)[["district", rcol]], on="district").dropna()
        r, p = spearmanr(t[rcol], t["median_yield_kg_ha"])
        window = "Sept 2023 to Aug 2024, the survey year" if rcol == "rain_anom_ahsyear_pct" else "calendar 2024"
        st.markdown(f"**Do wetter-than-normal districts yield more? (rainfall change, {window}, vs yield, {crop})**")
        st.write(f"Spearman rank correlation r = {r:.2f}, p = {p:.2f}, n = {len(t)} districts. "
                 "A weak or non-significant result means rainfall alone does not explain district yields here.")
    else:
        st.info("Run fetch_rainfall.py to add data/rainfall_anomaly.csv and test rainfall against these yields.")

# --- livestock ---
with t_live:
    st.subheader(T("Livestock risk (dry spell or heavy rain)"))
    lc = df["livestock_tier"].value_counts()
    a1, a2, a3 = st.columns(3)
    a1.metric(T("High livestock-risk districts"), int(lc.get("High", 0)))
    a2.metric(T("Elevated"), int(lc.get("Elevated", 0)))
    a3.metric(T("Districts with movement restriction"), int(df["animal_restriction"].sum()))
    figl = px.scatter_map(df, lat="lat", lon="lon", color="livestock_tier", size="cattle_exposure",
                          size_max=28, zoom=7, center={"lat": -1.95, "lon": 29.9}, height=480,
                          color_discrete_map=TIER_COLOR, hover_name="district",
                          hover_data={"livestock_risk": True, "keeps_cattle": ":.2f", "cattle_exposure": True,
                                      "lat": False, "lon": False, "livestock_tier": False})
    figl.update_layout(map_style="open-street-map", margin=dict(l=0, r=0, t=0, b=0), legend=dict(title="", orientation="h", y=1.04, x=0))
    show_chart(st, figl, width="stretch")
    st.caption("Livestock risk = hazard x average of (vulnerability index, cattle exposure). Bubble size = cattle exposure, "
               "the share of AHS 2024 households keeping cattle, rescaled 0-100. This is a simple heuristic: "
               "no disease data is used and the milk series below is shown for context, not scored. "
               "Movement restrictions come from the sidebar.")
    pl = st.selectbox(T("District (livestock alert)"), sorted(districts), key="live_pick")
    lrow = df[df["district"] == pl].iloc[0]
    l1, l2 = st.columns(2)
    for col, lang in ((l1, "Kinyarwanda"), (l2, "English")):
        col.markdown(f"**{lang}**")
        col.code(sms_livestock(lrow, lang), language=None)
    st.dataframe(df.sort_values("livestock_risk", ascending=False)[
        ["district", "livestock_tier", "livestock_risk", "hazard", "cattle_exposure", "vulnerability_index", "animal_restriction"]
    ].head(10), hide_index=True, width="stretch")

# --- USSD demo ---
with t_ussd:
    st.subheader(T("USSD demo (simulated phone menu)"))
    st.caption(T("Works on any basic phone. Nothing is sent: this shows what a farmer would see after dialling the code."))
    u1, u2 = st.columns(2)
    ulang = u1.radio(T("Language"), ["Kinyarwanda", "English"], index=0 if UI_LANG == "Kinyarwanda" else 1, horizontal=True, key="ussd_lang")
    udist = u2.selectbox(T("Phone registered in district"), sorted(districts), key="ussd_dist")
    urow = df[df["district"] == udist].iloc[0]
    if st.session_state.get("ussd_key") != (ulang, udist):
        st.session_state["ussd_key"] = (ulang, udist)
        st.session_state["ussd_screen"] = "menu"
    screen = st.session_state["ussd_screen"]
    st.markdown(f'<div class="ussd">{html.escape(ussd_screen(urow, ulang, screen))}</div>', unsafe_allow_html=True)
    if screen in ("menu", "1", "2", "3"):
        with st.form("ussd_form", clear_on_submit=True):
            entry = st.text_input(T("Reply"), max_chars=1, help="Menu: 1, 2, 3 or 0. On any other screen: * to go back.")
            if st.form_submit_button(T("Send")):
                if screen == "menu":
                    st.session_state["ussd_screen"] = entry if entry in ("0", "1", "2", "3") else "bad"
                else:
                    st.session_state["ussd_screen"] = "menu" if entry == "*" else screen
                st.rerun()
    else:
        if st.button(T("Dial again")):
            st.session_state["ussd_screen"] = "menu"
            st.rerun()

with t_live:
    st.markdown("---")
    st.subheader(T("Milk through the year (NISR AHS 2024, Sept 2023 to Aug 2024)"))
    mp = st.selectbox(T("Province"), ["Rwanda", "Kigali", "South", "West", "North", "East"], key="milk_prov")
    mm = milk[milk["province"] == mp]
    m1, m2, m3 = st.columns(3)
    for col, field, label, ttl in ((m1, "litres_per_cow_day", "Litres per cow per day", "Yield per cow"),
                                   (m2, "lactating_cows", "Lactating cows", "Lactating cows"),
                                   (m3, "farmgate_price_rwf_l", "Rwf per litre", "Farm-gate price")):
        figm = px.line(mm, x="month", y=field, markers=True, height=260, labels={"month": "", field: label})
        figm.update_layout(title=ttl, margin=dict(l=0, r=0, t=40, b=0))
        show_chart(col, figm, width="stretch")
    nat = milk[milk["province"] == "Rwanda"].set_index("month")
    st.write(f"Nationally, milk per cow fell from {nat.loc['2024-04', 'litres_per_cow_day']} litres a day in April 2024 to "
             f"{nat.loc['2024-08', 'litres_per_cow_day']} in August, lactating cows fell from {nat.loc['2024-02', 'lactating_cows']:,} "
             f"(February) to {nat.loc['2024-08', 'lactating_cows']:,}, and the farm-gate price rose from {nat.loc['2024-04', 'farmgate_price_rwf_l']} to "
             f"{nat.loc['2024-08', 'farmgate_price_rwf_l']} Rwf per litre. This is a seasonal pattern the survey recorded; it does not by itself prove the cause.")
    st.caption("Source: NISR, Agricultural Household Survey 2024 report, Tables 50, 51 and 53 (transcribed by hand; provincial cow counts "
               "add up to the published national totals). The report's South price for November 2023 (494 Rwf) looks unusually high "
               "and lifts the national figure for that month.")

# --- 4. institutions ---
with t_inst:
    st.subheader(T("Institutions dashboard"))
    counts = df["tier"].value_counts()
    k1, k2, k3, k4 = st.columns(4)
    k1.metric(T("High-risk districts"), int(counts.get("High", 0)))
    k2.metric(T("Elevated"), int(counts.get("Elevated", 0)))
    k3.metric(T("Farming households in High districts"), f"{int(df.loc[df.tier == 'High', 'est_households'].sum()):,}")
    k4.metric(T("Districts with movement restriction"), int(df["animal_restriction"].sum()))
    prov = st.multiselect(T("Province"), sorted(df["province"].unique()), default=sorted(df["province"].unique()), key="inst_prov")
    show = df[df["province"].isin(prov)].sort_values("risk", ascending=False)
    st.dataframe(show[["district", "province", "tier", "risk", "hazard", "vulnerability_index", "poverty_rate",
                       "no_extension", "no_account", "keeps_cattle", "crop_insurance", "est_households", "n_households"]],
                 hide_index=True, width="stretch")
    st.caption("Shares are survey-weighted AHS 2024 estimates. crop_insurance is the share of farming households "
               "with crop insurance (very low everywhere). keeps_cattle is the share keeping cattle.")

with t_inst:
    st.markdown("---")
    st.subheader(T("The information gap Intumwa targets"))
    cl = climate.set_index("province")
    g1, g2, g3 = st.columns(3)
    g1.metric("Households that received weather and climate information", f"{cl.loc['Rwanda', 'weather_climate_info_hh_pct']}%")
    g2.metric("...in Kigali / West", f"{cl.loc['Kigali', 'weather_climate_info_hh_pct']}% / {cl.loc['West', 'weather_climate_info_hh_pct']}%")
    g3.metric("Plots not irrigated because no water is available", f"{cl.loc['Rwanda', 'no_water_for_irrigation_pct_of_plots']}%")
    figc = px.bar(climate[climate["province"] != "Rwanda"], x="province",
                  y=["weather_climate_info_hh_pct", "veterinary_services_hh_pct", "animal_health_feeding_hh_pct"],
                  barmode="group", height=320, labels={"value": "% of agricultural households", "variable": "", "province": ""})
    show_chart(st, figc, width="stretch")
    st.caption("Source: NISR AHS 2024 report, Table 27 (extension services received) and Table 26 (shares of all plots; its rows add up to 100 only with the irrigated share included). Of households that received weather "
               "and climate information, 52.4% got it from media and 0.9% by telephone message (Table 29): "
               "a direct SMS/USSD channel is almost unused.")


# --- analytics & forecast ---
def ridge_fit(X, t, lam):
    mu, sd = X.mean(0), X.std(0) + 1e-9
    Xs = (X - mu) / sd
    tm = t.mean()
    b = np.linalg.solve(Xs.T @ Xs + lam * np.eye(X.shape[1]), Xs.T @ (t - tm))
    return mu, sd, b, tm

def ridge_loo(X, t, lam):
    """Leave-one-out predictions: each district is predicted by a model that never saw it."""
    out = np.zeros(len(t))
    for i in range(len(t)):
        keep = np.arange(len(t)) != i
        mu, sd, b, tm = ridge_fit(X[keep], t[keep], lam)
        out[i] = ((X[i] - mu) / sd) @ b + tm
    return out

def season_matrix(tidx, K=2):
    cols = [np.ones(len(tidx)), tidx.astype(float)]
    for k in range(1, K + 1):
        cols += [np.sin(2 * np.pi * k * tidx / 12), np.cos(2 * np.pi * k * tidx / 12)]
    return np.column_stack(cols)

def demo_milk_series(name):
    """SYNTHETIC monthly milk per cow (litres/day), Sept 2021 to Aug 2026. Seeded by district name. Not NISR data."""
    rng = np.random.default_rng(zlib.crc32(name.encode()))
    dates = pd.date_range("2021-09-01", periods=60, freq="MS")
    base = rng.uniform(3.0, 4.2)
    v = base + 0.5 * np.cos(2 * np.pi * (np.asarray(dates.month) - 2) / 12) + rng.normal(0, 0.18, 60)
    v[np.asarray((dates >= "2023-06-01") & (dates <= "2023-09-01"))] -= 0.6      # an invented dry spell
    return pd.DataFrame({"date": dates, "value": v.round(2)})

with t_ana:
    st.subheader(T("Statistical charts"))
    st.caption("Charts use real NISR data (survey district tables and the AHS 2024 report). The first two follow the current sidebar scenario.")
    prov_list = ["Rwanda", "Kigali", "South", "West", "North", "East"]
    CH = ["Districts by risk tier (pie)", "Farming households by risk tier (donut)", "How milk is used (pie, NISR Table 52)",
          "Why plots are not irrigated (pie, NISR Table 26)", "Where farmers got weather information (pie, NISR Table 29)",
          "The seven weaknesses, national share (bar)", "How the weaknesses relate (correlation heatmap)",
          "Vulnerability vs crop yield (scatter + fitted line)", "Spread of district risk (histogram)"]
    ch = st.selectbox(T("Chart"), CH, key="chart_pick")
    if ch.startswith("Districts by risk tier"):
        cnt = df["tier"].value_counts().rename_axis("tier").reset_index(name="districts")
        show_chart(st, px.pie(cnt, names="tier", values="districts", color="tier", color_discrete_map=TIER_COLOR, height=420), width="stretch")
    elif ch.startswith("Farming households"):
        hh_t = df.groupby("tier")["est_households"].sum().reset_index()
        show_chart(st, px.pie(hh_t, names="tier", values="est_households", hole=0.5, color="tier", color_discrete_map=TIER_COLOR, height=420), width="stretch")
    elif ch.startswith(("How milk", "Why plots")):
        topic = "milk_use" if ch.startswith("How milk") else "irrigation"
        pv = st.selectbox("Province", prov_list, key="pie_prov")
        sub = shares[(shares.topic == topic) & (shares.province == pv)]
        show_chart(st, px.pie(sub, names="category", values="pct", height=420), width="stretch")
        if topic == "irrigation":
            st.caption("Shares of all plots (the four slices add up to 100). Source: NISR AHS 2024 report, Table 26.")
        else:
            st.caption("Source: NISR AHS 2024 report, Table 52.")
    elif ch.startswith("Where farmers"):
        sub = shares[shares.topic == "weather_source"]
        show_chart(st, px.pie(sub, names="category", values="pct", height=460), width="stretch")
        st.caption("Households that received weather and climate information, by source (national). Media dominates; telephone messages are 0.9%. NISR AHS 2024, Table 29.")
    elif ch.startswith("The seven"):
        wn = {DRIVERS[c][0]: (df[c] * df["est_households"]).sum() / df["est_households"].sum() * 100 for c in DRIVERS}
        bd = pd.DataFrame({"weakness": list(wn), "share_pct": list(wn.values())}).sort_values("share_pct")
        show_chart(st, px.bar(bd, x="share_pct", y="weakness", orientation="h", height=380, labels={"share_pct": "% of farming households", "weakness": ""}), width="stretch")
        st.caption("Weighted national shares computed from the survey (poverty here is 22.6% vs 25.9% in the NISR report: see README).")
    elif ch.startswith("How the weaknesses"):
        cm = df[list(DRIVERS)].rename(columns={c: DRIVERS[c][0] for c in DRIVERS}).corr()
        show_chart(st, px.imshow(cm, text_auto=".2f", zmin=-1, zmax=1, color_continuous_scale="RdBu_r", height=520), width="stretch")
        st.caption("Correlation across the 30 districts. A high value means the two weaknesses tend to occur in the same districts.")
    elif ch.startswith("Vulnerability vs"):
        cr = st.selectbox("Crop", sorted(yields["crop"].unique()), key="sc_crop")
        sc = yields[yields["crop"] == cr].merge(df[["district", "vulnerability_index", "n_households"]], on="district")
        sc = sc[(sc.n_households >= 30) & (sc.n_records >= 20)]
        from scipy.stats import spearmanr
        rr, pp = spearmanr(sc["vulnerability_index"], sc["median_yield_kg_ha"])
        fsc = px.scatter(sc, x="vulnerability_index", y="median_yield_kg_ha", hover_name="district", height=440,
                         labels={"vulnerability_index": "Vulnerability index (0-100)", "median_yield_kg_ha": "Median yield (kg/ha)"})
        sl, ic = np.polyfit(sc["vulnerability_index"], sc["median_yield_kg_ha"], 1)
        xs = np.array([sc["vulnerability_index"].min(), sc["vulnerability_index"].max()])
        fsc.add_trace(go.Scatter(x=xs, y=sl * xs + ic, mode="lines", name="fitted line"))
        show_chart(st, fsc, width="stretch")
        st.write(f"Spearman r = {rr:.2f}, p = {pp:.2f}, n = {len(sc)} districts. An association across districts in one survey year, not proof of cause.")
    else:
        show_chart(st, px.histogram(df, x="risk", nbins=15, height=380, labels={"risk": "District risk (current scenario)"}), width="stretch")

    st.markdown("---")
    st.subheader("Prediction 1: can survey indicators predict district yields? (real data)")
    cp = st.selectbox("Crop", sorted(yields["crop"].unique()), key="pred_crop")
    XC = ["poverty_rate", "no_extension", "no_account", "no_improved_seed", "small_farm_lt_half_ha", "no_cooperative", "keeps_cattle"]
    pd_ = yields[yields["crop"] == cp].merge(df[["district", "n_households"] + XC], on="district")
    pd_ = pd_[(pd_.n_households >= 30) & (pd_.n_records >= 20)].reset_index(drop=True)
    if len(pd_) >= 12:
        Xm, tm_ = pd_[XC].values.astype(float), pd_["median_yield_kg_ha"].values.astype(float)
        LAM = 20.0
        pr = ridge_loo(Xm, tm_, LAM)
        r2 = 1 - ((tm_ - pr) ** 2).sum() / ((tm_ - tm_.mean()) ** 2).sum()
        mae_m, mae_b = np.abs(tm_ - pr).mean(), np.abs(tm_ - tm_.mean()).mean()
        q1, q2, q3 = st.columns(3)
        q1.metric("Districts used", len(pd_))
        q2.metric("Cross-validated R²", f"{r2:.2f}")
        q3.metric("Error vs guessing the average", f"{mae_m:,.0f} vs {mae_b:,.0f} kg/ha")
        verdict = "essentially no predictive power" if r2 < 0.1 else ("weak predictive power" if r2 < 0.4 else "moderate predictive power")
        st.write(f"**Reading:** ridge regression on seven survey indicators, tested by leave-one-district-out validation, shows **{verdict}** for {cp}. "
                 "With about 25 districts and one survey year, this is what honest validation looks like; it should not be used to forecast yields.")
        mu_, sd_, b_, _ = ridge_fit(Xm, tm_, LAM)
        cf = pd.DataFrame({"indicator": [DRIVERS.get(c, ("cattle ownership",))[0] for c in XC], "effect": b_}).sort_values("effect")
        c1, c2 = st.columns(2)
        show_chart(c1, px.bar(cf, x="effect", y="indicator", orientation="h", height=330, title="Direction of association (standardised)"), width="stretch")
        ap = pd.DataFrame({"district": pd_["district"], "actual": tm_, "predicted (held out)": pr})
        fap = px.scatter(ap, x="actual", y="predicted (held out)", hover_name="district", height=330, title="Actual vs predicted")
        lo_, hi_ = float(min(tm_.min(), pr.min())), float(max(tm_.max(), pr.max()))
        fap.add_trace(go.Scatter(x=[lo_, hi_], y=[lo_, hi_], mode="lines", name="perfect"))
        show_chart(c2, fap, width="stretch")
    else:
        st.info("Too few districts with enough records for this crop.")

    st.markdown("---")
    st.subheader("Prediction 2: seasonal forecast (DEMO data or your own file)")
    st.warning("DEMO: the default series below is SYNTHETIC (invented, seeded by the district name). It shows how the forecasting "
               "module will work once multi-year data is available; it is not NISR data and the numbers mean nothing. "
               "Real multi-year milk or yield series would come from the Seasonal Agriculture Survey, RAB or dairy plants.")
    up = st.file_uploader("Optional: upload your own monthly series (CSV with columns: date, value; at least 36 months)", type="csv")
    series, is_demo = None, True
    if up is not None:
        try:
            u = pd.read_csv(up)
            u["date"] = pd.to_datetime(u["date"]).dt.to_period("M").dt.to_timestamp()
            u = u.groupby("date", as_index=False)["value"].mean().sort_values("date")
            if len(u) < 36:
                st.error("Need at least 36 monthly values. Using the demo series instead.")
            else:
                series, is_demo = u, False
        except Exception as e:
            st.error(f"Could not read the file ({e}). It needs columns named date and value. Using the demo series instead.")
    if series is None:
        fd = st.selectbox("Demo district", sorted(districts), key="fc_dist")
        series = demo_milk_series(fd)
    H = 12
    ti = ((series["date"].dt.year - series["date"].dt.year.min()) * 12 + series["date"].dt.month).values
    y_ = series["value"].values.astype(float)
    # backtest: train on everything but the last 12 months, predict those 12, compare with "same month last year"
    tr = np.arange(len(y_)) < len(y_) - 12
    bt = np.linalg.lstsq(season_matrix(ti[tr]), y_[tr], rcond=None)[0]
    pred_bt = season_matrix(ti[~tr]) @ bt
    mae_model = np.abs(y_[~tr] - pred_bt).mean()
    mae_naive = np.abs(y_[~tr] - y_[np.roll(np.arange(len(y_)), 12)][~tr]).mean() if len(y_) >= 24 else float("nan")
    # final fit on all data and forecast the next 12 months
    bf = np.linalg.lstsq(season_matrix(ti), y_, rcond=None)[0]
    resid = y_ - season_matrix(ti) @ bf
    sig = resid.std(ddof=season_matrix(ti).shape[1])
    ft_dates = pd.date_range(series["date"].max() + pd.offsets.MonthBegin(1), periods=H, freq="MS")
    ft_idx = ti[-1] + np.arange(1, H + 1)
    fc = season_matrix(ft_idx) @ bf
    fig_f = go.Figure()
    fig_f.add_trace(go.Scatter(x=series["date"], y=y_, mode="lines+markers", name="history" + (" (SYNTHETIC)" if is_demo else "")))
    fig_f.add_trace(go.Scatter(x=list(ft_dates) + list(ft_dates[::-1]), y=list(fc + 1.28 * sig) + list((fc - 1.28 * sig)[::-1]),
                               fill="toself", line=dict(width=0), name="80% range", opacity=0.25))
    fig_f.add_trace(go.Scatter(x=ft_dates, y=fc, mode="lines+markers", name="forecast", line=dict(dash="dash")))
    fig_f.update_layout(height=420, margin=dict(l=0, r=0, t=10, b=0), yaxis_title="value")
    show_chart(st, fig_f, width="stretch")
    f1, f2, f3 = st.columns(3)
    f1.metric("Backtest error, this model (last 12 months)", f"{mae_model:.2f}")
    f2.metric("Backtest error, 'same as last year'", f"{mae_naive:.2f}")
    f3.metric("Lowest forecast month", ft_dates[int(np.argmin(fc))].strftime("%b %Y"))
    st.caption("Method: linear trend plus yearly seasonal curves, fitted by least squares (statistical learning, not deep learning). "
               "The 80% range is +/-1.28 residual standard deviations and is approximate. The backtest compares the model with simply repeating last year; "
               "if the model is not clearly better, do not trust it. A forecast is only as good as its history: with real data, add rainfall as an input.")

# --- 5. report an issue ---
with t_report:
    st.markdown("---")
    st.subheader(T("Report an issue (demo)"))
    st.caption("Reports are kept only in this browser session. A live system would send them to the district office.")
    if "reports" not in st.session_state:
        st.session_state["reports"] = []
    with st.form("report"):
        kind = st.selectbox("Issue", ["Crop pest or disease", "Hail or flood damage", "Sick animals", "Dry spell"])
        where = st.selectbox("District", districts)
        note = st.text_input("Details (optional)")
        if st.form_submit_button("Submit report"):
            st.session_state["reports"].append({"issue": kind, "district": where, "details": note})
    if st.session_state["reports"]:
        st.dataframe(pd.DataFrame(st.session_state["reports"]), hide_index=True, width="stretch")


# --- method & validation ---
with t_method:
    st.markdown(f'<div class="h2">{T("How Intumwa works")}</div><div class="muted">Transparent rules on real NISR data, so a district '
                'officer can see exactly why a warning was raised.</div>', unsafe_allow_html=True)
    m1, m2, m3 = st.columns(3)
    m1.markdown('<div class="step"><b>1. Hazard (0 to 100)</b><br>How far rainfall is from normal. 0 at normal rainfall, 100 at a '
                '50% deficit (drought) or 50% excess (heavy rain). Set by a scenario slider, or from NASA rainfall when that file is loaded.</div>',
                unsafe_allow_html=True)
    m2.markdown('<div class="step"><b>2. Vulnerability (0 to 100)</b><br>The average of seven weaknesses measured in the NISR '
                'Agriculture Household Survey 2024: poverty, extreme poverty, no extension advice, no bank or mobile-money account, '
                'no improved seed, land under 0.5 ha, not in a cooperative.</div>', unsafe_allow_html=True)
    m3.markdown('<div class="step"><b>3. Risk and tier</b><br>Risk = hazard / 100 x vulnerability. Low below 15, Elevated 15 to 30, '
                'High 30 or more. Livestock risk also uses how many households keep cattle. Districts with fewer than 30 survey '
                'households get no tier.</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<div class="h2">Validation against NISR\'s published figures</div><div class="muted">We rebuilt the national and '
                'provincial values from the household data and compared them with the published AHS 2024 report tables. '
                'Numbers are recomputed live from the district file.</div>', unsafe_allow_html=True)
    def inv(g):
        w = g["est_households"]
        f = lambda c: float(np.average(g[c], weights=w) * 100)
        return {"improved_seed": 100 - f("no_improved_seed"), "extension": 100 - f("no_extension"),
                "cooperative": 100 - f("no_cooperative"), "bank_account": 100 - f("no_account"),
                "farm_under_half_ha": f("small_farm_lt_half_ha"), "poverty": f("poverty_rate")}
    vals = {p: inv(g) for p, g in df.groupby("province")}
    vals["Rwanda"] = inv(df)
    vv = pd.DataFrame([(ind, p, v) for p, d_ in vals.items() for ind, v in d_.items()], columns=["indicator", "province", "intumwa_pct"])
    cmp_ = vv.merge(bench, on=["indicator", "province"])
    cmp_["diff"] = cmp_["intumwa_pct"] - cmp_["nisr_pct"]
    core = cmp_[cmp_["indicator"] != "poverty"]
    ok = int((core["diff"].abs() < 0.25).sum())
    st.markdown(f'<div class="good"><b>{ok} of {len(core)}</b> comparisons for the six non-poverty indicators match NISR within 0.25 percentage points '
                f'(five provinces plus the national figure).</div>', unsafe_allow_html=True)
    cols_order = ["Kigali", "South", "West", "North", "East", "Rwanda"]
    piv = cmp_.pivot(index="indicator", columns="province", values="diff")[cols_order]
    piv.index = [{"improved_seed": "Used improved seed (Table 19)", "extension": "Received extension (Table 27)",
                  "cooperative": "In a cooperative (Table 30)", "bank_account": "Has a bank account (Table 32)",
                  "farm_under_half_ha": "Farm under 0.5 ha (Table 14)", "poverty": "Poverty (Table 2)"}[i] for i in piv.index]
    sty = piv.style.format("{:+.1f}")
    sty = (getattr(sty, "map", None) or sty.applymap)(lambda v: "background-color:#E8F5EC" if abs(v) < 0.25 else "background-color:#FDEBD0")
    st.caption("Difference in percentage points (Intumwa minus NISR). Green = within 0.25.")
    st.dataframe(sty, width="stretch")
    pov_n = cmp_[(cmp_["indicator"] == "poverty") & (cmp_["province"] == "Rwanda")].iloc[0]
    st.markdown(f'<div class="callout"><b>One known gap: poverty.</b> It is {pov_n["intumwa_pct"]:.1f}% here against '
                f'{pov_n["nisr_pct"]:.1f}% in the NISR report, lower by a similar proportion (about 13%) in every province, which points to a '
                'different poverty variable or definition rather than sampling noise. We tested the effect: forcing poverty to match NISR\'s '
                'provincial values changes the vulnerability index by at most 0.3 points, the district ranking is unchanged '
                '(rank correlation 0.999) and no district changes tier.</div>', unsafe_allow_html=True)
    with st.expander("See the underlying numbers"):
        st.dataframe(cmp_.round(1), hide_index=True, width="stretch")

    st.markdown("---")
    st.markdown(f'<div class="h2">{T("What it is, and what it is not")}</div>', unsafe_allow_html=True)
    g1, g2 = st.columns(2)
    g1.markdown("**Strengths**\n- Built on NISR's own household survey and checked against NISR's published tables.\n"
                "- Every alert shows its reason; nothing is a black box.\n"
                "- Works on any basic phone (SMS and USSD, Kinyarwanda first).\n"
                "- One shared hazard signal serves both crops and livestock.\n"
                "- Honest about limits, with validation reported even when weak.")
    g2.markdown("**Limits**\n- A risk signal, not a forecast: one survey year cannot support a trained forecasting model.\n"
                "- Rainfall is a scenario by default. Real and live rainfall switch on after one run of fetch_rainfall.py; forecasts beyond about 7 days are uncertain.\n"
                "- No disease, pest or crop-price data yet; movement restrictions are entered from RAB notices.\n"
                "- SMS and USSD are simulated; a launch needs a telecom partner.\n"
                "- Kinyarwanda texts still need native-speaker review.")
    st.markdown('<div class="h3">From risk signal to forecast: the next steps</div>', unsafe_allow_html=True)
    n1, n2, n3, n4 = st.columns(4)
    n1.markdown('<div class="step"><b>Now</b><br>Risk map, alerts, USSD and dashboards on real NISR data, with live rainfall (Open-Meteo) and NISR catalogue lookups.</div>', unsafe_allow_html=True)
    n2.markdown('<div class="step"><b>Next</b><br>Load real rainfall, test it against farmers\' reported causes of poor harvests in the survey.</div>', unsafe_allow_html=True)
    n3.markdown('<div class="step"><b>Then</b><br>Add RAB disease and Meteo Rwanda data; pilot alerts in two districts with a telecom partner.</div>', unsafe_allow_html=True)
    n4.markdown('<div class="step"><b>Later</b><br>Multi-year Seasonal Agriculture Survey data to train and test real forecasts.</div>', unsafe_allow_html=True)

with t_method:
    st.markdown("---")
    st.markdown(f'<div class="h2">{T("Data sources and APIs")}</div><div class="muted">What is bundled, what is called live, and whether it worked just now.</div>', unsafe_allow_html=True)
    cat_rows, cat_status = nisr_catalog()
    om = "LIVE this session" if source.startswith("Live") else ("available (select it in the sidebar)" if NORMALS is not None else "off: run fetch_rainfall.py first")
    src_tbl = pd.DataFrame([
        ("NISR Agriculture Household Survey 2024 (microdata)", "Vulnerability index, yields", "Built offline; household data not redistributed", "bundled district tables"),
        ("NISR AHS 2024 report (Aug 2025)", "Province benchmarks, milk, weather information", "Transcribed tables, listed with table numbers", "bundled"),
        ("NISR microdata catalogue API (NADA)", "Provenance of the survey record", "microdata.statistics.gov.rw/index.php/api/catalog/search", ("OK" if cat_status["ok"] and cat_rows else ("reachable, no match" if cat_status["ok"] else "offline here"))),
        ("NASA POWER API", "1991-2020 rainfall normals", "power.larc.nasa.gov, run once by fetch_rainfall.py", "files present" if NORMALS is not None else "not run yet"),
        ("Open-Meteo API", "Live rainfall, last 30 days + 14-day forecast", "api.open-meteo.com/v1/forecast (no key)", om)],
        columns=["Source", "Used for", "Access", "Status"])
    st.dataframe(src_tbl, hide_index=True, width="stretch")
    if cat_rows:
        st.markdown("**NISR microdata catalogue, live search for the survey record:**")
        for r_ in cat_rows[:4]:
            st.markdown(f"- [{r_['title']}]({r_['link']}) ({r_['year']})")
    else:
        st.caption(cat_status["message"] + ". The survey is cited from the published report instead (this does not affect any score).")

st.markdown('<div class="foot"><b>Data:</b> NISR Agriculture Household Survey 2024 and the AHS 2024 report (August 2025); '
            'rainfall from NASA POWER when loaded. <b>Note:</b> a risk signal, not a forecast; SMS and USSD are simulated. '
            'Built for the NISR 2026 Big Data Hackathon, Track 1: Agricultural Productivity.</div>', unsafe_allow_html=True)
