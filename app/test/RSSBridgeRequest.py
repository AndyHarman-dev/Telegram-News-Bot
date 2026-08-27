import requests

# URL RSS Bridge, к которому вы хотите обратиться
rss_bridge_url = 'http://localhost:3000/'

# Параметры запроса (например, для запроса новостей)
params = {
    'action': 'display',
    'limit' : '',
    'bridge': 'WeLiveSecurityBridge',  # Замените 'FeedName' на имя конкретного моста, который вам нужен
    'format': 'Mrss',  # Используйте 'Atom' или 'Rss'
    # Другие параметры, если необходимо
}

# Отправка запроса на сервер RSS Bridge
response = requests.get(rss_bridge_url, params=params)

# Проверка успешности запроса
if response.status_code == 200:
    # Если запрос успешен, вы можете получить данные в формате RSS
    rss_data = response.text
    print(rss_data)
else:
    print("Ошибка при запросе к серверу RSS Bridge:", response.status_code)