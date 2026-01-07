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
st.set_page_config(page_title="Expo AI", page_icon="🚀", layout="centered")

# Використовуємо Flash. Завдяки оновленому requirements.txt це запрацює.
MODEL_NAME = "gemini-1.5-flash"

# Ініціалізація стану
if 'language' not in st.session_state:
    st.session_state['language'] = 'uk'

# --- 2. СЛОВНИК ПЕРЕКЛАДІВ ---
# Тут прописані ВСІ тексти інтерфейсу
translations = {
    'uk': {
        'title': "🚀 Expo AI Асистент",
        'lang_label': "Мова / Language",
        'input_company_label': "🏢 Назва компанії",
        'input_company_placeholder': "Введіть назву, якщо немає візитки",
        'photo_method_label': "Як додати фото?",
        'method_camera': "📸 Відкрити камеру",
        'method_upload': "📂 Завантажити файл (Швидше)",
        'cam_label': "Зробіть фото",
        'upload_label': "Виберіть фото візитки",
        'audio_header': "🎤 Голосовий запис",
        'audio_label': "Натисніть мікрофон та говоріть",
        'btn_submit': "📤 Обробити та відправити",
        'warning_nodata': "⚠️ Увага: Немає даних для відправки! Додайте фото, звук або назву.",
        'processing': "⏳ Аналізую візитку та аудіо... Це займе кілька секунд.",
        'success': "✅ Готово! Дані збережено в таблицю.",
        'error_title': "Помилка:",
        'result_header': "Результат обробки:",
        'settings_api_error': "Помилка API ключа. Перевірте налаштування Render.",
        'sheet_connect_error': "Помилка підключення до таблиці:"
    },
    'en': {
        'title': "🚀 Expo AI Assistant",
        'lang_label': "Language / Мова",
        'input_company_label': "🏢 Company Name",
        'input_company_placeholder': "Enter name if no card available",
        'photo_method_label': "Photo Input Method",
        'method_camera': "📸 Open Camera",
        'method_upload': "📂 Upload File (Faster)",
        'cam_label': "Take a photo",
        'upload_label': "Choose business card image",
        'audio_header': "🎤 Voice Recording",
        'audio_label': "Press mic and speak",
        'btn_submit': "📤 Process & Send",
        'warning_nodata': "⚠️ Warning: No data to send! Add photo, audio, or name.",
        'processing': "⏳ Analyzing card and audio... Please wait.",
        'success': "✅ Done! Data saved to sheet.",
        'error_title': "Error:",
        'result_header': "Processed Result:",
        'settings_api_error': "API Key Error. Check Render settings.",
        'sheet_connect_error': "Sheet Connection Error:"
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
            return None

        creds_dict = json.loads(creds_json_str)
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"{t('sheet_connect_error')} {e}")
        return None

def process_data(api_key, image_bytes, audio_file, user_text):
    genai.configure(api_key=api_key)
    
    # Спроба ініціалізації моделі
    try:
        model = genai.GenerativeModel(MODEL_NAME)
    except Exception:
        # Фоллбек, якщо раптом ім'я не сподобається
        model = genai.GenerativeModel("gemini-1.5-flash-latest")

    system_instruction = """
    You are an AI Sales Assistant at an exhibition.
    INPUTS: Business Card (Image) and/or Voice Feedback (Audio).
    
    TASK:
    1. Extract structured data from the image (Name, Company, Email, Phone, Position).
    2. Transcribe and summarize the audio (ignore background noise).
    3. IMPORTANT: The Output MUST be in the same language as the User Interface (Ukrainian or English).
    
    RETURN JSON:
    {
        "company_name": "string",
        "contact_person": "string",
        "position": "string",
        "email": "string",
        "phone": "string",
        "summary": "string (summary of the conversation)",
        "sentiment": "string (Positive/Neutral/Negative)",
        "next_steps": "string (action items)"
    }
    """
    
    content = [system_instruction]
    
    if user_text:
        content.append(f"User Text Note: {user_text}")
    
    if image_bytes:
        img = Image.open(io.BytesIO(image_bytes))
        content.append(img)
        
    if audio_file:
        audio_bytes = audio_file.read()
        content.append({"mime_type": "audio/wav", "data": audio_bytes})

    # Виклик
    response = model.generate_content(content, generation_config={"response_mime_type": "application/json"})
    return json.loads(response.text)

# --- 4. ІНТЕРФЕЙС ---

# --- Перемикач мови ---
# Використовуємо columns, щоб кнопка була компактною
col_head1, col_head2 = st.columns([3, 1])
with col_head1:
    st.title(t('title'))
with col_head2:
    # Radio кнопка працює як перемикач
    current_lang = st.radio(
        t('lang_label'), 
        ['UA', 'EN'], 
        index=0 if st.session_state['language'] == 'uk' else 1, 
        label_visibility="collapsed",
        horizontal=True
    )
    # Оновлення стану
    selected_lang = 'uk' if current_lang == 'UA' else 'en'
    if selected_lang != st.session_state['language']:
        st.session_state['language'] = selected_lang
        st.rerun()

st.divider()

# --- Ввід даних ---
company_text = st.text_input(t('input_company_label'), placeholder=t('input_company_placeholder'))

st.write("") # Відступ

# --- Фото (Вибір методу) ---
method = st.radio(t('photo_method_label'), [t('method_upload'), t('method_camera')], horizontal=True)

final_image_bytes = None

if method == t('method_camera'):
    # Камера
    cam_file = st.camera_input(t('cam_label'))
    if cam_file:
        final_image_bytes = cam_file.getvalue()
else:
    # Завантаження файлу (ШВИДШЕ)
    up_file = st.file_uploader(t('upload_label'), type=['jpg', 'png', 'jpeg'])
    if up_file:
        final_image_bytes = up_file.getvalue()
        st.image(up_file, width=200)

st.write("") # Відступ

# --- Аудіо ---
st.subheader(t('audio_header'))
audio_val = st.audio_input(t('audio_label'))

st.divider()

# --- Кнопка ---
if st.button(t('btn_submit'), type="primary", use_container_width=True):
    
    # Перевірка даних
    if not any([company_text, final_image_bytes, audio_val]):
        st.warning(t('warning_nodata'))
    else:
        # Перевірка ключа
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key and "GEMINI_API_KEY" in st.secrets:
            api_key = st.secrets["GEMINI_API_KEY"]
            
        if not api_key:
            st.error(t('settings_api_error'))
            st.stop()

        with st.spinner(t('processing')):
            try:
                # 1. AI Обробка
                result = process_data(api_key, final_image_bytes, audio_val, company_text)
                
                # 2. Google Sheets
                client = get_google_sheet_client()
                if client:
                    try:
                        sheet = client.open("Sales Leads").sheet1
                        # Заголовки, якщо треба
                        if not sheet.get_values():
                            sheet.append_row(["Timestamp", "Company", "Contact", "Position", "Email", "Phone", "Sentiment", "Summary", "Next Steps"])
                        
                        row = [
                            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
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
                    except Exception as e:
                        st.error(f"Sheet Error: {e}")

                st.success(t('success'))
                
                # Показати результат
                st.subheader(t('result_header'))
                st.json(result)
                
            except Exception as e:
                # Детальний вивід помилки
                st.error(f"{t('error_title')} {e}")