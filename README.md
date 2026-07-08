# MCHAV Analytics - Motor Backend (FastAPI) 🚀

Bienvenido al núcleo de **MCHAV Analytics**. Este backend está construido sobre Python y **FastAPI**, diseñado para ser un motor analítico de alto rendimiento que se integra con la API oficial de Atlassian Jira Cloud a través de OAuth2.

Nuestro objetivo es extraer, normalizar y calcular métricas ágiles avanzadas (Lead Time, Cycle Time, Throughput y Velocity) de forma automática.

---

## 🏗️ Arquitectura del Sistema

Hemos adoptado una arquitectura limpia y altamente escalable:

1. **Controladores y Servicios Desacoplados:**
   - **Controladores (Endpoints):** Ubicados en `app/api/v1/endpoints/`. Sirven como enrutadores ligeros que validan permisos mediante Inyección de Dependencias, sin albergar lógica matemática pesada.
   - **Servicios:** Ubicados en `app/services/`. Aquí reside la lógica de negocio pesada, como `jira_sync.py` (proceso ETL) y `kpi.py` (cálculos matemáticos).
2. **Seguridad Stateless (HMAC):**
   - No utilizamos middlewares bloqueantes ni JWT inflados. La autenticación se realiza mediante **Cookies Firmadas con HMAC (SHA-256)** que vinculan el `session_id` con el token de OAuth2 de Jira de forma ultra-rápida y a prueba de ataques XSS.
3. **Type-Safety Estricto (Pydantic):**
   - Todas las respuestas de la API están protegidas por modelos de **Pydantic** (`app/schemas/`), garantizando que si Atlassian cambia sus estructuras JSON, nuestro sistema rechace y gestione el error antes de romper el Frontend.

---

## 📊 Módulo Analítico JQL y Métricas (HUs y RFs)

El motor principal de este proyecto se basa en la extracción quirúrgica de datos de Jira mediante **JQL (Jira Query Language)**. Las estructuras oficiales están centralizadas en `app/core/jql_config.py` y expuestas a través del router aislado `/jql`.

### 1. Extracción Delta (HU-013 / RF-023)
* **Query JQL:** `project = '{project_key}' AND updated >= '-24h'`
* **Propósito:** Endpoint de optimización. Se usa en procesos batch nocturnos para actualizar únicamente los tickets que sufrieron cambios recientes, evitando re-sincronizar bases de datos enteras.
* **Endpoint:** `GET /api/v1/jql/extraction-delta`

### 2. Velocity y Throughput (HU-005, HU-006 / RF-011, RF-012)
* **Query JQL:** `project = '{project_key}' AND status = '{status_done}' AND sprint = {sprint_id}`
* **Propósito:** Analiza el rendimiento del Sprint activo o cerrado. Suma los **Story Points (Velocity)** completados y cuenta el volumen neto de tickets entregados **(Throughput)**.
* **Endpoint:** `GET /api/v1/jql/velocity-throughput`

### 3. Tiempos de Ciclo (HU-007, HU-008 / RF-013, RF-014)
* **Query JQL:** `project = '{project_key}' AND resolutiondate >= '{start_date}' AND resolutiondate <= '{end_date}'`
* **Propósito:** Obtiene el universo de tickets finalizados en un rango de fechas. Nuestro motor lee el *changelog* histórico de estos tickets para pre-computar en días hábiles el **Lead Time** (tiempo desde creación) y el **Cycle Time** (tiempo en desarrollo activo).
* **Endpoint:** `GET /api/v1/jql/time-cycles`

---

## 🔌 Webhooks y Sincronización en Tiempo Real

Para no depender exclusivamente de extracciones por lotes o procesos manuales, el sistema implementa un **Webhook Listener** pasivo.
* **Endpoint:** `POST /api/v1/jira/webhook`
* **Comportamiento:** Cada vez que un usuario de Jira mueve un ticket de columna o crea un bug, Atlassian dispara un JSON hacia este endpoint. El backend *mapea* instantáneamente esos datos hacia los modelos de PostgreSQL y recalcula los KPIs al vuelo para mantener el Dashboard en vivo.

---

## 🧪 Entorno de Pruebas Unitarias

El aseguramiento de la calidad está respaldado por **pytest**. 
Las pruebas puras (Edge Cases y Testing de Seguridad) se alojan en el directorio `/tests/`.

Para ejecutar toda la suite de pruebas unitarias (por ejemplo, para validar la invulnerabilidad del cifrado HMAC):
```bash
pytest tests/ -v
```

---

## 📚 Documentación Interactiva

FastAPI genera automáticamente la documentación técnica del proyecto. Para probar cualquier query JQL descrita arriba, revisar los esquemas de respuesta Pydantic, o simular un webhook, simplemente corre el servidor de desarrollo y visita:

👉 **[Swagger (OpenAPI) - http://localhost:8000/docs](http://localhost:8000/docs)**

Para un entendimiento más profundo, puedes consultar los archivos individuales en la carpeta `docs/`:
- `docs/controladores_vs_servicios.md`
- `docs/autenticacion_hmac.md`
- `docs/mapeo_datos_jira.md`
- `docs/swagger_jira_tutorial.md`
