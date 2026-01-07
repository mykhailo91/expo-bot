import streamlit as st
import google.generativeai as genai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from PIL import Image
import json
import os
import datetime
import io

# --- 1. НАЛАШТУВАННЯ ---
st.set_page_config(page_title="Expo AI Lead", page_icon="🚀", layout="centered")

# Використовуємо стабільну модель, щоб уникнути помилок 404
# Flash ідеальна для аудіо та швидкої відповіді
MODEL_NAME = "gemini-1.5-flash"

# Ініціалізація стану (пам'ять сесії)
if 'language' not in st.session_state:
    st.session_state['language'] = 'uk'
if 'camera_active' not in st.session_state:
    st.session_state['camera_active'] = False
if 'captured_photo' not in st.session_state:
    st.session_state['captured_photo'] = None

# --- 2. СЛОВНИК ПЕРЕКЛАДІВ ---
translations = {
    'uk': {
        'title': "🚀 Expo AI Асистент",
        'lang_select': "Мова / Language:",
        'input_company': "Назва компанії (введіть вручну, якщо немає візитки)",
        'btn_open_camera': "📸 Відкрити камеру",
        'btn_close_camera': "❌ Закрити камеру",
        'btn_delete_photo': "🗑️ Видалити фото",
        'cam_label': "Зробіть фото",
        'audio_label': "🎙️ Голосовий фідбек (скажіть враження, AI прибере шум)",
        'btn_submit': "📤 Обробити та відправити",
        'processing': "⏳ Відправляємо дані в AI та Google Sheets...",
        'success': "✅ Успішно! Дані в таблиці.",
        'error_input': "⚠️ Будь ласка, зробіть фото АБО запишіть аудіо АБО введіть назву.",
        'result_title': "Результат обробки:",
        'history_title': "Історія сесії"
    },
    'en': {
        'title': "🚀 Expo AI Assistant",
        'lang_select': "Language / Мова:",
        'input_company': "Company Name (manual entry if no card)",
        'btn_open_camera': "📸 Open Camera",
        'btn_close_camera': "❌ Close Camera",
        'btn_delete_photo': "🗑️ Delete Photo",
        'cam_label': "Take a photo",
        'audio_label': "🎙️ Voice Feedback (AI will filter background noise)",
        'btn_submit': "📤 Process & Send",
        'processing': "⏳ Sending to AI and Google Sheets...",
        'success': "✅ Success! Data saved.",
        'error_input': "⚠️ Please take a photo OR record audio OR enter a name.",
        'result_title': "Processed Result:",
        'history_title': "Session History"
    }
}

def t(key):
    return translations[st.session_state['language']][key]

# --- 3. ФУНКЦІЇ ---

def get_google_sheet_client():
    try:
        creds_json_str = os.environ.get("GOOGLE_CREDENTIALS")
        if not creds_json_str and "GOOGLE_CREDENTIALS" in st.secrets:
             creds_json_str = st.secrets["GOOGLE_CREDENTIALS"]
        
        if not creds_json_str:
            st.error("Credential error: No keys found.")
            return None

        creds_dict = json.loads(creds_json_str)
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"Google Sheets Connection Error: {e}")
        return None

def process_data(api_key, image_bytes, audio_file, user_text):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(MODEL_NAME) 

    # Промпт для AI
    system_instruction = """
    Analyze the provided sales meeting data (Audio and/or Image).
    Context: A busy exhibition.
    
    1. IMAGE: Extract Company Name, Contact Name, Email, Phone, Position.
    2. AUDIO: Transcribe user feedback about the meeting. Ignore background noise.
    3. LANGUAGE: Output the result in the user's interface language (Ukrainian or English).
    
    Return pure JSON structure:
    {
        "company_name": "string",
        "contact_person": "string",
        "position": "string",
        "email": "string",
        "phone": "string",
        "summary": "string (details of conversation)",
        "sentiment": "string (Positive/Neutral/Negative)",
        "next_steps": "string (action items)"
    }
    """
    
    content = [system_instruction]
    
    if user_text:
        content.append(f"User manual note: {user_text}")
    
    if image_bytes:
        img = Image.open(io.BytesIO(image_bytes))
        content.append(img)
        
    if audio_file:
        audio_bytes = audio_file.read()
        content.append({"mime_type": "audio/wav", "data": audio_bytes})

    # Виклик AI
    response = model.generate_content(content, generation_config={"response_mime_type": "application/json"})
    return json.loads(response.text)

