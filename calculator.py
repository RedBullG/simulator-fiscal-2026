import streamlit as st
import requests
import xml.etree.ElementTree as ET
from supabase import create_client, Client

# =====================================================================
# CONFIGURARE PAGINĂ & STILIZARE CSS
# =====================================================================
st.set_page_config(layout="wide", page_title="Hub Fiscal Inteligent", page_icon="🇷🇴")

st.markdown("""
<style>
    html, body, [data-testid="stAppViewContainer"] { font-family: 'Inter', sans-serif; background-color: #0d1117 !important; }
    .main-title { font-size: 36px !important; font-weight: 800 !important; color: #f0f6fc; text-align: center; }
    .subtitle { color: #8b949e !important; text-align: center; margin-bottom: 25px; }
    .rate-container { display: flex; gap: 20px; justify-content: center; margin-bottom: 30px; }
    .rate-box { background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 15px 30px; text-align: center; width: 100%; max-width: 300px; }
    .rate-label { color: #8b949e; font-size: 13px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px; }
    .rate-value { font-size: 22px; font-weight: 700; color: #38bdf8; }
    .fiscal-card { background: #161b22; border: 1px solid #30363d; border-radius: 16px; padding: 24px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
    .card-net-value { font-size: 28px !important; font-weight: 800 !important; color: #10b981 !important; text-align: center; margin-top: 10px; margin-bottom: 20px; }
    .tax-breakdown-title { font-size: 13px; font-weight: 600; color: #8b949e; text-transform: uppercase; text-align: center; margin-bottom: 15px; }
    .tax-item { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #21262d; font-size: 14px; }
    .tax-name { color: #c9d1d9; }
    .tax-val-bold { font-weight: 600; color: #f43f5e; }
    .tax-val-info { font-weight: 600; color: #38bdf8; }
    table { width: 100% !important; margin-left: auto; margin-right: auto; }
    th, td { text-align: center !important; }
    .info-text { color: #c9d1d9; font-size: 14px; line-height: 1.6; }
</style>
""", unsafe_allow_html=True)

# =====================================================================
# CURS VALUTAR BNR (LIVE)
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
    except:
        return 4.98, 4.70

EUR_BNR, USD_BNR = obtine_curs_bnr()

# =====================================================================
# CONEXIUNE SUPABASE & FALLBACK
# =====================================================================
@st.cache_data(ttl=600)
def incarca_config():
    config_fallback = {
        "salariu_minim_brut_iulie": 4325, "salariu_minim_anual_ponderat": 50250, "plafon_micro_eur": 100000,
        "taxe_angajat": {"cas_procent": 0.25, "cass_procent": 0.10, "impozit_procent": 0.10},
        "taxe_angajator": {"cam_procent": 0.0225},
        "pfa": {"impozit_procent": 0.10, "cas_procent": 0.25, "cass_procent": 0.10},
        "srl": {"impozit_venit_micro": 0.01, "impozit_profit_standard": 0.16, "impozit_dividende_nou": 0.16, "cass_dividende_procent": 0.10}
    }
    try:
        if "SUPABASE_URL" in st.secrets and "SUPABASE_KEY" in st.secrets:
            supabase: Client = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
            resp = supabase.table("configurare_fiscala").select("cheie, valoare").execute()
            data = {r["cheie"]: float(r["valoare"]) for r in resp.data}
            if data: return {
                "salariu_minim_brut_iulie": data.get("salariu_minim_brut_iulie", 4325),
                "salariu_minim_anual_ponderat": data.get("salariu_minim_anual_ponderat", 50250),
                "plafon_micro_eur": data.get("plafon_micro_eur", 100000),
                "taxe_angajat": {"cas_procent": data.get("cas_procent", 0.25), "cass_procent": data.get("cass_procent", 0.10), "impozit_procent": data.get("impozit_procent", 0.10)},
                "taxe_angajator": {"cam_procent": data.get("cam_procent", 0.0225)},
                "pfa": {"impozit_procent": data.get("impozit_procent", 0.10), "cas_procent": data.get("cas_procent", 0.25), "cass_procent": data.get("cass_procent", 0.10)},
                "srl": {"impozit_venit_micro": data.get("impozit_venit_micro", 0.01), "impozit_profit_standard": data.get("impozit_profit_standard", 0.16), "impozit_dividende_nou": data.get("impozit_dividende_nou", 0.16), "cass_dividende_procent": data.get("cass_procent", 0.10)}
            }
    except:
        pass
    return config_fallback

