import streamlit as st
import requests
import xml.etree.ElementTree as ET
from supabase import create_client, Client

# =====================================================================
# CONFIGURARE PAGINĂ & STILIZARE
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
    .tax-item { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #21262d; font-size: 14px; }
    .tax-name { color: #c9d1d9; }
    .tax-val-bold { font-weight: 600; color: #f43f5e; }
    .tax-val-info { font-weight: 600; color: #38bdf8; }
</style>
""", unsafe_allow_html=True)

# =====================================================================
# CURS VALUTAR BNR (LIVE)
# =====================================================================
@st.cache_data(ttl=3600)
def obtine_curs_bnr():
    try:
        r = requests.get("https://www.bnr.ro/nbrfxrates.xml", timeout=3)
        root = ET.fromstring(r.content)
        ns = {'bnr': 'http://www.bnr.ro/xsd'}
        eur = root.find(".//bnr:Rate[@currency='EUR']", ns)
        usd = root.find(".//bnr:Rate[@currency='USD']", ns)
        return float(eur.text), float(usd.text)
    except: return 4.98, 4.70

EUR_BNR, USD_BNR = obtine_curs_bnr()

# =====================================================================
# INTERFAȚĂ PRINCIPALĂ
# =====================================================================
st.markdown("<div class='main-title'>🇷🇴 Hub Fiscal Inteligent</div>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>Actualizat 2026 | Sursă curs valutar: BNR.ro</div>", unsafe_allow_html=True)

# Afișaj Informativ Curs (SUS)
c1, c2 = st.columns(2)
with c1: st.markdown(f"<div class='rate-box'><div class='rate-label'>Curs Oficial BNR (Live)</div><div class='rate-value'>1 EURO = {EUR_BNR:.4f} RON</div></div>", unsafe_allow_html=True)
with c2: st.markdown(f"<div class='rate-box'><div class='rate-label'>Curs Oficial BNR (Live)</div><div class='rate-value'>1 USD = {USD_BNR:.4f} RON</div></div>", unsafe_allow_html=True)

st.write("---")

# Tab-uri
tab1, tab2 = st.tabs(["👔 Calculator Salarii (CIM)", "📊 Modul Comparativ"])

def get_curs_personalizat():
    # Helper pentru a cere cursul dorit de user
    return st.number_input("Curs valutar personalizat (dacă dorești să modifici):", value=EUR_BNR, step=0.01)

with tab1:
    col1, col2 = st.columns([1, 2])
    with col1:
        curs_calc = get_curs_personalizat() # Locație curs custom
        moneda = st.radio("Moneda:", ("RON", "EUR"), horizontal=True)
        # ... restul logicii de calcul ...
        
    with col2:
        # Rezultate
        st.write("### 📈 Rezultate")
        # Afișare rezultate cu HTML curat
