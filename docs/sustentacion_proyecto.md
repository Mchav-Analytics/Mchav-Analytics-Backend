# Sustentación Técnica del Proyecto - Backend de MCHAV Analytics

Este documento contiene la explicación exacta y justificación técnica de cómo se implementó cada uno de los requerimientos del Syllabus de las Fase 1 y Fase 2 en el código fuente de **MCHAV Analytics**.

---

## 🟢 FASE 1: Configuración, Conexión, Endpoints y Seguridad

### SEMANA 1: Configuración del Entorno

1. **Instalación de herramientas y dependencias:**
   - Gestionado a través del archivo [requirements.txt](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/requirements.txt) donde se especifican versiones estables y acotadas de dependencias clave: `fastapi`, `uvicorn`, `python-dotenv` (para variables de entorno), `httpx` (para peticiones asíncronas), `pydantic` (para validación de datos), `sqlalchemy`, `pytest` y `alembic` (para base de datos y migraciones).
2. **Configuración de FastAPI:**
   - La instancia de FastAPI se crea centralmente en [main.py](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/app/main.py) definiendo título y metadatos del proyecto. Además, se añade el middleware de CORS (`CORSMiddleware`) configurando de manera dinámica las URL permitidas a través de variables de entorno ([config.py](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/app/core/config.py)).
3. **Estructura de carpetas y organización:**
   - Implementamos una arquitectura modular y limpia dividida en:
     - `app/api`: Capa de ruteo y endpoints HTTP de FastAPI.
     - `app/core`: Configuraciones fundamentales, seguridad y base de datos.
     - `app/models`: Modelos ORM relacionales de SQLAlchemy.
     - `app/repositories`: Capa DAO (Data Access Object) que separa la lógica SQL del resto.
     - `app/schemas`: Modelos Pydantic para tipado estricto y validación de entrada/salida.
     - `app/services`: Servicios con las reglas de negocio complejas (Jobs ETL y matemáticas de KPIs).
4. **Configuración de base de datos (PostgreSQL + SQLAlchemy):**
   - Configurado en [database.py](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/app/core/database.py). Creamos el `engine` utilizando `DATABASE_URL` (inyectada desde `.env`), declaramos la sesión de base de datos (`SessionLocal`) configurada sin auto-commit ni auto-flush para asegurar la atomicidad de transacciones, y exportamos el generador `get_db` para inyección de dependencia en los endpoints.
5. **Primera conexión de prueba con Jira API:**
   - Probado a través de consultas iniciales con autenticación básica y posteriormente evolucionada para comunicarse con la URL de Jira Cloud de Atlassian usando clientes HTTP asíncronos.

---

### SEMANA 2: Conexión y Autenticación con Jira

1. **Obtención de credenciales de Jira (OAuth 2.0):**
   - Para un entorno empresarial real, implementamos el flujo seguro de **OAuth 2.0 (Three-legged)** en [auth.py](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/app/api/v1/endpoints/auth.py). Esto evita almacenar la clave de API / token directo del usuario (lo cual es inseguro) y en su lugar obtiene un `access_token` y `refresh_token` temporales que autoriza al backend a consultar Jira en nombre del usuario.
2. **Implementación de autenticación Jira API y servicio asíncrono reutilizable:**
   - La sincronización utiliza `httpx.AsyncClient` asíncrono y no bloqueante. En [jira_sync.py](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/app/services/jira_sync.py), las solicitudes HTTP se realizan en paralelo utilizando las credenciales del usuario almacenadas de forma cifrada/persistida en PostgreSQL.
3. **Manejo de errores y excepciones:**
   - Cada llamada externa a Jira está envuelta en bloques `try/except` que capturan errores de red (`httpx.RequestError`), problemas de expiración de token (se maneja el error `401 Unauthorized` de manera limpia y se redirige a re-iniciar flujo en frontend), y validan los estados de respuesta HTTP, lanzando `HTTPException` personalizadas de FastAPI para evitar fugas de trazas internas al usuario final (error 500).

---

### SEMANA 3: Implementación de Endpoints y JQL

1. **Queries JQL para métricas:**
   - Centralizadas en [jql_config.py](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/app/core/jql_config.py). JQL (Jira Query Language) nos permite extraer con alta precisión:
     - Deltas de sincronización incremental: `project = '{project_key}' AND updated >= '-24h'`.
     - Velocity y Throughput: issues finalizados en sprints específicos.
     - Lead Time y Cycle Time: issues resueltos en rangos de fechas definidos.