config_fiscal = incarca_config()

# =====================================================================
# LOGICĂ DE CALCUL
# =====================================================================
def calculeaza_brut_la_net_dinamic(brut, are_tichete, valoare_tichet, zile_lucrate, config):
    val_tichete = (valoare_tichet * zile_lucrate) if are_tichete else 0.0
    cas = brut * config["taxe_angajat"]["cas_procent"]
    cass = (brut + val_tichete) * config["taxe_angajat"]["cass_procent"]
    impozit = max(0, (brut + val_tichete - cas - cass) * config["taxe_angajat"]["impozit_procent"])
    return {"net_cash": brut - cas - cass - impozit - val_tichete, "total_net": brut - cas - cass - impozit + val_tichete, "cas": cas, "cass": cass, "impozit": impozit, "cost_firma": brut + (brut * config["taxe_angajator"]["cam_procent"]) + val_tichete, "valoare_tichete": val_tichete}

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

# =====================================================================
# SIDEBAR (BUNE PRACTICI)
# =====================================================================
with st.sidebar:
    st.header("📘 Bune Practici & Ghid Fiscal")
    with st.expander("❓ Dicționar Acronime"):
        st.markdown("* **CAS (25%)**: Contribuția pentru pensie.\n* **CASS (10%)**: Asigurarea medicală (CNAS).\n* **Impozit (10%)**: Taxa generală pe venit.\n* **CAM (2.25%)**: Contribuție plătită strict de angajator.")
    with st.expander("⚠️ Regula Suprataxării Part-Time"):
        st.markdown(f"Dacă venitul cumulat este sub salariul minim pe țară, **CAS și CASS se plătesc forțat la nivelul unui salariu întreg de {config_fiscal['salariu_minim_brut_iulie']:.0f} lei**, chiar dacă angajatul lucrează doar 2 ore pe zi.")
    with st.expander("💸 1. Managementul Fluxului de Bani"):
        st.markdown("Separă total banii firmei de cumpărăturile personale. Provizionează mereu taxele într-un cont bancar separat de economii la fiecare încasare.")
    with st.expander("🌐 2. Documente și ANAF"):
        st.markdown("Verifică Spațiul Privat Virtual (SPV) săptămânal. Facturile B2B trebuie trimise obligatoriu în e-Factura în 5 zile calendaristice.")
    with st.expander("🎯 3. Justificarea Cheltuielilor"):
        st.markdown("Cheltuielile sunt deductibile doar dacă servesc activității economice. Pentru a deduce 100% cheltuielile auto, ai nevoie de foi de parcurs.")
    with st.expander("📆 4. Relația cu Contabilul"):
        st.markdown("Trimite toate documentele lunare până pe data de 5 a lunii următoare. Fii atent la plafoanele de trecere la TVA (300.000 lei).")
    with st.expander("💳 5. Plata Taxelor"):
        st.markdown("Data de 25 a lunii este termenul limită sfânt. Plățile întârziate generează penalități. Cere periodic fișa pe plătitor.")

# =====================================================================
# INTERFAȚĂ PRINCIPALĂ
# =====================================================================
st.markdown("<div class='main-title'>🇷🇴 Hub Fiscal Inteligent</div>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>Actualizat 2026 | Sursă curs valutar: BNR.ro</div>", unsafe_allow_html=True)

# Afișaj Informativ Curs (Carduri Sus)
col_a, col_b = st.columns(2)
with col_a: st.markdown(f"<div class='rate-box'><div class='rate-label'>Curs Oficial BNR (Live)</div><div class='rate-value'>1 EURO = {EUR_BNR:.4f} RON</div></div>", unsafe_allow_html=True)
with col_b: st.markdown(f"<div class='rate-box'><div class='rate-label'>Curs Oficial BNR (Live)</div><div class='rate-value'>1 USD = {USD_BNR:.4f} RON</div></div>", unsafe_allow_html=True)

st.write("---")

tab1, tab2, tab3, tab4 = st.tabs([
    "👔 Calculator Salarii (CIM)", 
    "📊 Modul Comparativ Economic", 
    "📅 Planificator Zile Lucrătoare", 
    "🎉 Sărbători Legale 2026"
])