# --- 4. ІНТЕРФЕЙС (UI) ---

# --- Перемикач мови (Зверху) ---
col_lang1, col_lang2 = st.columns([1, 3])
with col_lang1:
    st.write("🌐 Language:")
with col_lang2:
    # Використовуємо радіо кнопки горизонтально для швидкого доступу
    lang_choice = st.radio(
        "Label hidden", 
        options=['UA', 'EN'], 
        index=0 if st.session_state['language'] == 'uk' else 1,
        horizontal=True,
        label_visibility="collapsed"
    )
    # Оновлення мови при зміні
    new_lang = 'uk' if lang_choice == 'UA' else 'en'
    if new_lang != st.session_state['language']:
        st.session_state['language'] = new_lang
        st.rerun()

st.title(t('title'))
st.divider()

# --- Форма вводу ---

# 1. Текст
company_text = st.text_input("🏢 " + t('input_company'))

# 2. Блок Камери (Керований)
st.subheader("📷 Фото")

if st.session_state['captured_photo'] is None:
    # Якщо фото ще немає
    if not st.session_state['camera_active']:
        # Камера вимкнена - показуємо кнопку "Відкрити"
        if st.button(t('btn_open_camera')):
            st.session_state['camera_active'] = True
            st.rerun()
    else:
        # Камера увімкнена - показуємо інпут і кнопку "Закрити"
        col_cam_act1, col_cam_act2 = st.columns([3, 1])
        with col_cam_act1:
            img_file_buffer = st.camera_input(t('cam_label'))
        with col_cam_act2:
            if st.button(t('btn_close_camera')):
                st.session_state['camera_active'] = False
                st.rerun()
        
        # Якщо зробили фото
        if img_file_buffer is not None:
            st.session_state['captured_photo'] = img_file_buffer.getvalue()
            st.session_state['camera_active'] = False # Ховаємо камеру після знімку
            st.rerun()
else:
    # Фото вже є - показуємо його
    st.image(st.session_state['captured_photo'], caption="Ready to send", width=300)
    if st.button(t('btn_delete_photo')):
        st.session_state['captured_photo'] = None
        st.rerun()

# 3. Блок Аудіо
st.subheader("🎤 Аудіо")
audio_val = st.audio_input(t('audio_label'))

st.divider()

# --- Кнопка відправки ---
if st.button(t('btn_submit'), type="primary", use_container_width=True):
    
    # Перевірка: чи є хоч якісь дані
    has_data = any([company_text, st.session_state['captured_photo'], audio_val])
    
    if not has_data:
        st.warning(t('error_input'))
    else:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key and "GEMINI_API_KEY" in st.secrets:
            api_key = st.secrets["GEMINI_API_KEY"]
            
        if not api_key:
            st.error("API Key not found. Check settings on Render.")
            st.stop()

        with st.spinner(t('processing')):
            try:
                # 1. Обробка AI
                result = process_data(api_key, st.session_state['captured_photo'], audio_val, company_text)
                
                # 2. Збереження в Google Sheets
                client = get_google_sheet_client()
                if client:
                    sheet = client.open("Sales Leads").sheet1
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Перевірка на заголовки
                    if not sheet.get_values():
                        sheet.append_row(["Time", "Company", "Contact", "Position", "Email", "Phone", "Sentiment", "Summary", "Next Steps"])
                    
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
                
                st.success(t('success'))
                st.json(result) # Показуємо результат для перевірки
                
                # Очистка після успішної відправки (опціонально, можна прибрати)
                # st.session_state['captured_photo'] = None
                
            except Exception as e:
                st.error(f"Error: {e}")