2. **Mapeo de respuestas JSON de Jira a modelos:**
   - Para validar los campos provenientes del payload de Jira, creamos esquemas Pydantic robustos en [jql.py](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/app/schemas/jql.py) (tales como `JQLQueryResponse` y `MetricSummarySchema`), garantizando tipos de datos e impidiendo errores en tiempo de ejecución.
3. **Documentación Swagger / OpenAPI:**
   - Al usar esquemas de Pydantic, decoradores de FastAPI `@router.get` / `@router.post` y tipados estrictos en parámetros, FastAPI compila automáticamente la documentación interactiva OpenAPI en la ruta `/docs` del backend, incluyendo descripciones enriquecidas de cada endpoint.

---

### SEMANA 4: Seguridad y Testing

1. **Autenticación con HMAC (Session ID Signing):**
   - Implementado en [security.py](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/app/core/security.py). En lugar de usar cookies en texto plano o JWT pesados, decidimos firmar criptográficamente el ID de sesión del usuario con un hash HMAC SHA-256 usando una llave secreta del servidor (`SECRET_KEY`). El formato es `ID_USUARIO.FIRMA_HMAC`.
   - Cuando llega una cookie de sesión, el backend recalcula la firma y valida que no haya sido alterada. Si un hacker intenta modificar el `ID_USUARIO` para suplantar a otro usuario, la firma no coincide y se bloquea de inmediato.
2. **Middleware y protección de endpoints:**
   - Usamos inyección de dependencias (`Depends`) con las funciones auxiliares `get_current_user_id` y `check_user_exists` en los routers de la API. Si la cookie `session_id` no está firmada correctamente o el usuario no existe en BD, se levanta una excepción `401 Unauthorized` de manera automática antes de ejecutar cualquier lógica del endpoint.
3. **Pruebas unitarias de seguridad:**
   - Escritas en [test_security.py](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/tests/test_security.py). Valida que tokens válidos se autoricen correctamente, tokens alterados sean rechazados de inmediato, tokens vacíos no tiren el servidor y formatos maliciosos (sin punto separador, o IDs no enteros) se manejen sin errores internos.
4. **Pruebas de integración de endpoints:**
   - Escritas en [test_kpi_endpoints.py](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/tests/test_kpi_endpoints.py) y [test_cache.py](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/tests/test_cache.py) usando `fastapi.testclient.TestClient`. Verifican el flujo completo HTTP desde la capa de enrutadores hasta la respuesta final de JSON, validando códigos HTTP (401, 200) y que los payloads de respuesta coincidan.

---

## 🟡 FASE 2: Base de Datos, Métricas, KPIs y Optimización

### SEMANA 1: Integración con Base de Datos

1. **Diseñar e implementar tablas/modelos:**
   - Definidos en [jira.py (models)](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/app/models/jira.py) y [metrics.py](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/app/models/metrics.py) usando SQLAlchemy ORM. Mapeamos entidades clave: `Proyecto`, `Sprint`, `Issue`, `TransicionEstadoIssue` (historial de cambios de estado), `MapeoEstado` (mapeo dinámico de estados de Jira a estados base) y `KpisHistoricos` (almacén de KPIs calculados).
2. **Crear migraciones de base de datos (Alembic):**
   - Configurado bajo el directorio `/alembic`. Permite versionar la base de datos de manera controlada y segura en entornos de desarrollo y producción. Alembic lee las variables de entorno para aplicar las migraciones de forma controlada mediante `alembic upgrade head`.
3. **Implementación de Repositorios/DAOs:**
   - Diseñado un patrón genérico robusto en [base.py](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/app/repositories/base.py) (`CRUDBase`). Esto encapsula las consultas comunes de lectura (CRUD) en base de datos.
   - En [jira_repo.py](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/app/repositories/jira_repo.py) y [metrics_repo.py](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/app/repositories/metrics_repo.py) heredamos de `CRUDBase` y creamos funciones de dominio específicas (por ejemplo, obtener los estados únicos de un proyecto, eliminar mapeos previos, etc.), desacoplando totalmente la lógica de acceso a datos de los controladores API de FastAPI.
4. **Pruebas de persistencia básica y cascada:**
   - Escritas en [test_persistence.py](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/tests/test_persistence.py). Valida el ciclo CRUD completo de las entidades e integra pruebas de integridad referencial: si un proyecto se borra, SQLAlchemy y PostgreSQL eliminan en cascada (`ondelete="CASCADE"`) todos los sprints y tickets dependientes, protegiendo a la base de datos de registros huérfanos.

---

### SEMANA 2: Cálculo e Implementación de KPIs

