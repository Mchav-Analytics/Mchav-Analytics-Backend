import sqlite3
conn = sqlite3.connect('mchav.db')
c = conn.cursor()
c.execute("SELECT id, nombre, status FROM proyectos")
for row in c.fetchall():
    print(row)
conn.close()
