import sqlite3
conn = sqlite3.connect('mchav.db')
cur = conn.cursor()
cur.execute("SELECT assignee_email, assignee_name, status_actual, summary FROM issues")
rows = cur.fetchall()
print(f"Total issues in DB: {len(rows)}")
for r in rows:
    print(r)
