import sqlite3

conn = sqlite3.connect('mchav.db')
cur = conn.cursor()
cur.execute("SELECT id_sprint, nombre, fecha_inicio FROM sprints WHERE id_proyecto='10000'")
for r in cur.fetchall():
    print(r)
conn.close()
