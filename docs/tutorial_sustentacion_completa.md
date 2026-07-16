# Guía Didáctica y Sustentación Pedagógica del Backend - MCHAV Analytics

¡Bienvenido! Este documento ha sido diseñado como un material educativo detallado (paso a paso), redactado desde la perspectiva de un profesor de desarrollo de software. El objetivo es que comprendas a la perfección cómo funciona cada engranaje del backend, por qué tomamos ciertas decisiones de diseño y cómo defender técnicamente el proyecto ante cualquier comité o evaluación.

---

## 🧭 Introducción al Sistema: ¿Qué es MCHAV Analytics?

MCHAV Analytics es una plataforma web para la visualización de métricas de rendimiento de proyectos gestionados en **Jira Cloud**. 
Su backend está desarrollado con **FastAPI** (Python) y utiliza una base de datos relacional (**PostgreSQL** en producción, **SQLite** en pruebas) a través de **SQLAlchemy** (ORM).

### La Arquitectura por Capas (Separación de Responsabilidades)

Para que el código no sea un caos ("código espagueti"), organizamos el backend en capas separadas. Imagina que el backend es un restaurante:
1. **La Capa de API (Enrutadores / Controllers):** Son los meseros. Reciben la orden del cliente (las peticiones HTTP del navegador), llaman a la cocina (servicios) y le devuelven el plato al cliente (JSON).
   - Ubicación: [app/api/v1/endpoints/](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/app/api/v1/endpoints/)
2. **La Capa de Servicios (Lógica de Negocio):** Es el chef. Aquí se procesan las recetas complejas: cálculos matemáticos de KPIs, conexiones a Jira y tareas pesadas.
   - Ubicación: [app/services/](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/app/services/)
3. **La Capa de Modelos (Base de Datos):** Es el almacén de ingredientes. Define cómo se estructuran las tablas en la base de datos PostgreSQL.
   - Ubicación: [app/models/](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/app/models/)
4. **La Capa de Repositorios (DAO - Data Access Object):** Es el encargado de inventario. Es el único que interactúa directamente con la base de datos (haciendo SELECT, INSERT, UPDATE, DELETE). Los servicios no le hablan directo a la BD; le piden datos al repositorio.
   - Ubicación: [app/repositories/](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/app/repositories/)
5. **La Capa de Schemas (Pydantic):** Es el control de calidad. Define plantillas estrictas de entrada y salida para que los datos que viajan por HTTP tengan el formato correcto (ej: que un correo sea un correo válido, que un id sea texto, etc.).
   - Ubicación: [app/schemas/](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/app/schemas/)

---

## 🔌 1. Conexión Externa y Motor de Sincronización (ETL)

### ¿Cómo nos conectamos a Jira de forma segura? (OAuth 2.0)
En lugar de pedirle al usuario su contraseña de Jira o una clave API (lo cual sería un peligro de seguridad si alguien vulnera nuestra base de datos), implementamos **OAuth 2.0**.
- Cuando el usuario hace clic en "Conectar con Jira", nuestro backend lo redirige a la página oficial de Atlassian (Jira).
- El usuario inicia sesión allí y autoriza a nuestra aplicación.
- Atlassian redirige de vuelta a nuestro backend con un código temporal.
- En [auth.py](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/app/api/v1/endpoints/auth.py), intercambiamos ese código por un `access_token` (clave temporal de acceso) y un `refresh_token` (para renovar el token automáticamente sin volver a pedir contraseña).

### ¿Cómo descargamos datos pesados sin congelar la aplicación? (Background Tasks)
Descargar el historial completo de cientos de tickets de Jira y sus transiciones de estado toma tiempo (segundos o minutos). Si hiciéramos esto dentro de una petición HTTP estándar, la página del navegador se quedaría cargando (congelada) y daría error de tiempo de espera (Timeout).

Para solucionarlo, usamos **BackgroundTasks** de FastAPI en [jira.py (endpoints)](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/app/api/v1/endpoints/jira.py):
```python
@router.post("/sync")
async def trigger_jira_sync(request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    ...
    # Registramos la tarea en segundo plano y el endpoint responde inmediatamente
    background_tasks.add_task(run_jira_sync_task, user.id_usuario)
    return {"message": "Sincronización iniciada en segundo plano"}
```
FastAPI recibe la petición, le dice al sistema operativo: *"Corre `run_jira_sync_task` en segundo plano"* y de inmediato le devuelve un mensaje al frontend diciendo *"Listo, ya empecé"*. El usuario puede seguir usando la aplicación mientras el motor descarga los datos en silencio.

---

## 📐 2. La Matemática de los KPIs de Rendimiento

