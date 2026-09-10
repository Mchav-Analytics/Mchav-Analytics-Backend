import sqlite3

conn = sqlite3.connect('mchav.db')
cur = conn.cursor()
cur.execute("SELECT key_issue, id_sprint, story_points FROM issues WHERE id_proyecto='10000' AND id_sprint IS NOT NULL LIMIT 10")
print(cur.fetchall())
conn.close()
