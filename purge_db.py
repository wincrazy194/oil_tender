
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, 'data', 'oil_tender.db')
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 清理中石化之前的垃圾数据
    junk_patterns = ["%登录%", "%您好%", "%专区%", "%退出%"]
    for pattern in junk_patterns:
        cursor.execute("DELETE FROM tenders WHERE company = '中石化' AND title LIKE ?", (pattern,))
    
    conn.commit()
    print(f"Purged {cursor.rowcount} junk rows from Sinopec database.")
    
    # 统计最终结果
    cursor.execute('SELECT company, COUNT(*) FROM tenders GROUP BY company')
    print("\n--- Final Counts ---")
    for r in cursor.fetchall():
        print(f"{r[0]}: {r[1]} items")
        
    conn.close()
else:
    print("Database not found.")
