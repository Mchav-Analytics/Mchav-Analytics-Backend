# Documentación Interfaz OpenAPI y Swagger UI (FastAPI) 🚀

**MCHAV Analytics** utiliza **OpenAPI 3.0** y **Swagger UI** generados dinámicamente por FastAPI. Toda la especificación de la API RESTful se autodocumenta a partir de los tipos de datos en Python, esquemas Pydantic V2 y decoradores de controladores.

---

## 🌐 Direcciones de Acceso a la Documentación

Cuando el servidor Backend está en ejecución (`uvicorn app.main:app` o `docker compose up`), la documentación interactiva está disponible en:

* ⚙️ **Swagger UI (Pruebas en Vivo):** [http://localhost:8000/docs](http://localhost:8000/docs)
* 📄 **ReDoc (Documentación Estática):** [http://localhost:8000/redoc](http://localhost:8000/redoc)
* 📋 **Esquema OpenAPI JSON:** [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

---

## 🔒 Autenticación de la Documentación en Swagger

La interfaz de Swagger en `/docs` está protegida mediante **HTTP Basic Authentication** para evitar la exposición pública no autorizada del mapa de endpoints en producción.

### Credenciales de Acceso a `/docs`:
* **Usuario:** `admin` (Definido en la variable `DOCS_USER`)
* **Contraseña:** `MchavDocs2026!Sec#Admin` (Definida en la variable `DOCS_PASSWORD`)

> 💡 **Nota:** Al abrir `http://localhost:8000/docs` en el navegador, se desplegará una ventana emergente solicitando este usuario y contraseña antes de permitir visualizar la interfaz de Swagger.

---

## 🔍 Catálogo Completo de Endpoints Documentados en Swagger

### 1. 🔑 Autenticación y Control de Acceso (`/api/v1/auth`)

| Método | Endpoint | Descripción | Tipo de Auth |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/auth/login` | Redirecciona a Atlassian OAuth 2.0 (3LO) con estado CSRF | Pública |
| `GET` | `/api/v1/auth/callback` | Procesa el código devuelto por Atlassian y genera cookie HMAC | OAuth Code |
| `POST` | `/api/v1/auth/token` | Autenticación local mediante usuario y contraseña (Devuelve JWT Bearer) | Basic / Form |
| `POST` | `/api/v1/auth/jira-credentials` | Registra credenciales directas de API Token (Jira Domain, Email, Token) | Bearer / Cookie |

### 2. 📊 Métricas e Integración Jira (`/api/v1/jira`)

| Método | Endpoint | Descripción | Respuesta / JQL |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/jira/metrics` | Obtiene métricas agregadas globales (Caché TTL de 60s) | JQL: `statusCategory=Done`, `statusCategory="In Progress"`, `issuetype=Bug AND priority=Highest` |
| `POST` | `/api/v1/jira/sync` | Inicia la tarea asíncrona ETL de sincronización en segundo plano | Dispara `run_jira_sync_task` |
| `GET` | `/api/v1/jira/sync/logs` | Consulta los logs históricos del proceso de sincronización | Auditoría PostgreSQL (`LogsSincronizacion`) |
| `POST` | `/api/v1/jira/webhook` | Endpoint pasivo para recepción de eventos webhook de Jira | Procesa cambios de estado en tiempo real |

### 3. 🎯 Consultas Especializadas JQL (`/api/v1/jql`)

| Método | Endpoint | Parámetros Query | Propósito de la Consulta |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/jql/extraction-delta` | `project_key`, `updated_since` | Extrae tickets creados o modificados después de una fecha |
| `GET` | `/api/v1/jql/velocity-throughput` | `project_key`, `status_done`, `sprint_id` | Consulta datos para cálculo de velocidad e ítems completados |
| `GET` | `/api/v1/jql/time-cycles` | `project_key`, `start_date`, `end_date` | Filtra historias para análisis de Lead Time y Cycle Time |

### 4. 📁 Gestión de Proyectos y Mapeos (`/api/v1/projects`)

| Método | Endpoint | Descripción | Modelo DTO |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/projects/` | Lista todos los proyectos registrados con paginación | `list[ProjectResponse]` |
| `GET` | `/api/v1/projects/{proyecto_id}/kpis` | Consulta el historial de KPIs calculados del proyecto | `list[KpisHistoricos]` |
| `GET` | `/api/v1/projects/{proyecto_id}/sprints` | Lista los sprints asociados a un proyecto | `list[SprintResponse]` |
| `GET` | `/api/v1/projects/{proyecto_id}/statuses` | Obtiene la lista única de nombres de estados para mapeos | `list[str]` |
| `POST` | `/api/v1/projects/{proyecto_id}/mappings` | Reemplaza las reglas de mapeo de estados y recalculá KPIs | `list[ProjectMappingPayload]` |

---

## 🛠️ Guía Paso a Paso: ¿Cómo Documentar Endpoints en Swagger UI con FastAPI?

Para asegurar que un controlador o endpoint se documente de manera clara y profesional en Swagger, se siguen tres estándares en el código Python de los controladores (`app/api/v1/controllers/`):

### 1. Usar Metadatos en el Decorador del Router
Se deben incluir los parámetros `summary`, `description`, `response_model` y `status_code`:

```python
from fastapi import APIRouter, Depends, Request
from app.schemas.project_schema import ProjectResponse

router = APIRouter()

@router.get(
    "/",
    response_model=list[ProjectResponse],
    summary="Listar todos los proyectos sincronizados",
    description="""
    Retorna la lista completa de proyectos registrados en **PostgreSQL**.
    Soporta parámetros de ordenamiento y paginación:
    * `limit`: Cantidad máxima de registros (default 100).
    * `offset`: Desplazamiento inicial (default 0).
    * `sort`: Campo de ordenamiento (`id_proyecto`, `nombre`).
    * `order`: Sentido (`asc`, `desc`).
    """
)
async def get_projects(request: Request, limit: int = 100, offset: int = 0):
    # Lógica del controlador...
    pass
```

### 2. Definir Esquemas DTO con Pydantic y Ejemplos (Field Examples)
Los modelos en `app/schemas/` utilizan `Field` con ejemplos claros para que Swagger muestre payloads interactivos:

```python
from pydantic import BaseModel, Field

class ProjectMappingPayload(BaseModel):
    estado_jira: str = Field(..., example="In Development", description="Nombre del estado exacto en Jira Cloud")
    estado_base: str = Field(..., example="IN_PROGRESS", description="Estado estándar de la plataforma (TO_DO, IN_PROGRESS, DONE)")

    class Config:
        json_schema_extra = {
            "example": {
                "estado_jira": "En Desarrollo",
                "estado_base": "IN_PROGRESS"
            }
        }
```

### 3. Autenticación Interactiva en Swagger UI ("Authorize")
Para probar endpoints protegidos directamente en la interfaz de Swagger UI:
1. Haz clic en el botón **"Authorize"** 🔓 en la esquina superior derecha de `http://localhost:8000/docs`.
2. Introduce tu token en formato **Bearer Token** o la cookie de sesión.
3. Haz clic en **"Authorize"** y cierra la ventana emergente.
4. Ahora podrás usar el botón **"Try it out"** y **"Execute"** en cualquier endpoint para probar respuestas en vivo.
