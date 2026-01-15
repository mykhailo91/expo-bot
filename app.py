import streamlit as st
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials
from PIL import Image
import json
import os
import datetime
import io

# --- 1. НАЛАШТУВАННЯ ---
st.set_page_config(page_title="Expo AI", page_icon="🚀", layout="centered")

# Ініціалізація стану
if 'language' not in st.session_state:
    st.session_state['language'] = 'uk'
if 'theme' not in st.session_state:
    st.session_state['theme'] = 'dark'

# --- 2. ЛОКАЛІЗАЦІЯ (UA / EN / DE) ---
translations = {
    'uk': {
        'title': "Expo AI Асистент",
        'subtitle': "Capture. Process. Sync.",
        'setup_title': "Налаштування",
        'label_gemini': "Gemini API Key",
        'setup_warning': "Ключ діє лише цю сесію.",
        'theme_label': "Тема оформлення",
        'theme_dark': "Темна 🌑",
        'theme_light': "Світла ☀️",
        'input_company_placeholder': "Назва компанії (опціонально)",
        'photo_tab': "📸 Фото",
        'upload_tab': "📂 Файл",
        'audio_label': "🎤 Голосовий контекст",
        'btn_submit': "Обробити ліда",
        'processing': "Аналіз даних...",
        'success': "✅ Збережено в таблицю",
        'history_header': "Останні записи",
        'no_history': "Історія пуста.",
        'auth_req': "🔒 Потрібна авторизація",
        'auth_desc': "Введіть API Key у меню зліва для початку роботи.",
        'server_error': "❌ Помилка сервера: Немає доступу до Google Sheets."
    },
    'en': {
        'title': "Expo AI Assistant",
        'subtitle': "Capture. Process. Sync.",
        'setup_title': "Settings",
        'label_gemini': "Gemini API Key",
        'setup_warning': "Key is valid for this session only.",
        'theme_label': "Appearance",
        'theme_dark': "Dark 🌑",
        'theme_light': "Light ☀️",
        'input_company_placeholder': "Company Name (Optional)",
        'photo_tab': "📸 Photo",
        'upload_tab': "📂 File",
        'audio_label': "🎤 Voice Context",
        'btn_submit': "Process Lead",
        'processing': "Analyzing...",
        'success': "✅ Saved to Sheet",
        'history_header': "Recent Leads",
        'no_history': "History is empty.",
        'auth_req': "🔒 Authentication Required",
        'auth_desc': "Enter your API Key in the sidebar to start.",
        'server_error': "❌ Server Error: No Google Sheets access."
    },
    'de': {
        'title': "Expo AI Assistent",
        'subtitle': "Capture. Process. Sync.",
        'setup_title': "Einstellungen",
        'label_gemini': "Gemini API Key",
        'setup_warning': "Schlüssel gilt nur für diese Sitzung.",
        'theme_label': "Erscheinungsbild",
        'theme_dark': "Dunkel 🌑",
        'theme_light': "Hell ☀️",
        'input_company_placeholder': "Firmenname (Optional)",
        'photo_tab': "📸 Foto",
        'upload_tab': "📂 Datei",
        'audio_label': "🎤 Sprachkontext",
        'btn_submit': "Lead verarbeiten",
        'processing': "Verarbeitung...",
        'success': "✅ In Tabelle gespeichert",
        'history_header': "Letzte Einträge",
        'no_history': "Verlauf ist leer.",
        'auth_req': "🔒 Authentifizierung erforderlich",
        'auth_desc': "Geben Sie Ihren API-Schlüssel links ein.",
        'server_error': "❌ Serverfehler: Kein Zugriff auf Google Sheets."
    }
}

def t(key):
    return translations[st.session_state['language']][key]

# --- 3. СТИЛІ (Стабільні) ---
# Використовуємо змінні для кольорів, але без ламання верстки
if st.session_state['theme'] == 'dark':
    bg_color = "#0e1117"
    text_color = "#fafafa"
    card_bg = "#262730"
else:
    bg_color = "#ffffff"
    text_color = "#31333F"
    card_bg = "#f0f2f6"

