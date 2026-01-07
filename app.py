import streamlit as st
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials # Нова бібліотека авторизації
from PIL import Image
import json
import os
import datetime
import io

# --- 1. НАЛАШТУВАННЯ ---
st.set_page_config(page_title="Expo AI", page_icon="🚀", layout="centered")

MODEL_NAME = "gemini-1.5-flash"

# Ініціалізація стану
if 'language' not in st.session_state:
    st.session_state['language'] = 'uk'
if 'history' not in st.session_state:
    st.session_state['history'] = []

# --- 2. СЛОВНИК ПЕРЕКЛАДІВ ---
translations = {
    'uk': {
        'title': "🚀 Expo AI Асистент",
        'lang_label': "Мова / Language",
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
        'sheet_connect_error': "Помилка підключення до таблиці (Credentials).",
        'sheet_not_found': "❌ Таблицю 'Sales Leads' не знайдено! Перевірте назву.",
        'history_header': "🗂️ Історія сесії",
        'no_history': "Поки що пусто."
    },
    'en': {
        'title': "🚀 Expo AI Assistant",
        'lang_label': "Language / Мова",
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
        'sheet_connect_error': "Sheet connection error (Credentials).",
        'sheet_not_found': "❌ Sheet 'Sales Leads' not found! Check the name.",
        'history_header': "🗂️ Session History",
        'no_history': "No records yet."
    }
}

def t(key):
    return translations[st.session_state['language']][key]

# --- 3. ФУНКЦІЇ ---

def get_google_sheet_client():
    try:
        # Отримуємо JSON з секретів
        creds_json_str = os.environ.get("GOOGLE_CREDENTIALS")
        if not creds_json_str and "GOOGLE_CREDENTIALS" in st.secrets:
             creds_json_str = st.secrets["GOOGLE_CREDENTIALS"]
        
        if not creds_json_str:
            st.error("❌ Немає ключів доступу (GOOGLE_CREDENTIALS).")
            return None

        creds_dict = json.loads(creds_json_str)
        
        # НОВІ ПРАВИЛЬНІ SCOPES (для gspread v6+)
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        # Використовуємо нову бібліотеку google.oauth2
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"{t('sheet_connect_error')} {e}")
        return None

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

# Сайдбар для технічної інформації (щоб переконатися, що все оновилося)
with st.sidebar:
    st.caption(f"v: gspread {gspread.__version__}")
    
col_head1, col_head2 = st.columns([3, 1])
with col_head1: st.title(t('title'))
with col_head2:
    lang = st.radio(t('lang_label'), ['UA', 'EN'], index=0 if st.session_state['language']=='uk' else 1, horizontal=True, label_visibility="collapsed")
    if (lang == 'UA' and st.session_state['language'] != 'uk'): st.session_state['language'] = 'uk'; st.rerun()
    elif (lang == 'EN' and st.session_state['language'] != 'en'): st.session_state['language'] = 'en'; st.rerun()

st.divider()

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
                # 1. AI
                result = process_data(api_key, final_image_bytes, audio_val, company_text)
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                result['timestamp'] = timestamp
                if company_text: result['company_name'] = company_text
                
                # 2. Локальне збереження
                st.session_state['history'].insert(0, result)

                # 3. Таблиця
                client = get_google_sheet_client()
                if client:
                    try:
                        sheet = client.open("Sales Leads").sheet1
                        if not sheet.get_values():
                            sheet.append_row(["Timestamp", "Company", "Contact", "Position", "Email", "Phone", "Sentiment", "Summary", "Next Steps"])
                        
                        row = [
                            timestamp,
                            result.get("company_name", ""),
                            result.get("contact_person", ""),
                            result.get("position", ""),
                            result.get("email", ""),
                            result.get("phone", ""),
                            result.get("sentiment", ""),
                            result.get("summary", ""),
                            result.get("next_steps", "")
                        ]
                        sheet.append_row(row)
                        st.success(t('success')) # Якщо дійшли сюди - все точно ок
                    except gspread.exceptions.SpreadsheetNotFound:
                         st.error(t('sheet_not_found'))
                    except Exception as e:
                        st.error(f"Sheet Error Details: {e}")
                
            except Exception as e:
                st.error(f"General Error: {e}")

st.write("---")
st.subheader(t('history_header'))
if st.session_state['history']:
    for item in st.session_state['history']:
        header = item.get('company_name') or item.get('contact_person') or "Record"
        with st.expander(f"🏢 {header} ({item.get('timestamp')})"):
            st.json(item)
else:
    st.info(t('no_history'))