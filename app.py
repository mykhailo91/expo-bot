import streamlit as st
import google.generativeai as genai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from PIL import Image
import json
import os
import datetime

# --- КОНФІГУРАЦІЯ ---
# Якщо модель ще не доступна публічно під назвою 'gemini-3-pro-preview',
# спробуйте 'gemini-exp-1206' або 'gemini-1.5-pro-002'.
MODEL_NAME = "gemini-1.5-pro-002" 
# Я поставив 1.5 Pro як стабільну базу. 
# Якщо у вас є доступ до 3.0, змініть рядок вище на "gemini-3-pro-preview"

st.set_page_config(page_title="Expo AI Recorder", page_icon="🎙️", layout="centered")

# --- ФУНКЦІЇ ---

def get_google_sheet_client():
    # Отримуємо креденшали з секретів Streamlit або змінних середовища
    try:
        # Спроба отримати JSON з секретів (для Render/Local)
        creds_json_str = os.environ.get("GOOGLE_CREDENTIALS")
        if not creds_json_str and "GOOGLE_CREDENTIALS" in st.secrets:
             creds_json_str = st.secrets["GOOGLE_CREDENTIALS"]
        
        creds_dict = json.loads(creds_json_str)
        
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"Помилка підключення до Google Sheets: {e}")
        return None

def process_with_gemini(api_key, image, audio_file, user_text):
    genai.configure(api_key=api_key)
    
    # Конфігурація моделі
    generation_config = {
        "temperature": 0.4,
        "response_mime_type": "application/json",
    }
    
    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        generation_config=generation_config,
        system_instruction="""
        Ти - професійний асистент продажів. Твоє завдання - структурувати дані про зустріч.
        1. Проаналізуй фото візитки (якщо є) для отримання контактів.
        2. Прослухай аудіо (якщо є) для отримання контексту та нюансів.
        3. Використовуй текстові нотатки користувача як пріоритетні.
        
        Виведи JSON з такими полями (пиши українською, де доречно):
        - company_name (string)
        - contact_person (string)
        - position (string)
        - email (string)
        - phone (string)
        - summary (string, стислий підсумок зустрічі)
        - sentiment (string: "Холодний", "Теплий", "Гарячий")
        - action_items (string, наступні кроки)
        - notes (string, будь-які важливі деталі)
        """
    )

    prompt_parts = ["Оброби цю зустріч."]
    
    if user_text:
        prompt_parts.append(f"Додаткові нотатки користувача: {user_text}")
    
    if image:
        prompt_parts.append(image)
        
    if audio_file:
        # Streamlit повертає BytesIO, Gemini потребує байти
        audio_bytes = audio_file.read()
        prompt_parts.append({"mime_type": "audio/wav", "data": audio_bytes})

    response = model.generate_content(prompt_parts)
    return json.loads(response.text)

# --- ІНТЕРФЕЙС ---

st.title("🚀 Expo Meeting AI")
st.markdown(f"Using model: `{MODEL_NAME}`")

with st.form("meeting_form"):
    company_input = st.text_input("Назва компанії (опціонально)")
    
    col1, col2 = st.columns(2)
    with col1:
        picture = st.camera_input("📸 Фото візитки")
    with col2:
        audio_input = st.audio_input("🎙️ Голосовий фідбек")

    submit_button = st.form_submit_button("Обробити та зберегти", type="primary")

if submit_button:
    if not (picture or audio_input or company_input):
        st.warning("Будь ласка, додайте хоча б фото, аудіо або назву компанії.")
    else:
        # Перевірка наявності ключів
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key and "GEMINI_API_KEY" in st.secrets:
            api_key = st.secrets["GEMINI_API_KEY"]
            
        if not api_key:
            st.error("API Key for Gemini is missing!")
            st.stop()

        with st.spinner("AI думає... це може зайняти 10-15 секунд..."):
            try:
                # 1. Обробка AI
                img_obj = Image.open(picture) if picture else None
                
                ai_data = process_with_gemini(api_key, img_obj, audio_input, company_input)
                
                st.success("Дані оброблено!")
                st.json(ai_data) # Показати юзеру, що вийшло

                # 2. Збереження в Google Sheet
                client = get_google_sheet_client()
                if client:
                    # Вкажіть тут назву вашої таблиці
                    sheet = client.open("Sales Leads").sheet1 
                    
                    # Якщо таблиця порожня, додамо заголовки
                    if not sheet.get_values():
                        sheet.append_row(["Timestamp", "Company", "Contact", "Position", "Email", "Phone", "Sentiment", "Summary", "Action Items"])
                    
                    row = [
                        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        ai_data.get("company_name"),
                        ai_data.get("contact_person"),
                        ai_data.get("position"),
                        ai_data.get("email"),
                        ai_data.get("phone"),
                        ai_data.get("sentiment"),
                        ai_data.get("summary"),
                        ai_data.get("action_items")
                    ]
                    sheet.append_row(row)
                    st.toast("✅ Збережено в таблицю!", icon="🎉")
                
            except Exception as e:
                st.error(f"Сталася помилка: {e}")