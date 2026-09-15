import sqlite3
conn = sqlite3.connect('mchav.db')
cur = conn.cursor()
cur.execute("DELETE FROM usuarios WHERE email = 'vhoyos@mchav.com'")
conn.commit()
print("Usuario eliminado:", cur.rowcount)
