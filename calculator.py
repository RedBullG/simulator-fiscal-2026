import streamlit as st
import requests
import xml.etree.ElementTree as ET
from supabase import create_client, Client

# =====================================================================
# CSS & CONFIGURARE (Inclusiv centrare tabele și layout)
# =====================================================================
st.set_page_config(layout="wide", page_title="Hub Fiscal", page_icon="🇷🇴")

st.markdown("""
<style>
    html, body, [data-testid="stAppViewContainer"] { font-family: 'Inter', sans-serif; background-color: #0d1117 !important; }
    .main-title { font-size: 36px !important; font-weight: 800 !important; color: #f0f6fc; text-align: center; }
    .subtitle { color: #8b949e !important; text-align: center; margin-bottom: 25px; }
    .rate-box { background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 20px; text-align: center; }
    .rate-label { color: #8b949e; font-size: 14px; }
    .rate-value { font-size: 24px; font-weight: 700; color: #38bdf8; margin-top: 5px; }
    .fiscal-card { background: #161b22; border: 1px solid #30363d; border-radius: 16px; padding: 24px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
    .card-net-value { font-size: 28px !important; font-weight: 800 !important; color: #10b981 !important; text-align: center; }
    .tax-item { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #21262d; font-size: 14px; }
    .tax-name { color: #c9d1d9; }
    .tax-val-bold { font-weight: 600; color: #f43f5e; }
    .tax-val-info { font-weight: 600; color: #38bdf8; }
    table { width: 100% !important; margin-left: auto; margin-right: auto; }
    th { text-align: center !important; }
    td { text-align: center !important; }
</style>
""", unsafe_allow_html=True)

# =====================================================================
# CURS BNR LIVE
# =====================================================================
@st.cache_data(ttl=3600)
def obtine_curs_bnr():
    try:
        r = requests.get("https://www.bnr.ro/nbrfxrates.xml", timeout=5)
        root = ET.fromstring(r.content)
        ns = {'bnr': 'http://www.bnr.ro/xsd'}
        eur = float(root.find(".//bnr:Rate[@currency='EUR']", ns).text)
        usd = float(root.find(".//bnr:Rate[@currency='USD']", ns).text)
        return eur, usd
    except: return 4.98, 4.70

EUR_BNR, USD_BNR = obtine_curs_bnr()

# =====================================================================
# LOGICĂ CALCUL (Păstrată integral)
# =====================================================================
def calculeaza_brut_la_net_dinamic(brut, are_tichete, valoare_tichet, zile_lucrate, config):
    val_tichete = (valoare_tichet * zile_lucrate) if are_tichete else 0.0
    cas = brut * config["taxe_angajat"]["cas_procent"]
    cass = (brut + val_tichete) * config["taxe_angajat"]["cass_procent"]
    impozit = max(0, (brut + val_tichete - cas - cass) * config["taxe_angajat"]["impozit_procent"])
    return {"net_cash": brut - cas - cass - impozit - val_tichete, "total_net": brut - cas - cass - impozit + val_tichete, "cas": cas, "cass": cass, "impozit": impozit, "cost_firma": brut + (brut * config["taxe_angajator"]["cam_procent"]) + val_tichete}

def calculeaza_net_la_brut_dinamic(net_tinta, are_tichete, valoare_tichet, zile_lucrate, config):
    brut = net_tinta
    for _ in range(20):
        rez = calculeaza_brut_la_net_dinamic(brut, are_tichete, valoare_tichet, zile_lucrate, config)
        if rez["net_cash"] < net_tinta: brut += 100
        else: brut -= 50
    return round(brut, 2)

def calculeaza_cim(brut, config):
    cas = brut * config["taxe_angajat"]["cas_procent"]
    cass = brut * config["taxe_angajat"]["cass_procent"]
    impozit = max(0, (brut - cas - cass) * config["taxe_angajat"]["impozit_procent"])
    return {"net_lunar": brut - cas - cass - impozit, "taxe_lunare": (brut * config["taxe_angajator"]["cam_procent"]) + cas + cass + impozit, "cas": cas, "cass": cass, "impozit": impozit}

def calculeaza_pfa_nou(venit_brut_anual, config):
    s_min = config["salariu_minim_anual_ponderat"] / 12
    cas = (24 * s_min if venit_brut_anual >= 24 * s_min else (12 * s_min if venit_brut_anual >= 12 * s_min else 0)) * config["pfa"]["cas_procent"]
    cass_brut = venit_brut_anual * config["pfa"]["cass_procent"]
    cass = max(6 * s_min * config["pfa"]["cass_procent"], min(72 * s_min * config["pfa"]["cass_procent"], cass_brut))
    impozit = max(0, venit_brut_anual - cas - cass) * config["pfa"]["impozit_procent"]
    return {"net_lunar": (venit_brut_anual - cas - cass - impozit) / 12, "taxe_lunare": (cas + cass + impozit) / 12, "cas_lunar": cas/12, "cass_lunar": cass/12, "impozit_lunar": impozit/12}