El backend mide la eficiencia del equipo mediante métricas ágiles estándar:

### Lead Time y Cycle Time (Explicados con una analogía)
Imagina que vas a una pizzería:
- **Lead Time (Tiempo de Entrega):** Es el tiempo total desde que haces la orden (el ticket se crea) hasta que te entregan la pizza en tu mesa (el ticket se resuelve).
  - *Fórmula:* `Fecha de Resolución - Fecha de Creación`
- **Cycle Time (Tiempo de Ciclo):** Es el tiempo que el chef estuvo cocinando activamente la pizza (el ticket entra a un estado "En Desarrollo" o "In Progress") hasta que se sirve en tu mesa. No incluye el tiempo que estuviste esperando en la fila antes de que empezaran tu orden.
  - *Fórmula:* `Fecha de Resolución - Primera Fecha en Progreso`

### ¿Cómo identifica el backend la "Primera Fecha en Progreso"?
En Jira, los estados varían según el proyecto (ej: "Desarrollo", "Doing", "En progreso"). En [kpi.py](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/app/services/kpi.py) implementamos una lógica robusta:
1. Extraemos las transiciones de estado del ticket (`issue.transiciones`), las cuales representan cada vez que se movió el ticket (ej. de "To Do" a "In Progress").
2. Ordenamos cronológicamente esas transiciones por su fecha.
3. Buscamos la primera transición cuyo estado coincida con los estados mapeados como progreso (`in_progress_statuses`).
4. Si la encontramos, el cálculo se hace desde esa fecha. Si el ticket pasó directo de "To Do" a "Done" sin pasar por desarrollo, aplicamos un **fallback** y calculamos el tiempo usando la fecha de creación del ticket.

---

## ⚡ 3. La Gran Optimización: Delegación de Cálculos a SQL

### El Problema Inicial: Procesamiento en Memoria (N+1 Queries)
Inicialmente, para calcular el Lead Time y Cycle Time promedio de un proyecto, el código hacía esto en Python:
1. Traía todos los issues resueltos a la memoria de Python (`all_project_issues`).
2. Por cada issue, accedía a `issue.transiciones` para buscar la fecha de progreso. Como SQLAlchemy carga los datos relacionados de forma perezosa (lazy loading), **cada ticket generaba una consulta SELECT extra a la base de datos**. Si había 500 tickets, el servidor hacía 501 consultas. Esto se conoce como el problema **N+1**.
3. Se calculaban los promedios haciendo sumas de listas en la memoria RAM del servidor web.

Si el proyecto crecía a miles de tickets, el servidor web consumía demasiada memoria y las consultas tardaban varios segundos en cargar.

### La Solución: Consultas Agregadas Directas en SQL
Refactorizamos esta lógica moviendo todo el cálculo matemático al motor de base de datos relacional en [jira_repo.py](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/app/repositories/jira_repo.py):

```python
# Subconsulta para obtener la primera fecha de cambio de estado a "In Progress"
first_progress_date_sub = select(
    func.min(TransicionEstadoIssue.fecha_cambio)
).where(
    TransicionEstadoIssue.id_jira == Issue.id_jira,
    func.lower(TransicionEstadoIssue.estado_nuevo).in_(list(in_progress_statuses))
).scalar_subquery()
```

Esta subconsulta busca el valor mínimo (la fecha más antigua) en la tabla de transiciones donde el ID coincida y el estado nuevo esté dentro de los mapeados como progreso.

Luego, hacemos una única consulta agregada:
```python
return db.query(
    func.coalesce(func.sum(Issue.story_points), 0.0),
    func.count(Issue.id_jira),
    func.coalesce(func.avg(lead_time_clipped), 0.0),
    func.coalesce(func.avg(cycle_time_clipped), 0.0)
).filter(...)
```
- **`func.coalesce(val, default)`:** Si no hay datos (retorna Null), lo convierte a `0.0`. Evita errores por valores nulos.
- **`func.sum` y `func.avg`:** Calculan la suma de Story Points (Velocity) y los promedios de tiempo directamente en PostgreSQL en microsegundos, devolviendo un solo registro al servidor Python.
- **Diferencia de Dialectos:** Como en producción usamos PostgreSQL pero en pruebas unitarias usamos SQLite en memoria, el código detecta el motor de base de datos (`db.bind.dialect.name`) y genera la sintaxis adecuada:
  - En PostgreSQL usa: `func.extract('epoch', resolved - created) / 86400.0` (convierte el intervalo a segundos y lo divide para obtener días).
  - En SQLite usa: `func.julianday(resolved) - func.julianday(created)` (obtiene el día juliano directo como flotante).

---