# ---------------------------------------------------------------------
# TAB 1: CALCULATOR ANGAJAȚI
# ---------------------------------------------------------------------
with tab1:
    col_stg, col_drp = st.columns([1, 1], gap="large")
    with col_stg:
        st.write("### ⚙️ Parametri Contract")
        
        # Căsuța de curs mutat aici, perfect vizibilă, dar neintruzivă
        curs_personalizat = st.number_input("Curs valutar calcul (RON/EUR):", value=EUR_BNR, step=0.01, key="curs_t1")
        st.markdown("<br>", unsafe_allow_html=True)
        
        moneda = st.radio("Moneda:", ("RON", "EUR"), horizontal=True, key="mon_t1")
        tip_calcul = st.radio("Suma introdusă este:", ("Brut (Salariul de bază)", "Net (Banii pe card)"), horizontal=True)
        
        st.markdown("---")
        are_tichete = st.checkbox("Include tichete de masă?")
        valoare_tichet, zile_lucrate = 0.0, 0
        if are_tichete:
            c1, c2 = st.columns(2)
            with c1: valoare_tichet = st.number_input("Valoare nominală tichet (RON):", min_value=0.0, value=35.0, step=5.0)
            with c2: zile_lucrate = st.number_input("Zile lucrătoare:", min_value=0, max_value=31, value=21)
            
        suma_introdusa = st.number_input(f"Introduceți valoarea ({moneda}):", min_value=0.0, value=5000.0 if moneda == "RON" else 1000.0, step=100.0)
        
        # Logica
        suma_ron = suma_introdusa * curs_personalizat if moneda == "EUR" else suma_introdusa
        if "Brut" in tip_calcul:
            brut_final_ron = suma_ron
            rez = calculeaza_brut_la_net_dinamic(brut_final_ron, are_tichete, valoare_tichet, zile_lucrate, config_fiscal)
        else:
            brut_final_ron = calculeaza_net_la_brut_dinamic(suma_ron, are_tichete, valoare_tichet, zile_lucrate, config_fiscal)
            rez = calculeaza_brut_la_net_dinamic(brut_final_ron, are_tichete, valoare_tichet, zile_lucrate, config_fiscal)

    with col_drp:
        st.write("### 📈 Rezultate Extrase")
        net_afisat = rez['net_cash'] if moneda == "RON" else rez['net_cash'] / curs_personalizat
        cost_afisat = rez['cost_firma'] if moneda == "RON" else rez['cost_firma'] / curs_personalizat
        brut_afisat = brut_final_ron if moneda == "RON" else brut_final_ron / curs_personalizat
        
        str_brut = f"{brut_afisat:.2f} {moneda}"
        str_cas = f"{(rez['cas'] if moneda == 'RON' else rez['cas']/curs_personalizat):.2f} {moneda}"
        str_cass = f"{(rez['cass'] if moneda == 'RON' else rez['cass']/curs_personalizat):.2f} {moneda}"
        str_imp = f"{(rez['impozit'] if moneda == 'RON' else rez['impozit']/curs_personalizat):.2f} {moneda}"
        str_cost = f"{cost_afisat:.2f} {moneda}"
        
        html_t1 = "<div class='fiscal-card'>"
        html_t1 += "<div style='text-align:center;'><div class='card-badge badge-cim'>Contract Individual de Muncă</div></div>"
        html_t1 += f"<div class='card-net-value'>{net_afisat:.2f} {moneda}</div>"
        html_t1 += "<div class='tax-breakdown-title'>Detaliere rețineri și contribuții:</div>"
        html_t1 += f"<div class='tax-item'><span class='tax-name'>Salariu Brut Contractual:</span><span class='tax-val'>{str_brut}</span></div>"
        html_t1 += f"<div class='tax-item'><span class='tax-name'>CAS (Pensie 25%):</span><span class='tax-val-bold'>{str_cas}</span></div>"
        html_t1 += f"<div class='tax-item'><span class='tax-name'>CASS (Sănătate 10%):</span><span class='tax-val-bold'>{str_cass}</span></div>"
        html_t1 += f"<div class='tax-item'><span class='tax-name'>Impozit pe Venit (10%):</span><span class='tax-val-bold'>{str_imp}</span></div>"
        
        if are_tichete:
            t_val = rez['valoare_tichete'] if moneda == "RON" else rez['valoare_tichete'] / curs_personalizat
            tot_val = rez['total_net'] if moneda == "RON" else rez['total_net'] / curs_personalizat
            html_t1 += f"<div class='tax-item'><span class='tax-name'>Card tichete de masă:</span><span class='tax-val-info'>{t_val:.2f} {moneda}</span></div>"
            html_t1 += f"<div class='tax-item'><span class='tax-name'><b>Total Net Real (Bani + Tichete):</b></span><span class='tax-val-info'><b>{tot_val:.2f} {moneda}</b></span></div>"
            
        html_t1 += f"<div class='tax-item' style='margin-top: 15px; border-top: 1px dashed #30363d; padding-top: 15px;'><span class='tax-name'><b>Cost Total Angajator:</b></span><span class='tax-val-info' style='font-size: 18px;'>{str_cost}</span></div>"
        html_t1 += "</div>"
        
        st.markdown(html_t1, unsafe_allow_html=True)

