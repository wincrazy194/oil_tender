from bs4 import BeautifulSoup
import os

with open('debug_cnpc.html', 'r', encoding='utf-8') as f:
    soup = BeautifulSoup(f.read(), 'html.parser')
    print('--- CNPC Links ---')
    for a in soup.find_all('a'):
        text = a.get_text(strip=True)
        href = a.get('href', '')
        if any(k in text for k in ['招标', '公告', '中标', '结果', '公示']):
            print(f'Text: {text}, Href: {href}')
