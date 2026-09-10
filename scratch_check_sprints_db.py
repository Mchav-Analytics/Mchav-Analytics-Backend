import sqlite3

conn = sqlite3.connect('mchav.db')
cur = conn.cursor()
cur.execute("SELECT id_sprint, nombre FROM sprints WHERE id_proyecto='10000'")
print(cur.fetchall())
conn.close()