# ---------------------------------------------------------------------
# TAB 2: MODUL COMPARATIV ECONOMIC
# ---------------------------------------------------------------------
with tab2:
    st.write("### ⚖️ Analiza Optimizării Veniturilor dintr-un Buget Fix")
    c_m2, c_s2, c_c2 = st.columns([1, 1, 1])
    with c_m2: 
        moneda_t2 = st.radio("Valuta bugetului:", ("RON", "EUR"), horizontal=True, key="mon_t2")
    with c_s2: 
        b_introdus = st.number_input(f"Buget lunar total ({moneda_t2}):", min_value=500, value=15000 if moneda_t2 == "RON" else 3000, step=500)
    with c_c2:
        curs_comp = st.number_input("Curs valutar calcul (RON/EUR):", value=EUR_BNR, step=0.01, key="curs_t2")
    
    buget_lunar = b_introdus * curs_comp if moneda_t2 == "EUR" else b_introdus
    buget_anual = buget_lunar * 12
    rez_cim = calculeaza_cim(buget_lunar, config_fiscal)
    rez_pfa = calculeaza_pfa_nou(buget_anual, config_fiscal)
    rez_srl = calculeaza_srl_nou(buget_anual, curs_comp, config_fiscal)
    
    st.markdown("---")
    col1, col2, col3 = st.columns(3, gap="medium")
    coef = curs_comp if moneda_t2 == "EUR" else 1.0
    
    with col1:
        h_cim = "<div class='fiscal-card'>"
        h_cim += "<div style='text-align:center;'><div class='card-badge badge-cim'>Opțiunea 1</div></div>"
        h_cim += "<div style='text-align:center; color:#f0f6fc; font-size:20px; font-weight:700;'>👔 Angajat (CIM)</div>"
        h_cim += f"<div class='card-net-value'>{(rez_cim['net_lunar']/coef):.2f} {moneda_t2}</div>"
        h_cim += "<div class='tax-breakdown-title'>Taxe reținute detaliat:</div>"
        h_cim += f"<div class='tax-item'><span class='tax-name'>CAS (Pensie 25%):</span><span class='tax-val-bold'>{(rez_cim['cas']/coef):.2f} {moneda_t2}</span></div>"
        h_cim += f"<div class='tax-item'><span class='tax-name'>CASS (Sănătate 10%):</span><span class='tax-val-bold'>{(rez_cim['cass']/coef):.2f} {moneda_t2}</span></div>"
        h_cim += f"<div class='tax-item'><span class='tax-name'>Impozit pe Venit (10%):</span><span class='tax-val-bold'>{(rez_cim['impozit']/coef):.2f} {moneda_t2}</span></div>"
        h_cim += f"<div class='tax-item' style='margin-top:10px; border-top: 1px dashed #30363d; padding-top:10px;'><span class='tax-name'>Total Taxe CIM:</span><span class='tax-val-bold'>{(rez_cim['taxe_lunare']/coef):.2f} {moneda_t2}</span></div>"
        h_cim += "</div>"
        st.markdown(h_cim, unsafe_allow_html=True)
        
    with col2:
        h_pfa = "<div class='fiscal-card'>"
        h_pfa += "<div style='text-align:center;'><div class='card-badge badge-pfa'>Opțiunea 2</div></div>"
        h_pfa += "<div style='text-align:center; color:#f0f6fc; font-size:20px; font-weight:700;'>💼 PFA (Sistem Real)</div>"
        h_pfa += f"<div class='card-net-value'>{(rez_pfa['net_lunar']/coef):.2f} {moneda_t2}</div>"
        h_pfa += "<div class='tax-breakdown-title'>Contribuții estimate detaliat:</div>"
        h_pfa += f"<div class='tax-item'><span class='tax-name'>CAS (Pensie 25%):</span><span class='tax-val-bold'>{(rez_pfa['cas_lunar']/coef):.2f} {moneda_t2}</span></div>"
        h_pfa += f"<div class='tax-item'><span class='tax-name'>CASS (Sănătate 10%):</span><span class='tax-val-bold'>{(rez_pfa['cass_lunar']/coef):.2f} {moneda_t2}</span></div>"
        h_pfa += f"<div class='tax-item'><span class='tax-name'>Impozit pe Venit (10%):</span><span class='tax-val-bold'>{(rez_pfa['impozit_lunar']/coef):.2f} {moneda_t2}</span></div>"
        h_pfa += f"<div class='tax-item' style='margin-top:10px; border-top: 1px dashed #30363d; padding-top:10px;'><span class='tax-name'>Total Taxe PFA:</span><span class='tax-val-bold'>{(rez_pfa['taxe_lunare']/coef):.2f} {moneda_t2}</span></div>"
        h_pfa += "</div>"
        st.markdown(h_pfa, unsafe_allow_html=True)
        
    with col3:
        h_srl = "<div class='fiscal-card'>"
        h_srl += "<div style='text-align:center;'><div class='card-badge badge-srl'>Opțiunea 3</div></div>"
        h_srl += f"<div style='text-align:center; color:#f0f6fc; font-size:20px; font-weight:700;'>🏢 SRL ({rez_srl['regim']})</div>"
        h_srl += f"<div class='card-net-value'>{(rez_srl['net_lunar']/coef):.2f} {moneda_t2}</div>"
        h_srl += "<div class='tax-breakdown-title'>Impozite agregate detaliat:</div>"
        h_srl += f"<div class='tax-item'><span class='tax-name'>{rez_srl['label']}:</span><span class='tax-val-bold'>{(rez_srl['imp_firma']/coef):.2f} {moneda_t2}</span></div>"
        h_srl += f"<div class='tax-item'><span class='tax-name'>Impozit Dividende (16%):</span><span class='tax-val-bold'>{(rez_srl['imp_div']/coef):.2f} {moneda_t2}</span></div>"
        h_srl += f"<div class='tax-item'><span class='tax-name'>CASS Dividende (10%):</span><span class='tax-val-bold'>{(rez_srl['cass_div']/coef):.2f} {moneda_t2}</span></div>"
        h_srl += f"<div class='tax-item'><span class='tax-name'>Taxe Salariu Obligatoriu:</span><span class='tax-val-info'>{(rez_srl['taxe_angajat_salariu']/coef):.2f} {moneda_t2}</span></div>"
        h_srl += f"<div class='tax-item' style='margin-top:10px; border-top: 1px dashed #30363d; padding-top:10px;'><span class='tax-name'>Total Taxe SRL:</span><span class='tax-val-bold'>{(rez_srl['taxe_lunare']/coef):.2f} {moneda_t2}</span></div>"
        h_srl += "</div>"
        st.markdown(h_srl, unsafe_allow_html=True)

