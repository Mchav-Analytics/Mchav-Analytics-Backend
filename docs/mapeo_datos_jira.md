# ¿Qué significa "Mapear" los datos de Jira? 🧩

"Mapear respuestas JSON de Jira a modelos del backend" es básicamente **hacer de traductor y filtro** entre el idioma desordenado en el que Jira nos manda los datos y la estructura limpia que nuestra base de datos en PostgreSQL entiende.

Imagínate esto como recibir un paquete de Amazon gigantesco lleno de anime de embalaje, recibos y cajas dentro de cajas, cuando tú en realidad solo pediste un reloj.

---

## 🛑 El Problema (El JSON de Jira)
Cuando le preguntamos a Jira por un ticket (usando la API o a través de un Webhook), Jira no solo nos dice *"El ticket está en progreso"*. Nos manda un archivo de texto gigantesco (JSON) con **miles de líneas de información irrelevante**: 
- Enlaces a avatares.
- IDs internos raros de Atlassian.
- El color hexadecimal de la etiqueta.
- La zona horaria del usuario que lo creó.
- Configuraciones del tablero.

## 🟢 La Solución (El "Mapeo")
En nuestro backend de FastAPI (específicamente en `app/services/jira_sync.py` o en las rutas del webhook en `jira.py`), hacemos el proceso de "mapeo". Esto significa:

1. **Ignorar la basura:** Recibimos el paquete gigante (JSON) y desechamos todo lo que no nos sirve para la analítica.
2. **Extraer lo valioso:** Buscamos con pinzas variables muy específicas como `fields.summary` (título del ticket), `fields.created` (fecha de creación) o el historial de transiciones (*changelog*).
3. **Traducirlo a nuestros Modelos:** Tomamos esos datos extraídos y los metemos a la fuerza en nuestros "moldes" de Python (nuestras clases de SQLAlchemy como `models.Issue`, `models.Sprint` o `models.TransicionEstadoIssue`).

---

## 💻 Un Ejemplo Real en nuestro Código

Cuando entra un Webhook automático desde Jira, nosotros hacemos este mapeo exacto en Python:

```python
# 1. Llega el JSON gigante desde Jira (basura incluida)
payload = await request.json()

# 2. Empezamos a "mapear" (extraer con pinzas solo lo que nos importa del caos)
issue_key = payload["issue"]["key"] 
summary = payload["issue"]["fields"]["summary"]
status = payload["issue"]["fields"]["status"]["name"]

# 3. Lo metemos en nuestro Modelo Limpio del Backend (SQLAlchemy)
nuevo_ticket = models.Issue(
    key_issue = issue_key,
    summary = summary,
    status_actual = status
)

# 4. Lo guardamos permanentemente en PostgreSQL
db.add(nuevo_ticket)
db.commit()
```

### 🎯 En Resumen
Mapear es agarrar el formato complejo y caótico de un sistema externo (Jira) y "moldearlo" para que encaje perfectamente en las tablas relacionales de nuestra propia base de datos, asegurándonos de guardar **únicamente lo que necesitamos** para calcular nuestros KPIs (Lead Time, Cycle Time, Velocity y Throughput) y mantener nuestra base de datos ligera y rápida.
