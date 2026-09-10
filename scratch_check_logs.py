import sqlite3
conn = sqlite3.connect('mchav.db')
cur = conn.cursor()
cur.execute("SELECT id_log, fecha_ejecucion, tipo_sincronizacion, ejecutado_por FROM logs_sincronizacion")
print("Logs en BD:", cur.fetchall())