# ---------------------------------------------------------------------
# TAB 3: PLANIFICATOR ZILE LUCRĂTOARE
# ---------------------------------------------------------------------
with tab3:
    st.write("### 📅 Repartizarea orelor de muncă în funcție de contract (2026)")
    
    st.markdown("<div class='info-text'>În anul 2026, calendarul din România cuprinde un total de <b>250 de zile lucrătoare</b> (echivalentul a 2.000 de ore de muncă pentru un program normal de 8 ore/zi). Restul anului este format din 105 zile de weekend și 10 zile libere legale care cad în timpul săptămânii (dintr-un total de 17 sărbători oficiale).</div><br>", unsafe_allow_html=True)
    
    date_norme = {
        "Lună": ["Ianuarie", "Februarie", "Martie", "Aprilie", "Mai", "Iunie", "Iulie", "August", "Septembrie", "Octombrie", "Noiembrie", "Decembrie", "TOTAL ANUAL"],
        "Zile Lucrătoare": ["18", "20", "22", "20", "20", "21", "23", "21", "22", "22", "20", "21", "250"],
        "Normă 2h/zi": ["36", "40", "44", "40", "40", "42", "46", "42", "44", "44", "40", "42", "500"],
        "Normă 4h/zi": ["72", "80", "88", "80", "80", "84", "92", "84", "88", "88", "80", "84", "1000"],
        "Normă 6h/zi": ["108", "120", "132", "120", "120", "126", "138", "126", "132", "132", "120", "126", "1500"],
        "Normă 8h/zi": ["144", "160", "176", "160", "160", "168", "184", "168", "176", "176", "160", "168", "2000"]
    }
    st.table(date_norme)

    st.markdown("<div class='info-text' style='border-left: 4px solid #f59e0b; padding-left: 15px; margin-top: 20px;'><b>⚠️ Regula obligatorie privind taxarea contractelor part-time (Suprataxarea)</b><br>Dacă ai sau intenționezi să angajezi personal cu fracțiune de normă (2h, 4h sau 6h) în cadrul unui SRL pentru a bifa condiția regimului de microîntreprindere, reține o regulă fiscală de bază:<br><i>Dacă angajatul part-time nu realizează cumulat (din mai multe contracte) venituri cel puțin egale cu un salariu minim brut pe țară, contribuțiile pentru pensie (CAS 25%) și sănătate (CASS 10%) vor fi calculate și plătite la nivelul unui salariu întreg de 4.325 de lei, chiar dacă el lucrează doar 2 ore pe zi.</i><br>Excepții: Această suprataxare nu se aplică dacă angajatul este elev/student, pensionar, persoană cu dizabilități sau dacă are în paralel un alt contract de muncă cu normă întreagă (8 ore).</div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------
# TAB 4: SĂRBĂTORI LEGALE
# ---------------------------------------------------------------------
with tab4:
    st.write("### 🎉 Calendarul Oficial al Sărbătorilor Legale (Zile Libere)")
    
    st.markdown("<div class='info-text'>Guvernul nu a stabilit nicio punte suplimentară (zi liberă recuperabilă) pentru anul 2026. Decizia executivului a fost de a tăia tradiționalele punți acordate bugetarilor (cum ar fi fost ziua de luni, 5 ianuarie 2026, plasată între Anul Nou și Bobotează), impunând prezența normală la lucru.<br><br><b>Notă:</b> Sărbătorile care cad în weekend (Unirea Principatelor - 24 ianuarie, Prima zi de Paște - 12 aprilie, Prima zi de Rusalii - 31 mai, Adormirea Maicii Domnului - 15 august și A doua zi de Crăciun - 26 decembrie) nu influențează numărul de zile lucrătoare.</div><br>", unsafe_allow_html=True)
    
    date_sarbatori = {
        "Sărbătoare Oficială": [
            "Anul Nou", "A doua zi de Anul Nou", "Boboteaza", "Sfântul Ioan Botezătorul", 
            "Unirea Principatelor", "Vinerea Mare", "Prima zi de Paște", "A doua zi de Paște", 
            "Ziua Muncii", "Prima zi de Rusalii", "Ziua Copilului / A doua zi de Rusalii", "Adormirea Maicii Domnului", 
            "Sfântul Andrei", "Ziua Națională", "Crăciunul", "A doua zi de Crăciun"
        ],
        "Data în Calendar": [
            "1 Ianuarie", "2 Ianuarie", "6 Ianuarie", "7 Ianuarie", 
            "24 Ianuarie", "10 Aprilie", "12 Aprilie", "13 Aprilie", 
            "1 Mai", "31 Mai", "1 Iunie", "15 August", 
            "30 Noiembrie", "1 Decembrie", "25 Decembrie", "26 Decembrie"
        ],
        "Ziua din Săptămână": [
            "Joi (Liber)", "Vineri (Liber)", "Marți (Liber)", "Miercuri (Liber)", 
            "Sâmbătă (Weekend)", "Vineri (Liber)", "Duminică (Weekend)", "Luni (Liber)", 
            "Vineri (Liber)", "Duminică (Weekend)", "Luni (Liber - Suprapuse)", "Sâmbătă (Weekend)", 
            "Luni (Liber)", "Marți (Liber)", "Vineri (Liber)", "Sâmbătă (Weekend)"
        ]
    }
    st.table(date_sarbatori)