## 🔒 4. Seguridad de Datos con Firmado HMAC

### ¿Por qué HMAC en lugar de cookies en texto plano?
Si guardamos el ID del usuario en una cookie simple (ej. `session_id=5`), cualquier usuario malicioso podría abrir las herramientas de desarrollo del navegador, cambiar el valor a `session_id=6` y acceder a los proyectos y tokens de otro usuario de forma ilegal. Esto es una vulnerabilidad crítica llamada **IDOR** (Insecure Direct Object Reference).

Para prevenirlo, implementamos **Session ID Signing con HMAC SHA-256** en [security.py](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/app/core/security.py):
1. **Firma:** Cuando el usuario inicia sesión con éxito, tomamos su ID (ej. `5`) y generamos una firma digital usando una clave secreta guardada únicamente en el servidor (`SECRET_KEY`):
   $$\text{Firma} = \text{HMAC-SHA256}(\text{ID}, \text{SECRET\_KEY})$$
2. **Estructura de la Cookie:** Guardamos el valor como `5.hash_de_64_caracteres`.
3. **Verificación:** Cuando el usuario hace una petición, nuestro backend lee la cookie. Separa el ID (`5`) de la firma recibida. Vuelve a calcular el HMAC del ID usando la clave secreta y compara el resultado con la firma recibida.
   - Si un hacker altera el ID a `6` pero deja la firma del `5`, las firmas no coinciden y el servidor le deniega el acceso (`401 Unauthorized`).
   - El hacker no puede adivinar la firma del `6` porque no conoce la clave secreta del servidor.

---

## 📦 5. Paginación y Caché en Memoria

### Paginación (`limit` y `offset`)
Para evitar enviar miles de registros de golpe al frontend (lo cual consumiría mucho ancho de banda y ralentizaría el navegador), añadimos paginación basada en compensación (Offset Pagination):
- **`limit`:** Número de registros que deseamos recibir por página (ej. 20).
- **`offset`/`skip`:** Número de registros que queremos omitir desde el inicio (ej. si estamos en la página 3 y limit es 20, omitimos 40).
Esto se aplica directamente en las consultas mediante `.offset(skip).limit(limit)`.

### Short-Lived Cache (Caché en Memoria de Corto Ciclo)
Como el endpoint `GET /api/jira/metrics` realiza peticiones externas en vivo a Jira que toman más de un segundo, creamos una caché local rápida en memoria en [cache.py](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/app/core/cache.py).

#### Características técnicas clave:
1. **Seguridad frente a hilos (`threading.Lock`):** Como Python maneja concurrencia, utilizamos bloqueos mutuos (Locks). Esto asegura que si dos peticiones intentan leer/escribir en la caché al mismo milisegundo, no corrompan los datos en memoria del servidor web.
2. **Aislamiento por usuario:** La clave de caché es dinámica e incluye el id de usuario:
   `cache_key = f"metrics:{user.id_usuario}:{user.cloud_id}"`
   Esto garantiza que el usuario A jamás reciba del caché los datos del usuario B (fuga de información).
3. **TTL (Time To Live):** Los datos expiran automáticamente a los 60 segundos. Si el usuario refresca la página rápidamente, los datos se le sirven en **0 milisegundos**, protegiendo al API de Jira de saturación.

---

## 🧪 6. Estrategia de Testing (Pruebas Unitarias e Integración)

Implementamos una suite de **27 pruebas automatizadas** usando `pytest` dividida en:

1. **Pruebas de Seguridad ([test_security.py](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/tests/test_security.py)):**
   - Asegura que el cifrado y validación HMAC no tengan fallos.
2. **Pruebas Matemáticas de Cycle Time ([test_cycle_time.py](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/tests/test_cycle_time.py)):**
   - Valida cada uno de los casos extremos del cálculo de días de Cycle Time.
3. **Pruebas de Integración con Base de Datos SQLite en memoria (`test_resolved_stats_database_queries`):**
   - SQLite en memoria (`sqlite:///:memory:`) crea una base de datos temporal en la memoria RAM que se destruye al terminar la prueba.
   - Esto nos permite simular inserciones reales de proyectos, sprints, tickets y transiciones, y comprobar que las consultas complejas de agregación SQL compilen y devuelvan la matemática exacta sin alterar la base de datos real de desarrollo o producción.
4. **Pruebas de Endpoints ([test_kpi_endpoints.py](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/tests/test_kpi_endpoints.py) y [test_cache.py](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/tests/test_cache.py)):**
   - Simulan llamadas HTTP completas usando `TestClient`. Verifican el comportamiento del enrutador, cabeceras, manejo de cookies y respuestas esperadas de la API.
