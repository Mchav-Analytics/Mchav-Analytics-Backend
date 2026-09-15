import sqlite3
conn = sqlite3.connect('mchav.db')
cur = conn.cursor()
cur.execute("SELECT email, nombre FROM usuarios WHERE email='valentina1025m@gmail.com'")
print("Usuarios DB:", cur.fetchall())
