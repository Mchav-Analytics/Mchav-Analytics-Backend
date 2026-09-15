import sqlite3
conn = sqlite3.connect('mchav.db')
c = conn.cursor()
c.execute("SELECT count(*) FROM issues WHERE id_proyecto = '10000'")
print('Total 10000:', c.fetchone()[0])
c.execute("SELECT id_sprint, count(*) FROM issues WHERE id_proyecto = '10000' GROUP BY id_sprint")
print(c.fetchall())
