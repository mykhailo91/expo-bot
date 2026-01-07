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

MODEL_NAME = "gemini-1.5-flash"

# Ініціалізація змінних
if 'language' not in st.session_state:
    st.session_state['language'] = 'uk'

# --- 2. СЛОВНИК ПЕРЕКЛАДІВ ---
translations = {
    'uk': {
        'title': "🚀 Expo AI Асистент",
        'lang_label': "Мова",
        'input_company_label': "🏢 Назва компанії",
        'input_company_placeholder': "Введіть назву",
        'photo_method_label': "📸 Фото візитки",
        'method_camera': "Камера",
        'method_upload': "Завантажити файл",
        'cam_label': "Зробіть фото",
        'upload_label': "Виберіть фото",
        'audio_header': "🎤 Голосовий запис",
        'audio_label': "Натисніть мікрофон та говоріть",
        'btn_submit': "📤 Обробити та відправити",
        'warning_nodata': "⚠️ Немає даних для відправки!",
        'processing': "⏳ Обробка...",
        'success': "✅ Успішно! Записано в таблицю.",
        'history_header': "🗂️ Історія записів (з Google Таблиці)",
        'no_history': "Історія пуста або не завантажилась.",
        'loading_history': "🔄 Завантажую історію з таблиці..."
    },
    'en': {
        'title': "🚀 Expo AI Assistant",
        'lang_label': "Language",
        'input_company_label': "🏢 Company Name",
        'input_company_placeholder': "Enter name",
        'photo_method_label': "📸 Business Card Photo",
        'method_camera': "Camera",
        'method_upload': "Upload File",
        'cam_label': "Take a photo",
        'upload_label': "Choose file",
        'audio_header': "🎤 Voice Recording",
        'audio_label': "Press mic and speak",
        'btn_submit': "📤 Process & Send",
        'warning_nodata': "⚠️ No data to send!",
        'processing': "⏳ Processing...",
        'success': "✅ Success! Saved to sheet.",
        'history_header': "🗂️ Record History (from Google Sheet)",
        'no_history': "History is empty or failed to load.",
        'loading_history': "🔄 Loading history from sheet..."
    }
}

def t(key):
    return translations[st.session_state['language']][key]

# --- 3. ФУНКЦІЇ ---

# Кешуємо підключення, щоб не логінитись щоразу
@st.cache_resource
def get_google_sheet_client():
    try:
        creds_json_str = os.environ.get("GOOGLE_CREDENTIALS")
        if not creds_json_str and "GOOGLE_CREDENTIALS" in st.secrets:
             creds_json_str = st.secrets["GOOGLE_CREDENTIALS"]
        
        if not creds_json_str:
            return None

        creds_dict = json.loads(creds_json_str)
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        return None

# Функція завантаження історії (НОВА)
def load_history():
    client = get_google_sheet_client()
    if not client: return []
    
    try:
        sheet = client.open("Sales Leads").sheet1
        # Отримуємо всі записи як список словників
        records = sheet.get_all_records()
        # Розвертаємо, щоб нові були зверху
        return list(reversed(records))
    except Exception:
        return []

