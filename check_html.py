from bs4 import BeautifulSoup
import re
import sys

def analyze(filename):
    print(f'--- Analyzing {filename} ---')
    with open(filename, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')
    
    # Also find if there is an iframe
    iframes = soup.find_all('iframe')
    if iframes:
        print(f'Found {len(iframes)} iframes')
        for i, ifr in enumerate(iframes):
            print(f'  Iframe {i}: {ifr.attrs}')

    # Find keywords
    keywords = ['招标', '公告', '公示', '采购']
    found = False
    for kw in keywords:
        tags = soup.find_all(string=re.compile(kw))
        if tags:
            found = True
            print(f'Keyword "{kw}" found in {len(tags)} places.')
            for tag in tags[:10]:
                p = tag.parent
                print(f'  <{p.name} class={p.get("class")}>{tag.strip()[:50]}</{p.name}>')
    
    if not found:
        print('No keywords found.')

if __name__ == '__main__':
    if len(sys.argv) > 1:
        analyze(sys.argv[1])
