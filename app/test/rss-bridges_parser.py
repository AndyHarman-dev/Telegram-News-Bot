import requests
import re
from xml.etree import ElementTree as ET

def fetch_rss(url):
    try:
        response = requests.get(url)  # Получаем данные по URL
        response.raise_for_status()  # Проверяем на ошибки HTTP
        # Преобразуем полученные данные в структуру XML
        root = ET.fromstring(response.content)
        for item in root.findall('.//item'):  # Находим все элементы <item>
            title = item.find('title').text
            link = item.find('link').text
            description = re.sub(r'<table.*?>.*?</table>|<iframe.*?>.*?</iframe>|<figure.*?>.*?</figure>', '', item.find('description').text, flags=re.DOTALL)
            clean_text = re.sub(r'</?h[1-6].*?>|</?p>', '\n', description)
            clean_text = re.sub(r'</?b>', '', clean_text)
            clean_text = re.sub(r'<a.*?>(.*?)</a>', r'\1', clean_text)
            clean_text = re.sub(r'</?ul>', '', clean_text)
            clean_text = re.sub(r'<li>', '\n', clean_text)
            clean_text = re.sub(r'</li>', '', clean_text)
            clean_text = re.sub(r'<[^>]+>', '', clean_text)
            clean_text = re.sub(r'^\s+', '', clean_text, flags=re.MULTILINE)
            #description = item.find('description').text
            print(f"Название: {title}\nСсылка: {link}\nОписание: {clean_text}\n")
    except requests.HTTPError as http_err:
        print(f"HTTP error occured: {http_err}")  # Обработка исключений HTTP
    except Exception as err:
        print(f"An error occured: {err}")  # Обработка других исключений

# Замените url на вашу RSS ссылку
url = "http://localhost:3000/?action=display&bridge=WeLiveSecurityBridge&limit=&format=Mrss"
fetch_rss(url)