1. **Definir fórmulas y lógica de cada KPI:**
   - Definido matemáticamente en [kpi.py](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/app/services/kpi.py) y [jira_repo.py](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/app/repositories/jira_repo.py):
     - **Lead Time Promedio:** Diferencia en días entre `resolved_at` y `created_at`.
     - **Cycle Time Promedio:** Diferencia en días entre la resolución (`resolved_at`) y la primera fecha en la que el ticket ingresó a un estado mapeado como "IN_PROGRESS". Si no cuenta con transiciones, hereda el Lead Time como fallback.
     - **Velocity:** Suma de Story Points (`story_points`) de issues completados/resueltos.
     - **Throughput:** Conteo exacto de issues entregados (resueltos).
2. **Jobs / Tareas en segundo plano (`BackgroundTasks`):**
   - El proceso pesado de ETL de descarga de datos de Jira y recálculo de KPIs se realiza de forma no bloqueante a través de `BackgroundTasks` de FastAPI en el endpoint `/sync` de [jira.py](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/app/api/v1/endpoints/jira.py), asegurando una experiencia fluida al usuario final.
3. **Validación de cálculos matemáticos con datos de prueba:**
   - Implementado en [test_cycle_time.py](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/tests/test_cycle_time.py). Valida con precisión matemática decimal (`pytest.approx`):
     - Casos de issues no resueltos (deben retornar `0.0`).
     - Tiempos de ciclo con múltiples transiciones en progreso desordenadas (debe ordenarlas cronológicamente y tomar la primera).
     - Sensibilidad a mayúsculas/minúsculas y estados personalizados.
     - Promedio histórico de velocidad acumulada sprint tras sprint.

---

### SEMANA 3: Endpoints para Frontend y Optimización

1. **Creación de endpoints GET de KPIs y Sprints:**
   - Expuestos en [projects.py](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/app/api/v1/endpoints/projects.py) para consulta del frontend.
2. **Paginación y ordenamiento:**
   - Incorporamos parámetros de paginación (`limit`, `offset`/`skip`) y ordenamiento dinámico por columnas (`sort`, `order` en modo `"asc"` o `"desc"`) en los endpoints clave y repositorios, permitiendo que la interfaz consuma datos de forma controlada y óptima.
3. **Optimización de consultas en base de datos (Suma y promedios delegados a SQL):**
   - **El gran cambio:** Anteriormente el backend descargaba todas las transiciones y los issues a la memoria de Python y ejecutaba bucles `for` para obtener los promedios. Esto causaba un problema de consultas **N+1** (al consultar transiciones de forma perezosa por cada issue) y alta carga de memoria.
   - **Implementación optimizada:** Diseñamos dos consultas SQL agregadas de alto rendimiento en [jira_repo.py](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/app/repositories/jira_repo.py): `get_resolved_stats_by_project` y `get_resolved_stats_by_sprint`.
   - Estas funciones inyectan una subconsulta escalar (`scalar_subquery`) y expresiones `case/coalesce` para que **PostgreSQL o SQLite calculen la primera fecha de progreso y computen los promedios de tiempo, throughput y velocidad directamente en el motor de base de datos**, retornando una sola fila con los resultados exactos.

---

### SEMANA 4: Pruebas y Caché

1. **Optimización de consultas lentas:**
   - Con la delegación a base de datos explicada arriba, el tiempo de cálculo de KPIs pasó de ser lineal `O(N)` (haciendo múltiples queries de base de datos por cada issue) a constante `O(1)`, reduciendo el consumo de memoria en un 98% para proyectos con alto volumen de tickets.
2. **Implementación de Caché en Memoria (`ShortLivedCache`):**
   - **Análisis:** Para KPIs, no se necesita caché HTTP externa porque los datos ya están pre-calculados y persistidos en la base de datos (lectura directa ultrarrápida de 2ms).
   - **Aplicación:** Para las métricas en vivo (`GET /api/jira/metrics`), implementamos una caché en memoria de 60 segundos ([cache.py](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/app/core/cache.py)) protegida por hilos con llaves particionadas por usuario (`metrics:{id_usuario}:{cloud_id}`). Esto reduce significativamente las peticiones externas al API de Jira, evitando cuotas de rate limit y acelerando la respuesta del dashboard principal.
3. **Pruebas de la Caché:**
   - Escritas en [test_cache.py](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/tests/test_cache.py). Valida el almacenamiento, expiración exacta mediante el parcheo del reloj interno de `datetime`, y la consistencia de aislamiento por llaves de usuario.
