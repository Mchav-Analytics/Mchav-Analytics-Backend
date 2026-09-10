# Diapositivas de Sustentación: MCHAV Analytics 📊💻

Este documento contiene el contenido de las diapositivas y el **guión detallado para el expositor** para presentar punto por punto los 7 temas clave de la agenda del proyecto MCHAV Analytics.

---

## 📑 Agenda de la Exposición

1. [Diapositiva 1: Arquitectura](#1-diapositiva-1-arquitectura)
2. [Diapositiva 2: Autenticación](#2-diapositiva-2-autenticación)
3. [Diapositiva 3: Consultas JQL](#3-diapositiva-3-consultas-jql)
4. [Diapositiva 4: Proceso de Sincronización](#4-diapositiva-4-proceso-de-sincronización)
5. [Diapositiva 5: Implementación de HMAC](#5-diapositiva-5-implementación-de-hmac)
6. [Diapositiva 6: Documentación de la API](#6-diapositiva-6-documentación-de-la-api)
7. [Diapositiva 7: Optimización](#7-diapositiva-7-optimización)
8. [Diapositiva 8: Conclusión y Preguntas](#8-diapositiva-8-conclusión-y-preguntas)

---

## 1. Diapositiva 1: Arquitectura

### 🎨 Contenido de la Diapositiva:
* **Patrón de Arquitectura:** Clean Architecture (Arquitectura Limpia) con desacoplamiento total de capas.
* **Estructura en Capas:**
  * ⚙️ **Core:** Configuración centralizada (`config.py`), conexión a BD (`database.py`), firmas de seguridad (`security.py`) y caché (`cache.py`).
  * 🔌 **Datasources:** Cliente HTTP asíncrono de bajo nivel para la API REST de Jira (`jira_datasource.py`).
  * 🗄️ **Models (ORM):** Entidades divididas por dominios (`auth.py`, `jira.py`, `metrics.py`).
  * 📦 **Repositories (DAO):** Repositorio genérico base (`base.py`) y repositorios especializados (`jira_repo.py`, `auth_repo.py`, `metrics_repo.py`).
  * 🧠 **Services:** Lógica de negocio aislada para OAuth (`auth_service.py`), motor ETL (`jira_sync_service.py`) y métricas/KPIs (`kpi.py`).
  * 🎮 **Controllers (API v1):** Controladores HTTP delgados con versión `/api/v1/`.

### 🗣️ Guión para el Expositor:
> *"Para garantizar que el sistema sea mantenible, escalable y fácil de probar, implementamos Clean Architecture. Esto significa que la base de datos, los controladores HTTP y la conexión con Jira están completamente desacoplados de la lógica de negocio. Si el día de mañana cambiamos de base de datos o de framework web, los algoritmos que calculan el Velocity, Throughput o Cycle Time no sufren ningún cambio."*

---

## 2. Diapositiva 2: Autenticación

### 🎨 Contenido de la Diapositiva:
* **Estándar OAuth 2.0 (3-Legged OAuth):**
  * Integración oficial con Atlassian (`authorization_code`, `refresh_token`, `cloud_id`).
  * Protección CSRF mediante tokens aleatorios únicos de un solo uso (`state`).
* **Estrategia Híbrida Dual de Autenticación:**
  * **OAuth 2.0:** Inicio de sesión transparente e interactivo para los usuarios.
  * **API Token Fallback (Basic Auth):** Extracción directa mediante API Token de administrador para evitar bloqueos por límite de peticiones (Rate Limit HTTP 429) de Atlassian.
* **Archivos Clave:** `app/services/auth_service.py`, `app/api/v1/controllers/auth_controller.py`.

### 🗣️ Guión para el Expositor:
> *"Nuestra autenticación cuenta con un enfoque híbrido de alta disponibilidad. Por un lado, soportamos OAuth 2.0 estándar de Atlassian para que los usuarios inicien sesión con su cuenta. Por otro lado, para el procesamiento masivo de datos implementamos un fallback automático por API Token. Esto garantiza que si Atlassian limita las peticiones de la app por Rate Limit (HTTP 429), la sincronización continúe operando sin caídas."*

---

## 3. Diapositiva 3: Consultas JQL

### 🎨 Contenido de la Diapositiva:
* **Contrato Centralizado de JQL (`app/core/jql_config.py`):**
  * Consultas parametrizadas y estandarizadas en un solo lugar.
  * **Extracción Delta:** Tickets modificados en las últimas 24 horas (`updated >= '-24h'`).
  * **Velocidad y Throughput:** Tickets en estado finalizado (`status = Done`) por sprint.
  * **Tiempos de Ciclo:** Tickets resueltos dentro de rangos de fechas definidos.
* **Soporte para Atlassian Change 2046:**
  * Estrategia de 3 niveles: Intenta `GET /search/jql`, luego `POST /search/jql` y finalmente fallback al endpoint legacy `GET /search`.
* **Archivos Clave:** `app/core/jql_config.py`, `app/datasources/jira_datasource.py`, `app/schemas/jql.py`.

### 🗣️ Guión para el Expositor:
> *"Todas las búsquedas contra Jira utilizan consultas JQL estandarizadas. Además, preparamos nuestro motor para el cambio reciente Atlassian Change 2046: el sistema intenta utilizar primero el nuevo endpoint recomendado `/search/jql` en GET o POST, y si el servidor responde con error, conmuta automáticamente al endpoint legacy sin interrumpir al usuario."*

---

## 4. Diapositiva 4: Proceso de Sincronización

### 🎨 Contenido de la Diapositiva:
* **Pipeline ETL (Extract, Transform, Load):**
  * **Extraer:** Proyectos, tableros, sprints, tickets e historial de transiciones (changelog) desde Jira.
  * **Transformar:** Validación estricta por `projectKey` en tableros para evitar fuga de datos entre proyectos.
  * **Cargar:** Persistencia en PostgreSQL y cálculo inmediato de KPIs.
* **Procesamiento Asíncrono No Bloqueante:**
  * Tareas en segundo plano (`BackgroundTasks`) con sesiones de base de datos independientes (`SessionLocal()`).
* **Auditoría Inmutable:**
  * Registro detallado en la tabla `logs_sincronizacion` (duración, tickets procesados, estado `SUCCESS`/`ERROR`, traceback de excepciones).
* **Archivos Clave:** `app/services/jira_sync_service.py`, `app/models/metrics.py`.

### 🗣️ Guión para el Expositor:
> *"El proceso de sincronización es un motor ETL asíncrono. Cuando el usuario hace clic en Sincronizar, la tarea se ejecuta en segundo plano sin congelar la pantalla. El motor extrae los tickets y todo el historial de cambios de estado para calcular los tiempos reales de desarrollo. Además, cada ejecución guarda un log de auditoría completo con el tiempo empleado y cualquier eventual error."*

---

## 5. Diapositiva 5: Implementación de HMAC

### 🎨 Contenido de la Diapositiva:
* **Firma Criptográfica de Sesión (HMAC SHA-256):**
  * Cookies de sesión firmadas con formato `user_id.firma_hex`.
  * Imposibilidad de alterar o falsificar IDs de usuario en el cliente.
* **Atributos de Máxima Seguridad en Cookies:**
  * **`HTTP-Only`:** Inmune a robos de sesión por scripts XSS (JavaScript del navegador no puede leer la cookie).
  * **`SameSite=Lax`:** Protección activa contra ataques de falsificación de petición (CSRF).
* **Defensa contra Timing Attacks:**
  * Verificación mediante `hmac.compare_digest` en tiempo constante.
* **Guardias de Inyección de Dependencias:**
  * Protecciones `get_current_user_id()` y `check_user_exists()` en `app/api/v1/deps.py`.

### 🗣️ Guión para el Expositor:
> *"En materia de seguridad, evitamos guardar tokens en localStorage debido al riesgo de vulnerabilidades XSS. En su lugar, utilizamos cookies de sesión HTTP-Only firmadas criptográficamente con HMAC SHA-256. La cookie no puede ser leída por ningún código JavaScript inyectado, y cualquier intento de alterar el ID de usuario invalida la firma de inmediato en el servidor."*

---

## 6. Diapositiva 6: Documentación de la API

### 🎨 Contenido de la Diapositiva:
* **Ocultamiento de Rutas Públicas:**
  * Desactivación explícita de `/docs`, `/redoc` y `/openapi.json` sin autenticación.
* **Protección con HTTP Basic Auth:**
  * Acceso restringido por usuario y contraseña mediante `HTTPBasic` configurados en `.env` (`DOCS_USER` / `DOCS_PASSWORD`).
* **Estándar OpenAPI 3.0:**
  * Interfaces interactivas de Swagger UI con validación de esquemas DTO de Pydantic.
  * Versionamiento estructurado bajo el prefijo `/api/v1/`.
* **Archivos Clave:** `app/main.py`.

### 🗣️ Guión para el Expositor:
> *"Para evitar que usuarios no autorizados o scanners de seguridad exploren nuestra API en producción, ocultamos las rutas públicas por defecto de FastAPI. La documentación interactiva de Swagger UI está protegida detrás de una capa de autenticación HTTP Basic Auth, exigiendo credenciales administradoras para visualizar el mapa de endpoints."*

---

## 7. Diapositiva 7: Optimización

### 🎨 Contenido de la Diapositiva:
* **Caché en Memoria (`ShortLivedCache`):**
  * Almacenamiento thread-safe con expiración TTL de 60 segundos para evitar consultas redundantes a la API de Jira.
* **Agregaciones Matemáticas a Nivel de Motor SQL:**
  * Delegación del cálculo de Velocity, Throughput, Lead Time y Cycle Time a la base de datos mediante `func.sum`, `func.avg` y cláusulas `case`.
  * Rendimiento óptimo sin procesamiento pesado en memoria de Python.
* **Suite de Pruebas Automatizadas (`pytest`):**
  * **28 pruebas unitarias y de integración pasadas exitosamente (100% éxito)**.
* **Archivos Clave:** `app/core/cache.py`, `app/repositories/jira_repo.py`, `tests/`.

### 🗣️ Guión para el Expositor:
> *"Optimizamos el rendimiento del sistema en dos niveles: implementamos una caché en memoria de 60 segundos para respuestas instantáneas de métricas y delegamos todos los cálculos matemáticos pesados directamente al motor de base de datos PostgreSQL. Por último, la estabilidad del sistema está garantizada por una suite de 28 pruebas automatizadas ejecutadas con un 100% de éxito."*

---

## 8. Diapositiva 8: Conclusión y Preguntas

```text
================================================================================
                           ¡GRACIAS POR SU ATENCIÓN!
                           MCHAV Analytics - v1.0
================================================================================
  - Repositorio GitHub: Ramas 'main' y 'Mike' 100% Sincronizadas
  - Documentación Técnica: /docs (Guías completas de entregables y seguridad)
  - Pruebas Automatizadas: 28/28 Pruebas Pasadas Exitósamente ✅

¿Preguntas o comentarios?
```
