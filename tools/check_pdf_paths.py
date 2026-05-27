"""检查数据库中的 PDF 路径"""
import sqlite3
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import DB_PATH

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
c = conn.cursor()
c.execute('SELECT title, pdf_path FROM tenders WHERE pdf_path IS NOT NULL AND pdf_path != "" LIMIT 10')
rows = c.fetchall()

for r in rows:
    title = r['title'][:50]
    pdf_path = r['pdf_path']
    exists = os.path.exists(pdf_path) if pdf_path else False
    print(f"标题：{title}...")
    print(f"PDF 路径：{pdf_path}")
    print(f"存在：{exists}")
    print()

conn.close()
