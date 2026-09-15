import sqlite3
conn = sqlite3.connect('mchav.db')
cur = conn.cursor()
cur.execute("SELECT assignee_email, assignee_name, COUNT(*) FROM issues GROUP BY assignee_email, assignee_name")
print("Assignees in DB:")
for r in cur.fetchall():
    print(r)
