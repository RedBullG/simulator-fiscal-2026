import streamlit as st
import requests
import xml.etree.ElementTree as ET
from supabase import create_client, Client

# =====================================================================
# DESIGN PREMIUM & CONFIGURARE VIZUALĂ
# =====================================================================
st.set_page_config(layout="wide", page_title="Hub Fiscal", page_icon="🇷🇴")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        font-family: 'Inter', sans-serif;
        background-color: #0d1117 !important;
    }
    
    .main-title {
        font-size: 36px !important;
        font-weight: 800 !important;
        background: linear-gradient(90deg, #3b82f6, #10b981);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 5px !important;
        text-align: center;
    }
    
    .subtitle {
        color: #8b949e !important;
        font-size: 15px !important;
        margin-bottom: 25px !important;
        text-align: center;
    }

    .curs-container {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 15px 20px;
        margin-bottom: 25px;
    }

    .fiscal-card {
        background: linear-gradient(145deg, #161b22, #0d1117);
        border: 1px solid #30363d;
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 15px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.2);
        transition: all 0.3s ease;
    }
    .fiscal-card:hover {
        border-color: #38bdf8;
        transform: translateY(-2px);
    }
    
    .card-badge {
        display: inline-block;
        padding: 4px 10px;
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        border-radius: 20px;
        margin-bottom: 12px;
    }
    .badge-cim { background-color: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3); }
    .badge-pfa { background-color: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }
    .badge-srl { background-color: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }

    .card-title {
        font-size: 20px !important;
        font-weight: 700 !important;
        color: #f0f6fc !important;
        margin-bottom: 15px !important;
        text-align: center;
    }
    
    .card-value-container {
        background: rgba(255,255,255,0.02);
        border-radius: 12px;
        padding: 12px;
        margin-bottom: 20px;
        border: 1px solid rgba(255,255,255,0.05);
        text-align: center;
    }
    .card-value-label {
        font-size: 11px;
        color: #8b949e;
        text-transform: uppercase;
    }
    .card-net-value {
        font-size: 32px !important;
        font-weight: 800 !important;
        color: #10b981 !important;
    }
    
    .tax-breakdown-title {
        font-size: 13px;
        font-weight: 600;
        color: #8b949e;
        margin-bottom: 10px;
        text-transform: uppercase;
        text-align: center;
    }
    .tax-item {
        display: flex;
        justify-content: space-between;
        padding: 8px 0;
        border-bottom: 1px solid #21262d;
        font-size: 14px;
    }
    .tax-name { color: #c9d1d9; }
    .tax-val-bold { font-weight: 600; color: #f43f5e; }
    .tax-val-info { font-weight: 600; color: #38bdf8; }

    table { margin-left: auto !important; margin-right: auto !important; width: 100% !important; }
    th { text-align: center !important; background-color: #1f2937 !important; color: #f0f6fc !important; }
    td { text-align: center !important; color: #c9d1d9 !important; vertical-align: middle !important; }
    .stTable { background-color: #161b22 !important; border: 1px solid #30363d !important; border-radius: 8px !important; }
    
    .info-text { color: #c9d1d9; font-size: 14px; line-height: 1.6; margin-bottom: 15px; }
</style>
""", unsafe_allow_html=True)

# =====================================================================
# 💱 PRELUARE CURS VALUTAR LIVE BNR
# =====================================================================
@st.cache_data(ttl=3600)
def obtine_curs_bnr_live():
    try:
        url = "https://www.bnr.ro/nbrfxrates.xml"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        namespace = {'bnr': 'http://www.bnr.ro/xsd'}
        rata_eur = root.find(".//bnr:Rate[@currency='EUR']", namespace)
        if rata_eur is not None:
            return float(rata_eur.text)
    except Exception:
        pass
    return 4.98

CURS_BNR_LIVE = obtine_curs_bnr_live()

# =====================================================================
# 🔒 CONEXIUNE SUPABASE SECURE
# =====================================================================
@st.cache_data(ttl=600)
def incarca_config_din_supabase():
    config_fallback = {
        "salariu_minim_brut_iulie": 4325, "salariu_minim_anual_ponderat": 50250, "plafon_micro_eur": 100000,
        "taxe_angajat": {"cas_procent": 0.25, "cass_procent": 0.10, "impozit_procent": 0.10},
        "taxe_angajator": {"cam_procent": 0.0225},
        "pfa": {"impozit_procent": 0.10, "cas_procent": 0.25, "cass_procent": 0.10},
        "srl": {"impozit_venit_micro": 0.01, "impozit_profit_standard": 0.16, "impozit_dividende_nou": 0.16, "cass_dividende_procent": 0.10}
    }
    
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        supabase: Client = create_client(url, key)
        response = supabase.table("configurare_fiscala").select("cheie, valoare").execute()
        date_db = {rand["cheie"]: float(rand["valoare"]) for rand in response.data}
        return {
            "salariu_minim_brut_iulie": date_db["salariu_minim_brut_iulie"],
            "salariu_minim_anual_ponderat": date_db["salariu_minim_anual_ponderat"],
            "plafon_micro_eur": date_db["plafon_micro_eur"],
            "taxe_angajat": {"cas_procent": date_db["cas_procent"], "cass_procent": date_db["cass_procent"], "impozit_procent": date_db["impozit_procent"]},
            "taxe_angajator": {"cam_procent": date_db["cam_procent"]},
            "pfa": {"impozit_procent": date_db["impozit_procent"], "cas_procent": date_db["cas_procent"], "cass_procent": date_db["cass_procent"]},
            "srl": {"impozit_venit_micro": date_db["impozit_venit_micro"], "impozit_profit_standard": date_db["impozit_profit_standard"], "impozit_dividende_nou": date_db["impozit_dividende_nou"], "cass_dividende_procent": date_db["cass_procent"]}
        }
    except Exception:
        return config_fallback

config_fiscal = incarca_config_din_supabase()

# =====================================================================
# ENGINES DE CALCUL FISCAL
# =====================================================================
def calculeaza_brut_la_net_dinamic(brut, are_tichete, valoare_tichet, zile_lucrate, config=config_fiscal):
    valoare_tichete_luna = (valoare_tichet * zile_lucrate) if are_tichete else 0.0
    cas = brut * config["taxe_angajat"]["cas_procent"]
    cass = (brut + valoare_tichete_luna) * config["taxe_angajat"]["cass_procent"]
    baza_impozit = (brut + valoare_tichete_luna) - cas - cass
    impozit = max(0, baza_impozit * config["taxe_angajat"]["impozit_procent"])
    net_cash = brut - cas - cass - impozit - valoare_tichete_luna
    return {
        "valoare_tichete": valoare_tichete_luna, "cas": cas, "cass": cass, "impozit": impozit,
        "net_cash": net_cash, "total_net": net_cash + valoare_tichete_luna,
        "cost_firma": brut + (brut * config["taxe_angajator"]["cam_procent"]) + valoare_tichete_luna
    }

def calculeaza_net_la_brut_dinamic(net_tinta, are_tichete, valoare_tichet, zile_lucrate, config=config_fiscal):
    brut_estimat = net_tinta
    pas = 2000.0
    while pas > 0.001:
        rezultat_test = calculeaza_brut_la_net_dinamic(brut_estimat, are_tichete, valoare_tichet, zile_lucrate, config)
        if rezultat_test["net_cash"] < net_tinta: brut_estimat += pas
        else: brut_estimat -= pas; pas /= 2.0
    return round(brut_estimat, 2)

def calculeaza_cim(brut, config=config_fiscal):
    cas = brut * config["taxe_angajat"]["cas_procent"]
    cass = brut * config["taxe_angajat"]["cass_procent"]
    impozit = max(0, (brut - cas - cass) * config["taxe_angajat"]["impozit_procent"])
    net_lunar = brut - cas - cass - impozit
    cost_total_firma = brut + (brut * config["taxe_angajator"]["cam_procent"])
    return {"net_lunar": net_lunar, "total_net": net_lunar, "taxe_lunare": cost_total_firma - net_lunar, "cas": cas, "cass": cass, "impozit": impozit}

def calculeaza_pfa_nou(venit_brut_anual, config=config_fiscal):
    salariu_minim_mediu = config["salariu_minim_anual_ponderat"] / 12
    baza_cas = 24 * salariu_minim_mediu if venit_brut_anual >= 24 * salariu_minim_mediu else (12 * salariu_minim_mediu if venit_brut_anual >= 12 * salariu_minim_mediu else 0)
    cas = baza_cas * config["pfa"]["cas_procent"]
    cass_brut = venit_brut_anual * config["pfa"]["cass_procent"]
    p_min = 6 * salariu_minim_mediu * config["pfa"]["cass_procent"]
    p_max = 72 * salariu_minim_mediu * config["pfa"]["cass_procent"]
    cass = p_min if cass_brut < p_min else (p_max if cass_brut > p_max else cass_brut)
    impozit = max(0, venit_brut_anual - cas - cass) * config["pfa"]["impozit_procent"]
    return {"net_lunar": (venit_brut_anual - cas - cass - impozit) / 12, "taxe_lunare": (cas + cass + impozit) / 12, "cas_lunar": cas / 12, "cass_lunar": cass / 12, "impozit_lunar": impozit / 12}

def calculeaza_srl_nou(venit_brut_anual, curs_valutar, config=config_fiscal):
    s_brut_anual = config["salariu_minim_brut_iulie"] * 12
    cost_total_ang_anual = s_brut_anual + (s_brut_anual * config["taxe_angajator"]["cam_procent"])
    net_sal_anual = s_brut_anual - (s_brut_anual * config["taxe_angajat"]["cas_procent"]) - (s_brut_anual * config["taxe_angajat"]["cass_procent"]) - ((s_brut_anual - (s_brut_anual * config["taxe_angajat"]["cas_procent"]) - (s_brut_anual * config["taxe_angajat"]["cass_procent"])) * config["taxe_angajat"]["impozit_procent"])
    
    plafon_micro_ron = config["plafon_micro_eur"] * curs_valutar
    if venit_brut_anual <= plafon_micro_ron:
        impozit_firma = venit_brut_anual * config["srl"]["impozit_venit_micro"]
        regim, label = "Microîntreprindere (1%)", "Impozit Venit (1%)"
        profit_net_div = max(0, venit_brut_anual - cost_total_ang_anual - impozit_firma)
    else:
        impozit_firma = max(0, venit_brut_anual - cost_total_ang_anual) * config["srl"]["impozit_profit_standard"]
        regim, label = "Impozit Profit (16%)", "Impozit Profit (16%)"
        profit_net_div = max(0, venit_brut_anual - cost_total_ang_anual) - impozit_firma
        
    imp_div = profit_net_div * config["srl"]["impozit_dividende_nou"]
    div_ramase = profit_net_div - imp_div
    s_mediu = config["salariu_minim_anual_ponderat"] / 12
    baza_c_div = 24 * s_mediu if div_ramase >= 24 * s_mediu else (12 * s_mediu if div_ramase >= 12 * s_mediu else (6 * s_mediu if div_ramase >= 6 * s_mediu else 0))
    cass_div = baza_c_div * config["srl"]["cass_dividende_procent"]
    
    return {"net_lunar": (net_sal_anual + div_ramase - cass_div) / 12, "taxe_lunare": (venit_brut_anual - (net_sal_anual + div_ramase - cass_div)) / 12, "regim": regim, "impozit_firma_lunar": impozit_firma / 12, "impozit_dividende_lunar": imp_div / 12, "cass_dividende_lunar": cass_div / 12, "net_salariu_angajat_lunar": net_sal_anual / 12, "taxe_angajat_salariu_lunar": (cost_total_ang_anual - net_sal_anual) / 12, "label_impozit_firma": label}

# =====================================================================
# BARA LATERALĂ (SIDEBAR) BUNE PRACTICI
# =====================================================================
with st.sidebar:
    st.header("📘 Bune Practici & Ghid Fiscal")
    
    with st.expander("❓ Dicționar Acronime"):
        st.markdown("""
        * **CAS (25%)**: Contribuția pentru pensie. Merge la bugetul de stat pentru asigurarea vechimii și calculul pensiei viitoare.
        * **CASS (10%)**: Asigurarea medicală. Finanțează sistemul public de sănătate (CNAS), oferind acces la spitalizare și analize.
        * **Impozit pe Venit (10%)**: Taxa generală reținută pe veniturile realizate.
        * **CAM (2.25%)**: Contribuție plătită strict de angajator peste salariul brut, destinată fondului de șomaj și concedii medicale.
        """)
        
    with st.expander("⚠️ Regula Suprataxării Part-Time"):
        st.markdown(f"""
        Dacă folosești contracte part-time (2h, 4h, 6h) în SRL pentru păstrarea regimului de microîntreprindere, reține regula din Codul Fiscal:
        * **Baza minimă**: Dacă venitul cumulat al angajatului este sub salariul minim pe țară, **CAS și CASS se plătesc forțat la nivelul unui salariu întreg de {config_fiscal['salariu_minim_brut_iulie']:.0f} lei**, chiar dacă el lucrează doar 2 ore pe zi.
        * *Excepții*: Elevi, studenți, pensionari sau persoane care au în paralel un alt contract cu normă întreagă (8 ore).
        """)

    with st.expander("💸 1. Managementul Fluxului de Bani"):
        st.markdown("""
        * **Separarea totală a banilor:** Nu folosi cardul firmei pentru cumpărături personale. La SRL, banii sunt ai firmei, nu ai tăi; îi poți scoate legal doar prin salarii sau dividende. La PFA ai acces liber, dar separarea ajută.
        * **Provizionarea taxelor:** Deschide un cont bancar secundar (de economii). La încasarea unei facturi, transferă imediat acolo procentul estimat de taxe (minim 10-15% la PFA și procentul de dividend + micro la SRL). Nu te atinge de acel cont!
        """)

    with st.expander("🌐 2. Documente și Digitalizare (ANAF)"):
        st.markdown("""
        * **Activarea SPV (Spațiul Privat Virtual):** Verifică-l cel puțin o dată pe săptămână. ANAF trimite notificări exclusiv acolo, considerate comunicate legal în termen de 15 zile.
        * **Adoptarea e-Factura:** Asigură-te că facturile emise către alte firme (B2B) sunt transmise în RO e-Factura în termenul legal de 5 zile calendaristice de la emitere. Nerespectarea aduce amenzi mari.
        * **Arhivare cloud:** Scanează bonurile fiscale termice, deoarece cerneala se șterge în timp.
        """)

    with st.expander("🎯 3. Justificarea Cheltuielilor"):
        st.markdown("""
        * **Regula necesității:** O cheltuială este deductibilă doar dacă este efectuată în scopul desfășurării activității economice.
        * **Achiziții suspecte:** Bunurile de lux, vacanțele decontate ca deplasări fără ordin sau cumpărăturile zilnice la supermarket vor fi reîncadrate de inspectori ca nedeductibile, atrăgând penalități.
        * **Foile de parcurs:** Dacă deduci 100% cheltuielile cu mașina firmei, ești obligat prin lege să completezi foi de parcurs detaliate pentru fiecare cursă. Fără ele, poți deduce doar 50%.
        """)

    with st.expander("📆 4. Relația cu Contabilul & Plafoane"):
        st.markdown("""
        * **Contabilul este un partener:** Trimite documentele lunare complete până pe data de 5 ale lunii următoare. Nu trimite documente în ultima zi!
        * **Monitorizarea plafoanelor:** Ține o evidență strictă a veniturilor pentru a nu fi luat prin surprindere de trecerea la TVA (plafon de 300.000 lei) sau de trecerea forțată la impozit pe profit (plafon 100.000 EUR).
        """)
        
    with st.expander("💳 5. Plata Taxelor"):
        st.markdown("""
        * **Respectarea termenului de 25:** Data de 25 a lunii este termenul sfânt pentru depunerea declarațiilor și plata obligațiilor. Întârzierile generează dobânzi.
        * **Fișa pe plătitor:** Cere sau descarcă singur din SPV „Fișa de evidență pe plătitor” pentru a te asigura că plățile s-au stins corect în trezorerie.
        """)

# =====================================================================
# INTERFAȚA WEB PRINCIPALĂ
# =====================================================================
st.markdown("<div class='main-title'>🇷🇴 Hub Fiscal Inteligent</div>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>Simulator avansat de analiză comparativă și modelare a structurilor de venit. (Actualizat 2026)</div>", unsafe_allow_html=True)

st.markdown("<div class='curs-container'>", unsafe_allow_html=True)
col_curs_1, col_curs_2, col_curs_3 = st.columns([1, 2, 1])
with col_curs_2:
    st.write(f"🔄 **Sursă Curs Valutar:** bnr.ro")
    curs_eur = st.number_input("💱 Curs Valutar de Referință (EUR/RON):", min_value=1.0, value=CURS_BNR_LIVE, step=0.01, key="curs_global", disabled=True)
st.markdown("</div>", unsafe_allow_html=True)

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
        moneda = st.radio("Moneda:", ("RON", "EUR"), horizontal=True)
        tip_calcul = st.radio("Suma introdusă este:", ("Brut (Salariul de bază)", "Net (Banii pe card)"), horizontal=True)
        
        st.markdown("---")
        are_tichete = st.checkbox("Include tichete de masă?")
        valoare_tichet, zile_lucrate = 0.0, 0
        if are_tichete:
            c1, c2 = st.columns(2)
            with c1: valoare_tichet = st.number_input("Valoare nominală tichet (RON):", min_value=0.0, value=35.0, step=5.0)
            with c2: zile_lucrate = st.number_input("Zile lucrătoare lucrate efectiv:", min_value=0, max_value=31, value=21)
            
        suma_introdusa = st.number_input(f"Introduceți valoarea ({moneda}):", min_value=0.0, value=5000.0 if moneda == "RON" else 1000.0, step=100.0)
        suma_ron = suma_introdusa * curs_eur if moneda == "EUR" else suma_introdusa
        
        if "Brut" in tip_calcul:
            brut_final_ron = suma_ron
            rezultat = calculeaza_brut_la_net_dinamic(brut_final_ron, are_tichete, valoare_tichet, zile_lucrate)
        else:
            brut_final_ron = calculeaza_net_la_brut_dinamic(suma_ron, are_tichete, valoare_tichet, zile_lucrate)
            rezultat = calculeaza_brut_la_net_dinamic(brut_final_ron, are_tichete, valoare_tichet, zile_lucrate)

    with col_drp:
        st.write("### 📈 Rezultate Extrase")
        net_afisat = rezultat['net_cash'] if moneda == "RON" else rezultat['net_cash'] / curs_eur
        cost_afisat = rezultat['cost_firma'] if moneda == "RON" else rezultat['cost_firma'] / curs_eur
        brut_afisat = brut_final_ron if moneda == "RON" else brut_final_ron / curs_eur
        
        str_brut = f"{brut_afisat:.2f} {moneda}"
        str_cas = f"{(rezultat['cas'] if moneda == 'RON' else rezultat['cas']/curs_eur):.2f} {moneda}"
        str_cass = f"{(rezultat['cass'] if moneda == 'RON' else rezultat['cass']/curs_eur):.2f} {moneda}"
        str_imp = f"{(rezultat['impozit'] if moneda == 'RON' else rezultat['impozit']/curs_eur):.2f} {moneda}"
        str_cost = f"{cost_afisat:.2f} {moneda}"
        
        html_t1 = "<div class='fiscal-card'>"
        html_t1 += "<div style='text-align:center;'><div class='card-badge badge-cim'>Contract Individual de Muncă</div></div>"
        html_t1 += f"<div class='card-value-container'><div class='card-value-label'>Bani pe card (Net Cash)</div><div class='card-net-value'>{net_afisat:.2f} {moneda}</div></div>"
        html_t1 += "<div class='tax-breakdown-title'>Detaliere rețineri și contribuții:</div>"
        html_t1 += f"<div class='tax-item'><span class='tax-name'>Salariu Brut Contractual:</span><span class='tax-val'>{str_brut}</span></div>"
        html_t1 += f"<div class='tax-item'><span class='tax-name'>CAS (Pensie 25%):</span><span class='tax-val-bold'>{str_cas}</span></div>"
        html_t1 += f"<div class='tax-item'><span class='tax-name'>CASS (Sănătate 10%):</span><span class='tax-val-bold'>{str_cass}</span></div>"
        html_t1 += f"<div class='tax-item'><span class='tax-name'>Impozit pe Venit (10%):</span><span class='tax-val-bold'>{str_imp}</span></div>"
        
        if are_tichete:
            t_val = rezultat['valoare_tichete'] if moneda == "RON" else rezultat['valoare_tichete'] / curs_eur
            tot_val = rezultat['total_net'] if moneda == "RON" else rezultat['total_net'] / curs_eur
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
    c_m2, c_s2 = st.columns(2)
    with c_m2: moneda_t2 = st.radio("Valuta bugetului:", ("RON", "EUR"), horizontal=True, key="mon_t2")
    with c_s2: b_introdus = st.number_input(f"Introduceți bugetul lunar total alocat ({moneda_t2}):", min_value=500, value=15000 if moneda_t2 == "RON" else 3000, step=500)
    
    buget_lunar = b_introdus * curs_eur if moneda_t2 == "EUR" else b_introdus
    buget_anual = buget_lunar * 12
    rez_cim, rez_pfa, rez_srl = calculeaza_cim(buget_lunar), calculeaza_pfa_nou(buget_anual), calculeaza_srl_nou(buget_anual, curs_valutar=curs_eur)
    
    st.markdown("---")
    col1, col2, col3 = st.columns(3, gap="medium")
    coef = curs_eur if moneda_t2 == "EUR" else 1.0
    
    with col1:
        h_cim = "<div class='fiscal-card'>"
        h_cim += "<div style='text-align:center;'><div class='card-badge badge-cim'>Opțiunea 1</div></div>"
        h_cim += "<div class='card-title'>👔 Angajat (CIM)</div>"
        h_cim += f"<div class='card-value-container'><div class='card-net-value'>{(rez_cim['net_lunar']/coef):.2f} {moneda_t2}</div></div>"
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
        h_pfa += "<div class='card-title'>💼 PFA (Sistem Real)</div>"
        h_pfa += f"<div class='card-value-container'><div class='card-net-value'>{(rez_pfa['net_lunar']/coef):.2f} {moneda_t2}</div></div>"
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
        h_srl += f"<div class='card-title'>🏢 SRL ({rez_srl['regim']})</div>"
        h_srl += f"<div class='card-value-container'><div class='card-net-value'>{(rez_srl['net_lunar']/coef):.2f} {moneda_t2}</div></div>"
        h_srl += "<div class='tax-breakdown-title'>Impozite agregate detaliat:</div>"
        h_srl += f"<div class='tax-item'><span class='tax-name'>{rez_srl['label_impozit_firma']}:</span><span class='tax-val-bold'>{(rez_srl['impozit_firma_lunar']/coef):.2f} {moneda_t2}</span></div>"
        h_srl += f"<div class='tax-item'><span class='tax-name'>Impozit Dividende (16%):</span><span class='tax-val-bold'>{(rez_srl['impozit_dividende_lunar']/coef):.2f} {moneda_t2}</span></div>"
        h_srl += f"<div class='tax-item'><span class='tax-name'>CASS Dividende (10%):</span><span class='tax-val-bold'>{(rez_srl['cass_dividende_lunar']/coef):.2f} {moneda_t2}</span></div>"
        h_srl += f"<div class='tax-item'><span class='tax-name'>Taxe Salariu Obligatoriu:</span><span class='tax-val-info'>{(rez_srl['taxe_angajat_salariu_lunar']/coef):.2f} {moneda_t2}</span></div>"
        h_srl += f"<div class='tax-item' style='margin-top:10px; border-top: 1px dashed #30363d; padding-top:10px;'><span class='tax-name'>Total Taxe SRL:</span><span class='tax-val-bold'>{(rez_srl['taxe_lunare']/coef):.2f} {moneda_t2}</span></div>"
        h_srl += "</div>"
        st.markdown(h_srl, unsafe_allow_html=True)

# ---------------------------------------------------------------------
# TAB 3: PLANIFICATOR ZILE LUCRĂTOARE 
# ---------------------------------------------------------------------
with tab3:
    st.write("### 📅 Repartizarea orelor de muncă în funcție de contract (2026)")
    
    st.markdown("""
    <div class='info-text'>
    În anul 2026, calendarul din România cuprinde un total de <b>250 de zile lucrătoare</b> (echivalentul a 2.000 de ore de muncă pentru un program normal de 8 ore/zi). 
    Restul anului este format din 105 zile de weekend și 10 zile libere legale care cad în timpul săptămânii (dintr-un total de 17 sărbători oficiale).
    </div>
    """, unsafe_allow_html=True)
    
    date_norme = {
        "Lună": ["Ianuarie", "Februarie", "Martie", "Aprilie", "Mai", "Iunie", "Iulie", "August", "Septembrie", "Octombrie", "Noiembrie", "Decembrie", "TOTAL ANUAL"],
        "Zile Lucrătoare": ["18", "20", "22", "20", "20", "21", "23", "21", "22", "22", "20", "21", "250"],
        "Normă 2h/zi": ["36", "40", "44", "40", "40", "42", "46", "42", "44", "44", "40", "42", "500"],
        "Normă 4h/zi": ["72", "80", "88", "80", "80", "84", "92", "84", "88", "88", "80", "84", "1000"],
        "Normă 6h/zi": ["108", "120", "132", "120", "120", "126", "138", "126", "132", "132", "120", "126", "1500"],
        "Normă 8h/zi": ["144", "160", "176", "160", "160", "168", "184", "168", "176", "176", "160", "168", "2000"]
    }
    st.table(date_norme)

    st.markdown("""
    <div class='info-text' style='border-left: 4px solid #f59e0b; padding-left: 15px; margin-top: 20px;'>
    <b>⚠️ Regula obligatorie privind taxarea contractelor part-time (Suprataxarea)</b><br>
    Dacă ai sau intenționezi să angajezi personal cu fracțiune de normă (2h, 4h sau 6h) în cadrul unui SRL pentru a bifa condiția regimului de microîntreprindere, reține o regulă fiscală de bază:<br>
    <i>Dacă angajatul part-time nu realizează cumulat (din mai multe contracte) venituri cel puțin egale cu un salariu minim brut pe țară, contribuțiile pentru pensie (CAS 25%) și sănătate (CASS 10%) vor fi calculate și plătite la nivelul unui salariu întreg de 4.325 de lei, chiar dacă el lucrează doar 2 ore pe zi.</i><br>
    Excepții: Această suprataxare nu se aplică dacă angajatul este elev/student, pensionar, persoană cu dizabilități sau dacă are în paralel un alt contract de muncă cu normă întreagă (8 ore).
    </div>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------------------
# TAB 4: SĂRBĂTORI LEGALE
# ---------------------------------------------------------------------
with tab4:
    st.write("### 🎉 Calendarul Oficial al Sărbătorilor Legale (Zile Libere)")
    
    st.markdown("""
    <div class='info-text'>
    Guvernul nu a stabilit nicio punte suplimentară (zi liberă recuperabilă) pentru anul 2026. Decizia executivului a fost de a tăia tradiționalele punți acordate bugetarilor (cum ar fi fost ziua de luni, 5 ianuarie 2026, plasată între Anul Nou și Bobotează), impunând prezența normală la lucru.<br><br>
    <b>Notă:</b> Sărbătorile care cad în weekend (Unirea Principatelor - 24 ianuarie, Prima zi de Paște - 12 aprilie, Prima zi de Rusalii - 31 mai, Adormirea Maicii Domnului - 15 august și A doua zi de Crăciun - 26 decembrie) nu influențează numărul de zile lucrătoare.
    </div>
    """, unsafe_allow_html=True)
    
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
