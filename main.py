import os
import re
import requests
from datetime import datetime
from pypdf import PdfReader
from bs4 import BeautifulSoup

def download_latest_menu():
    url = "https://laspalmas.salesianos.edu/colegio/comedorescolar/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # We look for all links that end in .pdf and contain "Descargar"
        pdf_link = None
        for a in soup.find_all('a', href=True):
            if ".pdf" in a['href'] and "Descargar" in a.text:
                # To be extra safe, we check if the URL contains current year/month
                current_year_month = datetime.now().strftime("%Y/%m")
                if current_year_month in a['href']:
                    pdf_link = a['href']
                    break
        
        # Fallback: If no year/month match, just take the first "Descargar" PDF link found
        if not pdf_link:
            for a in soup.find_all('a', href=True):
                if ".pdf" in a['href'] and "Descargar" in a.text:
                    pdf_link = a['href']
                    break

        if pdf_link:
            print(f"Found PDF: {pdf_link}")
            pdf_data = requests.get(pdf_link, headers=headers).content
            with open("menu.pdf", "wb") as f:
                f.write(pdf_data)
            return "menu.pdf"
            
    except Exception as e:
        print(f"Error scraping or downloading: {e}")
    
    return None

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
        first_page = reader.pages[1] # Now first page is informative and the menu is in second page.
        
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


def main():
    pdf_file = download_latest_menu()
    if not pdf_file or not os.path.exists(pdf_file):
        print("Could not get the menu file.")
        return

    menu_data = parse_and_clean_menu(read_first_page(pdf_file))

    today_menu = get_today_menu(menu_data)

    if today_menu:
        TOKEN = os.getenv("TELEGRAM_TOKEN")
        CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
        send_telegram_message(TOKEN, CHAT_ID, today_menu)
    else:
        print("Menu found in PDF, but no entry matches today's date.")

if __name__ == "__main__":
    main()
