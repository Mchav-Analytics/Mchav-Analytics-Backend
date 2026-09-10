import sqlite3
conn = sqlite3.connect('mchav.db')
cur = conn.cursor()
cur.execute("SELECT id_proyecto, nombre, key_proyecto FROM proyectos")
print("Proyectos en DB:")
for r in cur.fetchall():
    print(r)