st.markdown(f"""
    <style>
        .stApp {{
            background-color: {bg_color};
            color: {text_color};
        }}
        .stTextInput > div > div > input, .stTextArea > div > div > textarea {{
            background-color: {card_bg};
            color: {text_color};
        }}
        .streamlit-expanderHeader {{
            background-color: {card_bg};
            color: {text_color};
        }}
        .streamlit-expanderContent {{
            background-color: {card_bg};
            color: {text_color};
            opacity: 0.8;
        }}
        h1, h2, h3, p {{
            color: {text_color} !important;
        }}
    </style>
""", unsafe_allow_html=True)

# --- 4. ФУНКЦІОНАЛ ---

@st.cache_resource
def get_google_sheet_client():
    try:
        creds_json_str = os.environ.get("GOOGLE_CREDENTIALS")
        if not creds_json_str and "GOOGLE_CREDENTIALS" in st.secrets:
             creds_json_str = st.secrets["GOOGLE_CREDENTIALS"]
        
        if not creds_json_str: return None

        creds_dict = json.loads(creds_json_str)
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        return client
    except Exception:
        return None

def load_history():
    client = get_google_sheet_client()
    if not client: return []
    try:
        sheet = client.open("Sales Leads").sheet1
        records = sheet.get_all_records()
        return list(reversed(records))
    except Exception:
        return []

def save_to_sheets(row_data):
    client = get_google_sheet_client()
    if not client: return False

    try:
        spreadsheet = client.open("Sales Leads")
        
        # 1. Основний лист
        main_sheet = spreadsheet.sheet1
        expected_headers = list(row_data.keys())
        
        if main_sheet.row_count > 0:
            existing_headers = main_sheet.row_values(1)
            if not existing_headers or existing_headers[0] != "Company":
                 main_sheet.clear()
                 main_sheet.append_row(expected_headers)
        else:
            main_sheet.append_row(expected_headers)
            
        main_sheet.append_row(list(row_data.values()))
        
        # 2. Бекап
        try:
            backup_sheet = spreadsheet.worksheet("Backup_Logs")
        except gspread.exceptions.WorksheetNotFound:
            backup_sheet = spreadsheet.add_worksheet(title="Backup_Logs", rows="1000", cols="20")
            backup_sheet.append_row(expected_headers)
            
        backup_sheet.append_row(list(row_data.values()))
        
        return True
    except Exception as e:
        st.error(f"Save Error: {e}")
        return False

def process_data(user_api_key, image_bytes, audio_file, user_text):
    genai.configure(api_key=user_api_key)
    try:
        model = genai.GenerativeModel("gemini-2.5-pro")
    except:
        model = genai.GenerativeModel("gemini-2.5-pro")

    system_instruction = """
    You are an AI Sales Assistant.
    TASK: Extract structured data.
    OUTPUT LANGUAGE: Match User Interface Language (UA/EN/DE).
    RETURN JSON ONLY:
    {
        "company_name": "string",
        "contact_person": "string",
        "position": "string",
        "email": "string",
        "phone": "string",
        "summary": "string",
        "sentiment": "string",
        "next_steps": "string"
    }
    """
    
    content = [system_instruction]
    if user_text: content.append(f"User Note / Company Name: {user_text}")
    if image_bytes: content.append(Image.open(io.BytesIO(image_bytes)))
    if audio_file: content.append({"mime_type": "audio/wav", "data": audio_file.read()})

    response = model.generate_content(content, generation_config={"response_mime_type": "application/json"})
    return json.loads(response.text)

# --- 5. ІНТЕРФЕЙС ---

