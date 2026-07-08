# Documentación y Pruebas con Swagger (FastAPI) 🚀

En FastAPI, no tienes que escribir la documentación de Swagger a mano en un archivo extraño. **FastAPI genera la interfaz de Swagger automáticamente** leyendo el código Python. 

Para ver tu Swagger ahora mismo, solo entra en tu navegador a:
👉 **`http://localhost:8000/docs`**

A continuación, te presento la documentación de nuestras queries y un tutorial práctico de cómo inyectarle descripciones hermosas a ese Swagger.

---

## 🔍 Parte 1: Documentación de las Queries JQL y Endpoints Actuales

### 1. `GET /api/v1/jira/metrics` (Métricas Generales "Al Vuelo")
Extrae estadísticas globales en tiempo real haciendo peticiones a Jira.
* **JQL para Tickets Completados:** `statusCategory=Done` (Trae todo lo finalizado).
* **JQL para Tickets en Progreso:** `statusCategory="In Progress"` (Trae el trabajo actual).
* **JQL para Bugs Críticos:** `issuetype=Bug AND priority=Highest` (Identifica emergencias operativas).

### 2. `POST /api/v1/jira/sync` (Motor ETL de Sincronización)
Arranca el proceso pesado para descargar toda la historia de tickets a nuestra base de datos PostgreSQL.
* **JQL Principal:** `project='{LLAVE_DEL_PROYECTO}'`
* **Parámetros extra:** Usa `expand=changelog` para traer el historial minuto a minuto de en qué estado estuvo cada ticket, vital para calcular Lead/Cycle Time.

### 3. `GET /api/v1/jira/sync/logs` (Auditoría)
No usa JQL. Lee nuestra tabla local de PostgreSQL (`LogsSincronizacion`) para retornar el estado de las últimas tareas de sincronización.

### 4. `POST /api/v1/jira/webhook` (Eventos en Tiempo Real)
No usa JQL. Es un "teléfono rojo" pasivo. Espera a que Jira le mande un mensaje automático (Payload) cada vez que alguien mueve un ticket en el tablero oficial.

---

## 🛠️ Parte 2: Tutorial - ¿Cómo documentar esto en Swagger?

Para que tu interfaz en `http://localhost:8000/docs` se vea profesional, explique las queries y te permita hacer pruebas fácilmente, solo tienes que agregar tres cosas a tu código en `app/api/v1/endpoints/jira.py`:

### Paso 1: Ponerle "Nombre" y "Descripción" al Endpoint
Añade los parámetros `summary` y `description` al decorador `@router`. Puedes usar Markdown en la descripción.

```python
@router.get(
    "/metrics", 
    summary="Obtener métricas rápidas con JQL",
    description="""
    Realiza 3 consultas **JQL** a Jira para obtener totales rápidos:
    * `statusCategory=Done`
    * `statusCategory="In Progress"`
    * `issuetype=Bug AND priority=Highest`
    """
)
async def get_jira_metrics(request: Request, db: Session = Depends(get_db)):
    # ... tu código aquí
```

### Paso 2: Explicar qué responde (Response Model)
Swagger necesita saber cómo se ve el JSON de respuesta para mostrarte un ejemplo antes de que le des al botón "Try it out". Esto se hace creando una clase `Pydantic`.

```python
from pydantic import BaseModel

# Defines cómo se ve tu respuesta
class MetricsResponse(BaseModel):
    active_projects: int
    completed_tickets: int
    in_progress_tickets: int
    critical_bugs: int

# Se lo agregas al router
@router.get("/metrics", response_model=MetricsResponse)
async def get_jira_metrics(...):
```

### Paso 3: Probarlo en vivo
1. Guarda el archivo `jira.py`. Uvicorn recargará el servidor automáticamente.
2. Entra a `http://localhost:8000/docs`.
3. Busca tu endpoint, dale clic.
4. Verás la descripción que escribiste y un botón enorme que dice **"Try it out"**.
5. Dale clic y luego en **"Execute"** para hacer la prueba real desde ahí mismo.

---

*💡 **¿Qué sigue?** Si quieres, puedo modificar el archivo `jira.py` ahora mismo aplicándole todas estas reglas de Swagger a tus 4 endpoints para que te queden listos para probar y presentar.*