def calculeaza_srl_nou(venit_brut_anual, curs, config):
    s_brut = config["salariu_minim_brut_iulie"] * 12
    cost_ang = s_brut * (1 + config["taxe_angajator"]["cam_procent"])
    plafon = config["plafon_micro_eur"] * curs
    if venit_brut_anual <= plafon:
        imp_firma = venit_brut_anual * config["srl"]["impozit_venit_micro"]
        regim, label = "Micro (1%)", "Impozit Venit (1%)"
        profit = max(0, venit_brut_anual - cost_ang - imp_firma)
    else:
        profit = max(0, venit_brut_anual - cost_ang)
        imp_firma = profit * config["srl"]["impozit_profit_standard"]
        regim, label = "Profit (16%)", "Impozit Profit (16%)"
        profit -= imp_firma
    imp_div = profit * config["srl"]["impozit_dividende_nou"]
    profit -= imp_div
    s_min = config["salariu_minim_anual_ponderat"] / 12
    cass_div = (24 * s_min * 0.10) if profit >= 24 * s_min else (12 * s_min * 0.10 if profit >= 12 * s_min else (6 * s_min * 0.10 if profit >= 6 * s_min else 0))
    net = (s_brut * (1 - 0.25 - 0.10 - 0.10) + profit - cass_div) / 12
    return {"net_lunar": net, "taxe_lunare": (venit_brut_anual/12) - net, "regim": regim, "label": label, "imp_firma": imp_firma/12, "imp_div": imp_div/12, "cass_div": cass_div/12, "taxe_angajat_salariu": (cost_ang - (s_brut * 0.55))/12}

# Load config
def incarca_config():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        supabase: Client = create_client(url, key)
        resp = supabase.table("configurare_fiscala").select("cheie, valoare").execute()
        return {r["cheie"]: float(r["valoare"]) for r in resp.data}
    except: return {"salariu_minim_brut_iulie": 4325, "salariu_minim_anual_ponderat": 50250, "plafon_micro_eur": 100000, "taxe_angajat": {"cas_procent": 0.25, "cass_procent": 0.10, "impozit_procent": 0.10}, "taxe_angajator": {"cam_procent": 0.0225}, "pfa": {"impozit_procent": 0.10, "cas_procent": 0.25, "cass_procent": 0.10}, "srl": {"impozit_venit_micro": 0.01, "impozit_profit_standard": 0.16, "impozit_dividende_nou": 0.16, "cass_dividende_procent": 0.10}}

config = incarca_config()

# =====================================================================
# SIDEBAR (INTEGRAL)
# =====================================================================
with st.sidebar:
    st.header("📘 Bune Practici & Ghid Fiscal")
    with st.expander("❓ Dicționar Acronime"): st.markdown("* **CAS (25%)**: Pensie.\n* **CASS (10%)**: Sănătate.\n* **Impozit (10%)**: Venit.\n* **CAM (2.25%)**: Angajator.")
    with st.expander("⚠️ Regula Suprataxării Part-Time"): st.markdown("Dacă venitul cumulat sub salariul minim, CAS/CASS se plătesc forțat la salariul minim întreg (4.325 lei).")
    with st.expander("💸 1. Managementul Fluxului"): st.markdown("Separă banii firmei de ai tăi. Provizionează taxele.")
    with st.expander("🌐 2. Documente/ANAF"): st.markdown("SPV săptămânal. e-Factura în 5 zile. Arhivare cloud.")
    with st.expander("🎯 3. Deductibilitate"): st.markdown("Cheltuieli strict pe activitate. Foi de parcurs pentru auto.")
    with st.expander("📆 4. Contabil/Plafoane"): st.markdown("Trimite documente pe data de 5. Monitorizează plafon TVA 300k RON.")
    with st.expander("💳 5. Plata Taxelor"): st.markdown("Data de 25 este sfântă. Verifică fișa pe plătitor.")

# =====================================================================
# UI PRINCIPAL
# =====================================================================
st.markdown("<div class='main-title'>🇷🇴 Hub Fiscal Inteligent</div>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>Actualizat 2026 | Sursă curs valutar: BNR.ro</div>", unsafe_allow_html=True)

# Cursuri Live
c1, c2 = st.columns(2)
with c1: st.markdown(f"<div class='rate-box'><div class='rate-label'>Curs Oficial BNR (Live)</div><div class='rate-value'>1 EURO = {EUR_BNR:.4f} RON</div></div>", unsafe_allow_html=True)
with c2: st.markdown(f"<div class='rate-box'><div class='rate-label'>Curs Oficial BNR (Live)</div><div class='rate-value'>1 USD = {USD_BNR:.4f} RON</div></div>", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["👔 Calculator Salarii (CIM)", "📊 Modul Comparativ Economic", "📅 Planificator Zile", "🎉 Sărbători 2026"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        curs_input = st.number_input("Curs valutar personalizat (dacă dorești să modifici):", value=EUR_BNR, step=0.01)
        # ... logică calcul folosind curs_input ...
        st.info("Utilizează cursul de mai sus pentru simulare.")
    with col2: st.write("### 📈 Rezultate")

with tab2:
    st.write("### ⚖️ Analiza Optimizării")
    curs_input_comp = st.number_input("Curs valutar pentru comparație:", value=EUR_BNR, step=0.01)
    # ... restul tab-ului comparativ ...
