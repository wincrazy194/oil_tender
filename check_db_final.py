
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, 'data', 'oil_tender.db')
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("--- Distribution ---")
    cursor.execute('SELECT company, COUNT(*) FROM tenders GROUP BY company')
    for r in cursor.fetchall():
        print(f"{r[0]}: {r[1]}")
    
    for company in ["中石化", "中石油", "中海油"]:
        print(f"\n--- Latest 5 from {company} ---")
        cursor.execute('SELECT title, publish_date FROM tenders WHERE company = ? ORDER BY id DESC LIMIT 5', (company,))
        rows = cursor.fetchall()
        if not rows:
            print("No records found.")
        for r in rows:
            print(f"- {r[0]} | {r[1]}")
            
    conn.close()
else:
    print("Database not found.")
