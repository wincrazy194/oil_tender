from bs4 import BeautifulSoup
import re
import sys

def deep_analyze(filename, keyword):
    print(f'--- Deep Analysis of {filename} for "{keyword}" ---')
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f.read(), 'html.parser')
    except Exception as e:
        print(f'Error reading file: {e}')
        return

    targets = soup.find_all(string=re.compile(keyword))
    if not targets:
        print(f'Keyword "{keyword}" not found.')
        return

    print(f'Found {len(targets)} matches. Showing top 5 structures:')
    for i, tag in enumerate(targets[:5]):
        print(f'\nMatch {i+1}: "{tag.strip()[:50]}"')
        curr = tag.parent
        path = []
        for depth in range(8):
            attrs_str = " ".join([f'{k}="{v}"' for k, v in curr.attrs.items()])
            path.append(f'<{curr.name} {attrs_str}>')
            curr = curr.parent
            if not curr or curr.name == '[document]': break
        
        for p in reversed(path):
            print(f'  {p}')

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python deep_check.py <file> <keyword>")
    else:
        deep_analyze(sys.argv[1], sys.argv[2])
