import streamlit as st
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials
from PIL import Image
import json
import os
import datetime
import io

# --- 1. CONFIG & STATE ---
st.set_page_config(page_title="Expo AI", page_icon="✨", layout="wide")

# Init State
if 'language' not in st.session_state: st.session_state['language'] = 'uk'
if 'theme' not in st.session_state: st.session_state['theme'] = 'dark'
if 'history' not in st.session_state: st.session_state['history'] = []

# --- 2. MODERN UI SYSTEM (CSS) ---

# Color Palettes
THEMES = {
    "dark": {
        "bg_gradient": "linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%)", # Deep Midnight
        "sidebar_bg": "#020617",
        "card_bg": "rgba(30, 41, 59, 0.7)", # Glassy Dark
        "text_main": "#f8fafc",
        "text_sub": "#94a3b8",
        "accent": "#6366f1", # Indigo 500
        "accent_hover": "#4f46e5",
        "border": "rgba(148, 163, 184, 0.1)",
        "input_bg": "rgba(15, 23, 42, 0.6)",
        "shadow": "0 10px 15px -3px rgba(0, 0, 0, 0.5)"
    },
    "light": {
        "bg_gradient": "linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%)", # Ceramic White
        "sidebar_bg": "#ffffff",
        "card_bg": "rgba(255, 255, 255, 0.8)", # Glassy White
        "text_main": "#0f172a",
        "text_sub": "#64748b",
        "accent": "#4f46e5", # Indigo 600
        "accent_hover": "#4338ca",
        "border": "rgba(148, 163, 184, 0.2)",
        "input_bg": "#ffffff",
        "shadow": "0 10px 25px -5px rgba(0, 0, 0, 0.05)"
    }
}

current_theme = THEMES[st.session_state['theme']]

st.markdown(f"""
    <style>
        /* IMPORT FONTS */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        /* RESET & BASE */
        .stApp {{
            background: {current_theme['bg_gradient']};
            background-attachment: fixed;
            font-family: 'Inter', -apple-system, sans-serif;
            color: {current_theme['text_main']};
        }}

        /* HIDE STREAMLIT CHROME */
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        header {{visibility: hidden;}}
        
        /* LAYOUT OPTIMIZATION */
        .block-container {{
            padding-top: 2rem;
            padding-bottom: 5rem;
            max-width: 900px; /* Optimal readability width */
            margin: 0 auto;
        }}

        /* TYPOGRAPHY */
        h1, h2, h3 {{
            color: {current_theme['text_main']} !important;
            font-weight: 700 !important;
            letter-spacing: -0.02em;
        }}
        p, label, .stMarkdown {{
            color: {current_theme['text_sub']} !important;
            font-size: 1rem;
            line-height: 1.6;
        }}

        /* INPUT FIELDS - AWARD WINNING STYLE */
        .stTextInput > div > div > input, 
        .stTextArea > div > div > textarea {{
            background-color: {current_theme['input_bg']};
            color: {current_theme['text_main']};
            border: 1px solid {current_theme['border']};
            border-radius: 12px;
            padding: 12px 16px;
            font-size: 16px; /* Prevents zoom on iOS */
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: 0 2px 5px rgba(0,0,0,0.02);
        }}
        .stTextInput > div > div > input:focus,
        .stTextArea > div > div > textarea:focus {{
            border-color: {current_theme['accent']};
            box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2);
            outline: none;
        }}

        /* BUTTONS - HIGH PERFORMANCE LOOK */
        .stButton > button {{
            background: {current_theme['accent']};
            color: white !important;
            border: none;
            border-radius: 12px;
            padding: 14px 28px;
            font-weight: 600;
            letter-spacing: 0.02em;
            width: 100%;
            transition: all 0.2s ease;
            box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3);
        }}
        .stButton > button:hover {{
            background: {current_theme['accent_hover']};
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(79, 70, 229, 0.4);
        }}
        .stButton > button:disabled {{
            opacity: 0.6;
            transform: none;
            box-shadow: none;
        }}

        /* CARDS (EXPANDERS) - GLASSMORPHISM */
        .streamlit-expanderHeader {{
            background-color: {current_theme['card_bg']};
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid {current_theme['border']};
            border-radius: 12px;
            color: {current_theme['text_main']};
            font-weight: 500;
        }}
        .streamlit-expanderContent {{
            background-color: transparent;
            border: 1px solid {current_theme['border']};
            border-top: none;
            border-bottom-left-radius: 12px;
            border-bottom-right-radius: 12px;
            color: {current_theme['text_sub']};
            padding: 16px;
        }}

        /* TABS - SEGMENTED CONTROL STYLE */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 8px;
            background-color: {current_theme['input_bg']};
            padding: 4px;
            border-radius: 16px;
            border: 1px solid {current_theme['border']};
        }}
        .stTabs [data-baseweb="tab"] {{
            height: 40px;
            border-radius: 12px;
            background-color: transparent;
            color: {current_theme['text_sub']};
            border: none;
            font-weight: 500;
            flex: 1; /* Stretch tabs */
        }}
        .stTabs [aria-selected="true"] {{
            background-color: {current_theme['card_bg']};
            color: {current_theme['accent']};
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }}
        
        /* SIDEBAR STYLING */
        [data-testid="stSidebar"] {{
            background-color: {current_theme['sidebar_bg']};
            border-right: 1px solid {current_theme['border']};
        }}
        
        /* CUSTOM ALERTS (TOASTS) */
        .stToast {{
            background-color: {current_theme['card_bg']};
            color: {current_theme['text_main']};
            border-radius: 12px;
            border: 1px solid {current_theme['border']};
        }}

        /* MOBILE OPTIMIZATIONS */
        @media (max-width: 640px) {{
            .block-container {{
                padding-left: 1rem;
                padding-right: 1rem;
            }}
            h1 {{ font-size: 1.8rem !important; }}
            .stButton > button {{ padding: 12px 20px; }}
        }}
    </style>
""", unsafe_allow_html=True)