def process_data(api_key, image_bytes, audio_file, user_text):
    genai.configure(api_key=api_key)
    try:
        model = genai.GenerativeModel(MODEL_NAME)
    except:
        model = genai.GenerativeModel("gemini-1.5-flash-latest")

    system_instruction = """
    You are an AI Sales Assistant.
    TASK: Extract structured data.
    OUTPUT LANGUAGE: Match User Interface Language (UA/EN).
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
    if user_text: content.append(f"User Note: {user_text}")
    if image_bytes: content.append(Image.open(io.BytesIO(image_bytes)))
    if audio_file: content.append({"mime_type": "audio/wav", "data": audio_file.read()})

    response = model.generate_content(content, generation_config={"response_mime_type": "application/json"})
    return json.loads(response.text)

# --- 4. ІНТЕРФЕЙС ---

# Завантаження історії при старті (якщо ще немає в сесії)
if 'history' not in st.session_state:
    with st.spinner(t('loading_history')):
        st.session_state['history'] = load_history()

col_head1, col_head2 = st.columns([3, 1])
with col_head1: st.title(t('title'))
with col_head2:
    lang = st.radio(t('lang_label'), ['UA', 'EN'], index=0 if st.session_state['language']=='uk' else 1, horizontal=True, label_visibility="collapsed")
    if (lang == 'UA' and st.session_state['language'] != 'uk'): st.session_state['language'] = 'uk'; st.rerun()
    elif (lang == 'EN' and st.session_state['language'] != 'en'): st.session_state['language'] = 'en'; st.rerun()

st.divider()

# Ввід даних
company_text = st.text_input(t('input_company_label'), placeholder=t('input_company_placeholder'))
st.write("")

method = st.radio(t('photo_method_label'), [t('method_upload'), t('method_camera')], horizontal=True)
final_image_bytes = None

if method == t('method_camera'):
    cam_file = st.camera_input(t('cam_label'))
    if cam_file: final_image_bytes = cam_file.getvalue()
else:
    up_file = st.file_uploader(t('upload_label'), type=['jpg', 'png', 'jpeg'])
    if up_file: 
        final_image_bytes = up_file.getvalue()
        st.image(up_file, width=200)

st.write("")
st.subheader(t('audio_header'))
audio_val = st.audio_input(t('audio_label'))
st.divider()

if st.button(t('btn_submit'), type="primary", use_container_width=True):
    if not any([company_text, final_image_bytes, audio_val]):
        st.warning(t('warning_nodata'))
    else:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key and "GEMINI_API_KEY" in st.secrets: api_key = st.secrets["GEMINI_API_KEY"]
        
        if not api_key: st.error("API Key Error"); st.stop()

        with st.spinner(t('processing')):
            try:
                # 1. AI Обробка
                result = process_data(api_key, final_image_bytes, audio_val, company_text)
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Підготовка запису для таблиці
                row_data = {
                    "Timestamp": timestamp,
                    "Company": result.get("company_name", company_text),
                    "Contact": result.get("contact_person", ""),
                    "Position": result.get("position", ""),
                    "Email": result.get("email", ""),
                    "Phone": result.get("phone", ""),
                    "Sentiment": result.get("sentiment", ""),
                    "Summary": result.get("summary", ""),
                    "Next Steps": result.get("next_steps", "")
                }

                # 2. Запис в Google Sheets
                client = get_google_sheet_client()
                if client:
                    try:
                        sheet = client.open("Sales Leads").sheet1
                        # Якщо таблиця пуста - додаємо заголовки
                        if not sheet.get_values():
                            sheet.append_row(list(row_data.keys()))
                        
                        sheet.append_row(list(row_data.values()))
                        st.success(t('success'))
                        
                        # 3. Оновлюємо локальну історію (додаємо новий запис на початок)
                        # Але оскільки ми хочемо точно те, що в таблиці - 
                        # краще просто додати цей об'єкт в сесію
                        st.session_state['history'].insert(0, row_data)
                        
                    except Exception as e:
                        st.error(f"Sheet Error: {e}")
                
            except Exception as e:
                st.error(f"General Error: {e}")

# --- 5. ВІДОБРАЖЕННЯ ІСТОРІЇ ---
st.write("---")
col_hist1, col_hist2 = st.columns([3,1])
with col_hist1:
    st.subheader(t('history_header'))
with col_hist2:
    if st.button("🔄 Reload"):
        st.session_state['history'] = load_history()
        st.rerun()

if st.session_state['history']:
    for item in st.session_state['history']:
        # Адаптуємо ключі, бо gspread повертає те, що в заголовку таблиці (наприклад "Company")
        # А JSON від AI дає "company_name".
        # Шукаємо назву в різних варіантах ключів
        comp = item.get('Company') or item.get('company_name') or "Record"
        contact = item.get('Contact') or item.get('contact_person') or ""
        time = item.get('Timestamp') or item.get('timestamp') or ""
        
        with st.expander(f"🏢 {comp} - {contact} ({time})"):
            st.write(f"**Email:** {item.get('Email') or item.get('email')}")
            st.write(f"**Phone:** {item.get('Phone') or item.get('phone')}")
            st.write(f"**Sentiment:** {item.get('Sentiment') or item.get('sentiment')}")
            st.info(f"**Summary:** {item.get('Summary') or item.get('summary')}")
            st.warning(f"**Next Steps:** {item.get('Next Steps') or item.get('next_steps')}")
else:
    st.info(t('no_history'))