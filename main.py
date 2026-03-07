import os
import re
import requests
from datetime import datetime
from pypdf import PdfReader

def get_today_menu(menu_list):
    # Format today's date to match "07mar."
    # %d is day with leading zero, %b is short month name in lowercase
    today_str = datetime.now().strftime("%d%b").lower() + "."
    
    for item in menu_list:
        if item['date'] == today_str:
            return item
    return None

def read_first_page(file_path):
    try:
        # Create a reader object
        reader = PdfReader(file_path)
        
        # Get the first page (Python is 0-indexed, so 0 is page 1)
        first_page = reader.pages[0]
        
        # Extract and return text
        return first_page.extract_text()
    
    except Exception as e:
        return f"An error occurred: {e}"

def clean_menu_item(text):
    """Removes codes like /C, 1C, standalone C, H, F, dashes, and numbers."""
    # 1. Remove allergen ranges (e.g., 09-14)
    text = re.sub(r'\d{2}-\d{2}', '', text)
    # 2. Remove codes like /C, /F, /H, 1C, or 01
    text = re.sub(r'(/\w|\d+[A-Z]|\b\d{2}\b)', '', text)
    # 3. Remove standalone letters C, H, F, or T (usually at the end of lines)
    text = re.sub(r'\b[CHFT]\b', '', text)
    # 4. Remove dashes and dots used as separators
    text = text.replace("-", "").replace("Tr", "")
    # 5. Remove 'Fruta' or 'Lácteo' if you only want the main meal
    text = text.replace("Fruta", "").replace("Lácteo", "")
    # 6. Final cleanup of extra spaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def parse_and_clean_menu(text):
    # Pattern captures the date and everything until the Nutritional E: line
    pattern = r"(\d{2}[a-z]{3}\.)\s*(.*?)\s*E:\s*\d+"
    matches = re.findall(pattern, text, re.DOTALL)
    
    clean_data = []
    for date, raw_content in matches:
        # Split by newline to separate first and second course
        lines = [line.strip() for line in raw_content.split('\n') if line.strip()]
        
        if lines:
            first = clean_menu_item(lines[0])
            # Join the rest as the second course
            second = clean_menu_item(" ".join(lines[1:]))
            
            clean_data.append({
                "date": date,
                "first_course": first,
                "second_course": second
            })
            
    return clean_data

def send_telegram_message(token, chat_id, menu_item):
    if not menu_item:
        message = "No hay menú programado para hoy."
    else:
        message = (
            f"🍴 *Menú de Hoy ({menu_item['date']})*\n\n"
            f"🔹 *Primero:* {menu_item['first_course']}\n"
            f"🔸 *Segundo:* {menu_item['second_course']}\n\n"
            "¡Buen provecho! 🥗"
        )
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    response = requests.post(url, data=payload)
    return response.json()

# PRO TIP: Use 'r' before the string to fix "invalid escape sequence"
path = r"./menu.pdf" 
menu_data = parse_and_clean_menu(read_first_page(path))

today_menu = get_today_menu(menu_data)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
send_telegram_message(TOKEN, CHAT_ID, today_menu)