# --- 3. LOCALIZATION DICTIONARY ---
translations = {
    'uk': {
        'hero_title': "Expo AI",
        'hero_subtitle': "Інтелектуальна обробка лідів у реальному часі.",
        'settings': "Налаштування",
        'api_label': "Gemini API Key",
        'api_help': "Ваш ключ для доступу до AI",
        'theme': "Тема інтерфейсу",
        'lang': "Мова інтерфейсу",
        'dark': "Темна (Midnight)",
        'light': "Світла (Ceramic)",
        'input_ph': "Введіть назву компанії...",
        'tab_photo': "📸 Сканер",
        'tab_upload': "📂 Завантаження",
        'tab_cam': "Камера",
        'label_voice': "🎙 Голосові нотатки",
        'btn_process': "Аналізувати та Зберегти",
        'history': "Історія лідів",
        'empty': "Поки що записів немає",
        'login_req': "Авторизація",
        'login_msg': "Введіть API ключ у бічній панелі для доступу.",
        'success': "Успішно збережено!",
        'err_server': "Помилка з'єднання з Google Sheets"
    },
    'en': {
        'hero_title': "Expo AI",
        'hero_subtitle': "Intelligent real-time lead capture.",
        'settings': "Settings",
        'api_label': "Gemini API Key",
        'api_help': "Your access key for AI",
        'theme': "Appearance",
        'lang': "Language",
        'dark': "Dark (Midnight)",
        'light': "Light (Ceramic)",
        'input_ph': "Enter company name...",
        'tab_photo': "📸 Scanner",
        'tab_upload': "📂 Upload",
        'tab_cam': "Camera",
        'label_voice': "🎙 Voice Notes",
        'btn_process': "Analyze & Save",
        'history': "Lead History",
        'empty': "No records yet",
        'login_req': "Authentication",
        'login_msg': "Enter API Key in sidebar to continue.",
        'success': "Successfully saved!",
        'err_server': "Google Sheets connection error"
    },
    'de': {
        'hero_title': "Expo AI",
        'hero_subtitle': "Intelligente Lead-Erfassung in Echtzeit.",
        'settings': "Einstellungen",
        'api_label': "Gemini API Key",
        'api_help': "Ihr Zugangsschlüssel für KI",
        'theme': "Erscheinungsbild",
        'lang': "Sprache",
        'dark': "Dunkel (Midnight)",
        'light': "Hell (Ceramic)",
        'input_ph': "Firmenname eingeben...",
        'tab_photo': "📸 Scanner",
        'tab_upload': "📂 Datei",
        'tab_cam': "Kamera",
        'label_voice': "🎙 Sprachnotizen",
        'btn_process': "Analysieren & Speichern",
        'history': "Verlauf",
        'empty': "Noch keine Einträge",
        'login_req': "Authentifizierung",
        'login_msg': "Geben Sie den API-Schlüssel ein.",
        'success': "Erfolgreich gespeichert!",
        'err_server': "Verbindungsfehler zu Google Sheets"
    }
}