# --- SIDEBAR (ГАРАНТОВАНО ПРАЦЮЄ) ---
with st.sidebar:
    st.header(t('setup_title'))
    
    # 1. API Key
    user_gemini_key = st.text_input(t('label_gemini'), type="password")
    st.caption(t('setup_warning'))
    
    st.divider()
    
    # 2. Language Selection
    lang_map = {'UA': 'uk', 'EN': 'en', 'DE': 'de'}
    curr = st.session_state['language']
    idx = 0
    if curr == 'en': idx = 1
    elif curr == 'de': idx = 2
    
    lang_sel = st.radio("Language", ['UA', 'EN', 'DE'], index=idx, horizontal=True)
    
    selected_lang_code = lang_map[lang_sel]
    if st.session_state['language'] != selected_lang_code:
        st.session_state['language'] = selected_lang_code
        st.rerun()
    
    st.divider()

    # 3. Theme Toggle
    theme_sel = st.radio(
        t('theme_label'), 
        [t('theme_dark'), t('theme_light')],
        index=0 if st.session_state['theme'] == 'dark' else 1
    )
    new_theme = 'dark' if theme_sel == t('theme_dark') else 'light'
    if st.session_state['theme'] != new_theme:
        st.session_state['theme'] = new_theme
        st.rerun()

# --- MAIN CONTENT ---

# Header
st.title(t('title'))
st.caption(t('subtitle'))

# Server Check
if not get_google_sheet_client():
    st.error(t('server_error'))
    st.stop()

# Auth Check
disabled_state = not user_gemini_key

if disabled_state:
    st.warning(f"{t('auth_req')}: {t('auth_desc')}")
    if 'history' not in st.session_state:
        st.session_state['history'] = load_history()
else:
    if 'history' not in st.session_state:
        st.session_state['history'] = load_history()

st.divider()

# Inputs
col1, col2 = st.columns([1, 1])

with col1:
    company_text = st.text_input(t('input_company_placeholder'), disabled=disabled_state)
    
    st.write("")
    
    tab_cam, tab_up = st.tabs([t('photo_tab'), t('upload_tab')])
    final_image_bytes = None
    
    with tab_cam:
        cam_file = st.camera_input("Camera", label_visibility="collapsed", disabled=disabled_state)
        if cam_file: final_image_bytes = cam_file.getvalue()
        
    with tab_up:
        up_file = st.file_uploader("Upload", type=['jpg', 'png', 'jpeg'], label_visibility="collapsed", disabled=disabled_state)
        if up_file: final_image_bytes = up_file.getvalue()

with col2:
    st.write(f"**{t('audio_label')}**")
    audio_val = st.audio_input("Audio", label_visibility="collapsed")

st.write("")
st.write("")

# Submit
if st.button(t('btn_submit'), type="primary", use_container_width=True, disabled=disabled_state):
    if not any([company_text, final_image_bytes, audio_val]):
        st.warning("⚠️ No data to send!")
    else:
        with st.spinner(t('processing')):
            try:
                # 1. AI Processing
                result = process_data(user_gemini_key, final_image_bytes, audio_val, company_text)
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                ai_company = result.get("company_name", "").strip()
                final_company_name = company_text if company_text else (ai_company if ai_company else "No Name")
                
                row_data = {
                    "Company": final_company_name,
                    "Contact": result.get("contact_person", ""),
                    "Position": result.get("position", ""),
                    "Email": result.get("email", ""),
                    "Phone": result.get("phone", ""),
                    "Sentiment": result.get("sentiment", ""),
                    "Summary": result.get("summary", ""),
                    "Next Steps": result.get("next_steps", ""),
                    "Timestamp": timestamp
                }

                # 2. Save
                if save_to_sheets(row_data):
                    st.success(t('success'))
                    st.session_state['history'] = load_history()
                
            except Exception as e:
                st.error(f"Error: {e}")

# History
st.divider()
st.subheader(t('history_header'))

if st.session_state.get('history'):
    for item in st.session_state['history'][:10]:
        comp = item.get('Company') or "No Name"
        time = item.get('Timestamp') or ""
        
        with st.expander(f"🏢 {comp} • {time}"):
            st.write(f"**👤 Contact:** {item.get('Contact')} ({item.get('Position')})")
            st.write(f"**📞 Info:** {item.get('Phone')} | 📧 {item.get('Email')}")
            st.info(f"📝 {item.get('Summary')}")
            st.caption(f"👉 Next: {item.get('Next Steps')}")
else:
    st.info(t('no_history'))