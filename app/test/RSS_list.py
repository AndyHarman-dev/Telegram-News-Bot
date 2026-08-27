import requests
import json

rss_bridge_url = 'https://rss-bridge.org/bridge01/'

params = {
    'action': 'list'
}

questionToChatGPT3_5 = """
Answer my question with only "Yes" or "No". Don't write anything other than that. 
So, when customizing the article display, there is this option: '{}'. 
Now my question is: will selecting it allow me to see the full article content?
"""

response = requests.get(rss_bridge_url, params=params)

if response.status_code == 200:
    rss_data = response.text
    rss_data_dict: dict = json.loads(rss_data)
    print(rss_data_dict['bridges']['ABCNewsBridge']['parameters'][0]['topic']['name'])
    print(rss_data_dict['bridges']['WeLiveSecurityBridge']['parameters'][0]['limit']['name'])
    print(rss_data_dict['bridges']['NationalGeographicBridge']['parameters'])
    print(rss_data_dict['bridges']['AirBreizhBridge']['parameters']['Publications']['theme']['values'])
    print(rss_data_dict['bridges']['TldrTechBridge']['parameters'].keys())
else:
    print("Error accessing to RSS Bridge:", response.status_code)