def t(key): return translations[st.session_state['language']][key]

# --- 4. LOGIC & API ---
@st.cache_resource
def get_sheets():
    try:
        creds_str = os.environ.get("GOOGLE_CREDENTIALS") or st.secrets.get("GOOGLE_CREDENTIALS")
        if not creds_str: return None
        creds = Credentials.from_service_account_info(json.loads(creds_str), scopes=["https://www.googleapis.com/auth/spreadsheets"])
        return gspread.authorize(creds)
    except: return None

def load_history_data():
    client = get_sheets()
    if not client: return []
    try: return list(reversed(client.open("Sales Leads").sheet1.get_all_records()))
    except: return []

def push_data(data):
    client = get_sheets()
    if not client: return False
    try:
        sh = client.open("Sales Leads")
        # Main Sheet
        ws = sh.sheet1
        if ws.row_count > 0 and (not ws.row_values(1) or ws.row_values(1)[0] != "Company"):
            ws.clear(); ws.append_row(list(data.keys()))
        elif ws.row_count == 0: ws.append_row(list(data.keys()))
        ws.append_row(list(data.values()))
        
        # Backup
        try: bu = sh.worksheet("Backup_Logs")
        except: bu = sh.add_worksheet("Backup_Logs", 1000, 20); bu.append_row(list(data.keys()))
        bu.append_row(list(data.values()))
        return True
    except: return False

def analyze_lead(key, img, aud, txt):
    genai.configure(api_key=key)
    model = genai.GenerativeModel("gemini-2.5-pro")
    
    prompt = """
    Extract sales lead data. JSON only.
    Fields: company_name, contact_person, position, email, phone, summary, sentiment, next_steps.
    Language: Match User Interface Language (UA/EN/DE).
    """
    content = [prompt]
    if txt: content.append(f"Context: {txt}")
    if img: content.append(Image.open(io.BytesIO(img)))
    if aud: content.append({"mime_type": "audio/wav", "data": aud.read()})
    
    res = model.generate_content(content, generation_config={"response_mime_type": "application/json"})
    return json.loads(res.text)

# --- 5. UI COMPONENTS ---

# Sidebar
with st.sidebar:
    st.markdown(f"### ⚙️ {t('settings')}")
    
    api_key = st.text_input(t('api_label'), type="password", help=t('api_help'))
    st.markdown("---")
    
    # Lang Selector
    langs = {'UA': 'uk', 'EN': 'en', 'DE': 'de'}
    l_sel = st.pills(t('lang'), list(langs.keys()), default="UA" if st.session_state['language']=='uk' else ("DE" if st.session_state['language']=='de' else "EN"))
    if l_sel and st.session_state['language'] != langs[l_sel]:
        st.session_state['language'] = langs[l_sel]; st.rerun()

    # Theme Toggle
    theme_ui = st.radio(t('theme'), [t('dark'), t('light')], index=0 if st.session_state['theme']=='dark' else 1)
    new_theme = 'dark' if theme_ui == t('dark') else 'light'
    if st.session_state['theme'] != new_theme:
        st.session_state['theme'] = new_theme; st.rerun()

