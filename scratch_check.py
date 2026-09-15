import sqlite3
conn = sqlite3.connect('mchav.db')
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
print('Tablas:', cur.fetchall())