# Main Header
st.markdown(f"""
    <div style="text-align: center; margin-bottom: 40px;">
        <h1 style="font-size: 3rem; margin-bottom: 10px; background: linear-gradient(90deg, {current_theme['accent']}, #a855f7); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">{t('hero_title')}</h1>
        <p style="font-size: 1.2rem; opacity: 0.8;">{t('hero_subtitle')}</p>
    </div>
""", unsafe_allow_html=True)

if not get_sheets():
    st.error(t('err_server')); st.stop()

# Auth Gate
if not api_key:
    st.info(f"{t('login_req')}: {t('login_msg')}")
    if 'history' not in st.session_state: st.session_state['history'] = load_history_data()
else:
    if not st.session_state['history']: st.session_state['history'] = load_history_data()

# Input Container
disabled = not api_key

# Responsive Grid
col1, col2 = st.columns([1.2, 1], gap="large")

with col1:
    company = st.text_input("Company", placeholder=t('input_ph'), label_visibility="collapsed", disabled=disabled)
    st.markdown("<div style='height: 12px'></div>", unsafe_allow_html=True)
    
    # Custom Tabs styling is applied via CSS
    t1, t2 = st.tabs([t('tab_photo'), t('tab_upload')])
    img_bytes = None
    
    with t1:
        c_file = st.camera_input("Cam", label_visibility="collapsed", disabled=disabled)
        if c_file: img_bytes = c_file.getvalue()
    with t2:
        u_file = st.file_uploader("Up", type=['jpg','png'], label_visibility="collapsed", disabled=disabled)
        if u_file: img_bytes = u_file.getvalue()

with col2:
    st.markdown(f"**{t('label_voice')}**")
    audio = st.audio_input("Voice", label_visibility="collapsed") # Check streamlit version for disabled param support

st.markdown("<div style='margin-top: 30px;'></div>", unsafe_allow_html=True)

if st.button(t('btn_process'), type="primary", disabled=disabled):
    if not any([company, img_bytes, audio]):
        st.toast("⚠️ Input required", icon="⚡")
    else:
        with st.spinner("✨ AI Processing..."):
            try:
                res = analyze_lead(api_key, img_bytes, audio, company)
                final_comp = res.get("company_name") or company or "Unknown"
                
                row = {
                    "Company": final_comp,
                    "Contact": res.get("contact_person", ""),
                    "Position": res.get("position", ""),
                    "Email": res.get("email", ""),
                    "Phone": res.get("phone", ""),
                    "Sentiment": res.get("sentiment", ""),
                    "Summary": res.get("summary", ""),
                    "Next Steps": res.get("next_steps", ""),
                    "Timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                }
                
                if push_data(row):
                    st.balloons()
                    st.toast(t('success'), icon="✅")
                    st.session_state['history'] = load_history_data()
            except Exception as e:
                st.error(f"Error: {e}")

# History Feed
st.markdown(f"### {t('history')}")
st.markdown("---")

hist = st.session_state.get('history', [])
if hist:
    for item in hist[:8]:
        with st.expander(f"🏢 {item.get('Company', 'No Name')}  •  {item.get('Timestamp', '')}"):
            st.markdown(f"""
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                    <div><b>👤 Contact:</b> {item.get('Contact')}</div>
                    <div><b>💼 Position:</b> {item.get('Position')}</div>
                    <div><b>📞 Phone:</b> {item.get('Phone')}</div>
                    <div><b>📧 Email:</b> {item.get('Email')}</div>
                </div>
                <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid {current_theme['border']};">
                    <i>"{item.get('Summary')}"</i>
                </div>
                <div style="margin-top: 5px; color: {current_theme['accent']}; font-weight: 600;">
                    👉 {item.get('Next Steps')}
                </div>
            """, unsafe_allow_html=True)
else:
    st.markdown(f"<p style='text-align:center; opacity:0.5;'>{t('empty')}</p>", unsafe_allow_html=True)