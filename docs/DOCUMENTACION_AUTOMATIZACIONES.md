# ⚙️ Guía Maestra de Automatizaciones de la Plataforma MCHAV Analytics

Este documento consolida y describe en detalle **todas las automatizaciones** implementadas en el sistema MCHAV Analytics: su propósito de negocio, los archivos de código fuente donde residen, su flujo de ejecución paso a paso, sus mecanismos de resiliencia y cómo se operan o monitorean.

---

## 📑 Tabla de Contenidos
1. [Arquitectura General de Automatizaciones](#1-arquitectura-general-de-automatizaciones)
2. [Automatización 1: Planificador de Tareas en Segundo Plano (Cron Scheduler)](#2-automatización-1-planificador-de-tareas-en-segundo-plano-cron-scheduler)
3. [Automatización 2: Motor de Ingesta y Sincronización Incremental con Jira](#3-automatización-2-motor-de-ingesta-y-sincronización-incremental-con-jira)
4. [Automatización 3: Motor de Alertas Inteligentes y Detección de Bloqueos (NubiAlerts)](#4-automatización-3-motor-de-alertas-inteligentes-y-detección-de-bloqueos-nubialerts)
5. [Automatización 4: Motor de Análisis y Recomendaciones con IA (Nubi AI / Gemini)](#5-automatización-4-motor-de-análisis-y-recomendaciones-con-ia-nubi-ai--gemini)
6. [Automatización 5: Despacho Automático de Reportes Mensuales por Correo Electrónico](#6-automatización-5-despacho-automático-de-reportes-mensuales-por-correo-electrónico)
7. [Automatización 6: Automatizaciones de Interfaz y Sincronización en Tiempo Real (Frontend)](#7-automatización-6-automatizaciones-de-interfaz-y-sincronización-en-tiempo-real-frontend)
8. [Automatización 7: Automatizaciones de Infraestructura, Base de Datos y Despliegue](#8-automatización-7-automatizaciones-de-infraestructura-base-de-datos-y-despliegue)
9. [Matriz Resumen de Archivos, Triggers y Responsabilidades](#9-matriz-resumen-de-archivos-triggers-y-responsabilidades)

---

## 1. Arquitectura General de Automatizaciones

La plataforma MCHAV Analytics utiliza una arquitectura orientada a procesos en segundo plano (*Background Workers* y *Scheduled Jobs*) con ejecución asíncrona no bloqueante:

```
                  ┌────────────────────────────────────────┐
                  │          APScheduler Daemon            │
                  │       (app/core/scheduler.py)          │
                  └───────┬────────────────────────┬───────┘
                          │                        │
         Diario a las 02:00 AM          1° de cada mes a las 08:00 AM
                          │                        │
                          ▼                        ▼
           ┌───────────────────────────┐   ┌───────────────────────────┐
           │ Sincronización Jira       │   │ Despachador de Reportes   │
           │ (jira_sync_service.py)    │   │ (monthly_report_...py)    │
           └──────────────┬────────────┘   └─────────────┬─────────────┘
                          │                              │
                          ▼                              ▼
           ┌───────────────────────────┐   ┌───────────────────────────┐
           │ Normalizador & Base Datos │   │ Gemini AI Analysis        │
           │ (jira_normalizer.py)      │   │ + Generación PDF          │
           └──────────────┬────────────┘   └─────────────┬─────────────┘
                          │                              │
                          ▼                              ▼
           ┌───────────────────────────┐   ┌───────────────────────────┐
           │ Motor de Alertas          │   │ Envío SMTP por Correo     │
           │ (alerts_engine_service.py)│   │ (email_service.py)        │
           └───────────────────────────┘   └───────────────────────────┘
```

---

## 2. Automatización 1: Planificador de Tareas en Segundo Plano (Cron Scheduler)

### 📍 Ubicación en el Código:
- **Archivo principal:** [`Mchav-Backend/app/core/scheduler.py`](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/app/core/scheduler.py)
- **Inicialización:** [`Mchav-Backend/app/main.py`](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/app/main.py) (función `lifespan`)
- **Controlador API:** [`Mchav-Backend/app/api/v1/controllers/automation_controller.py`](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/app/api/v1/controllers/automation_controller.py)

### ⚙️ ¿Cómo funciona?
1. Al arrancar FastAPI, el gestor de ciclo de vida (`lifespan`) invoca `start_scheduler()`.
2. Se instancia un `BackgroundScheduler(daemon=True)` de **APScheduler** que corre en un hilo independiente de Python.
3. Se registran dos tareas cron recurrentes:
   - **`automatic_jira_sync`**: Programada diariamente a las **02:00 AM** (`CronTrigger(hour=2, minute=0)`).
   - **`automatic_monthly_reports`**: Programada el **primer día de cada mes a las 08:00 AM** (`CronTrigger(day=1, hour=8, minute=0)`).
4. **Mecanismo de Bloqueo Distribuido (Distributed Lock):**
   Antes de iniciar la sincronización, el job consulta `log_repo.has_running_sync(db)`. Si ya existe una sincronización en estado `RUNNING` (ej. disparada manualmente o corriendo en otra réplica), el job se cancela de inmediato para evitar colisiones en la base de datos o duplicación de llamadas a Jira.
5. Al apagar el servidor, `stop_scheduler()` finaliza el planificador de forma limpia sin corromper tareas.

---

## 3. Automatización 2: Motor de Ingesta y Sincronización Incremental con Jira

### 📍 Ubicación en el Código:
- **Servicio principal:** [`Mchav-Backend/app/services/jira_sync_service.py`](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/app/services/jira_sync_service.py)
- **Normalizador de estados:** [`Mchav-Backend/app/services/jira_normalizer.py`](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/app/services/jira_normalizer.py)
- **Orquestador asíncrono:** [`Mchav-Backend/app/services/jira_sync.py`](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/app/services/jira_sync.py)
- **Registro de auditoría:** [`Mchav-Backend/app/repositories/sync_log_repo.py`](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/app/repositories/sync_log_repo.py)

### ⚙️ ¿Cómo funciona?
1. **Detección de modo y credenciales:**
   - Valida si el usuario tiene sesión OAuth 2.0 activa con token de acceso y refresco.
   - Si no o si expiró, activa el **fallback transparente** a las credenciales cifradas con Fernet (API Token de Jira).
2. **Sincronización Incremental:**
   - Consulta la marca de tiempo de la última sincronización exitosa (`last_sync_at`).
   - Construye una consulta JQL optimizada: `updated >= "YYYY-MM-DD HH:MM" ORDER BY updated ASC`.
   - Si es la primera vez, realiza una carga completa paginada en bloques de 50 o 100 issues.
3. **Normalización Inteligente de Estados y Tipos (`jira_normalizer.py`):**
   - Transforma los estados propios de cada tablero de Jira a las 4 categorías analíticas de flujo:
     - `To Do` (Backlog, Por hacer, Open, Nuevo)
     - `In Progress` (En progreso, In Dev, Coding)
     - `In Review` (En revisión, Code Review, QA, Testing)
     - `Done` (Cerrado, Resuelto, Finalizado)
   - Extrae campos clave: `issue_type` (Story, Bug, Task, Epic), `priority`, `story_points`, `assignee`, `changelog` (historial de transiciones de estados para calcular Lead Time y Cycle Time exactos).
4. **Resiliencia ante Rate Limits de Atlassian:**
   - Si Atlassian responde con `HTTP 429 Too Many Requests`, el motor captura la cabecera `Retry-After` y aplica **Retroceso Exponencial con Jitter (Backoff)** reintentando automáticamente hasta 3 veces.
5. **Auditoría:**
   - Registra en la tabla `sync_logs` el estado final (`SUCCESS`, `FAILED`), la duración en milisegundos, el número de issues actualizados y el mensaje de error si aplica.

---

## 4. Automatización 3: Motor de Alertas Inteligentes y Detección de Bloqueos (NubiAlerts)

### 📍 Ubicación en el Código:
- **Motor analítico:** [`Mchav-Backend/app/services/alerts_engine_service.py`](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/app/services/alerts_engine_service.py)
- **Controlador API:** [`Mchav-Backend/app/api/v1/controllers/alerts_controller.py`](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/app/api/v1/controllers/alerts_controller.py)
- **Cálculo de tiempos:** [`Mchav-Backend/app/services/kpi.py`](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/app/services/kpi.py)

### ⚙️ ¿Cómo funciona?
Cada vez que finaliza una sincronización de Jira (o cuando se consulta el panel de alertas), el motor ejecuta `scan_and_generate_alerts()` sobre la base de datos real:

1. **Detección de Tareas Estancadas / Bloqueos (> 48h):**
   - Evalúa cada issue no resuelto en estado `In Progress` o `In Review`.
   - Calcula `get_issue_active_days()` comparando la última transición de estado contra `datetime.now(timezone.utc)`.
   - Si la tarea lleva más de **2 días (48 horas)** sin cambios, genera una alerta de severidad **ALTA**.
2. **Detección de Sobrecarga de WIP (Work In Progress):**
   - Agrupa los issues activos por desarrollador asignado (`assignee_id`).
   - Si un desarrollador tiene **más de 3 tareas activas en paralelo**, se genera una alerta preventiva de riesgo de cuello de botella y sobrecarga.
3. **Detección de Desviación Severa de Cycle Time:**
   - Calcula el Cycle Time promedio histórico del proyecto.
   - Si una tarea activa supera el **doble del promedio del proyecto**, genera una alerta de desviación de entrega.
4. **Ciclo de Vida y Persistencia:**
   - Las alertas se guardan en la tabla `alertas_sistema`.
   - Los líderes técnicos pueden marcarlas como `PENDIENTE`, `EN_PROCESO` o `RESUELTO`, y dejar comentarios bidireccionales.

---

## 5. Automatización 4: Motor de Análisis y Recomendaciones con IA (Nubi AI / Gemini)

### 📍 Ubicación en el Código:
- **Servicio Gemini:** [`Mchav-Backend/app/services/gemini_service.py`](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/app/services/gemini_service.py)
- **Controlador API:** [`Mchav-Backend/app/api/v1/controllers/ai_controller.py`](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/app/api/v1/controllers/ai_controller.py)
- **Configuración de clave:** `.env` (`GEMINI_API_KEY`)

### ⚙️ ¿Cómo funciona?
1. **Extracción y Consolidación de Contexto:**
   - El backend recopila métricas agregadas reales: Lead Time, Cycle Time percentil 85 (P85), Throughput semanal, índice de retrabajo (Bugs vs Stories) y salud del Sprint.
2. **Ingeniería de Prompts y LLM:**
   - Se alimenta al modelo **Google Gemini** con un System Prompt especializado como experto en metodologías ágiles y analítica de entrega de software.
3. **Generación Automatizada:**
   - **Análisis Ejecutivo:** Diagnóstico del estado del proyecto en prosa clara.
   - **Detección de Riesgos:** Identificación de cuellos de botella y miembros con sobrecarga.
   - **Recomendaciones Accionables:** 3 a 5 acciones puntuales para el Líder Técnico o Scrum Master.
4. **Cache y Fallback Inteligente:**
   - Si la API Key no está configurada o se produce un fallo de red hacia los servidores de Google, el servicio cuenta con un generador determinístico basado en reglas de negocio para no interrumpir el flujo.

---

## 6. Automatización 5: Despacho Automático de Reportes Mensuales por Correo Electrónico

### 📍 Ubicación en el Código:
- **Despachador mensual:** [`Mchav-Backend/app/services/monthly_report_dispatcher_service.py`](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/app/services/monthly_report_dispatcher_service.py)
- **Servicio SMTP:** [`Mchav-Backend/app/services/email_service.py`](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/app/services/email_service.py)
- **Generador de Reportes PDF:** [`Mchav-Backend/app/services/report_service.py`](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/app/services/report_service.py)

### ⚙️ ¿Cómo funciona?
El día 1 de cada mes a las 08:00 AM, el job `scheduled_monthly_reports_job` ejecuta la siguiente secuencia automática:

1. **Segmentación de Destinatarios por Rol:**
   - Consulta a los usuarios con rol **Administrador** y **Líder Técnico**.
2. **Generación del Reporte PDF en Memoria:**
   - Invoca a `generate_pdf_report_bytes()`.
   - Incluye gráficos de rendimiento, distribución de tiempos, métricas de calidad y la síntesis generada por Nubi AI.
   - El PDF se compila en un buffer de memoria (`io.BytesIO`) sin necesidad de guardar archivos temporales en el disco.
3. **Construcción del Correo HTML:**
   - Utiliza plantillas responsivas (`_build_admin_email_html` y `_build_leader_email_html`).
4. **Envío Seguro:**
   - Conecta vía SMTP con cifrado TLS y envía el correo con el PDF adjunto (`reporte_mensual_YYYY_MM.pdf`).
   - Registra en logs el éxito o error de cada envío.

---

## 7. Automatización 6: Automatizaciones de Interfaz y Sincronización en Tiempo Real (Frontend)

### 📍 Ubicación en el Código:
- **Hook de Sincronización:** [`Mchav-Frontend/src/features/sync/hooks/useSystemSync.ts`](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Frontend/src/features/sync/hooks/useSystemSync.ts)
- **Panel de Control de Sincronización:** [`Mchav-Frontend/src/features/sync/components/SystemSyncControlPanel.tsx`](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Frontend/src/features/sync/components/SystemSyncControlPanel.tsx)
- **Visor de Logs en Vivo:** [`Mchav-Frontend/src/features/sync/components/SyncLogsViewer.tsx`](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Frontend/src/features/sync/components/SyncLogsViewer.tsx)
- **Generador de Reportes React-to-Print:** [`Mchav-Frontend/src/features/reports/views/CentroReportesView.jsx`](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Frontend/src/features/reports/views/CentroReportesView.jsx)

### ⚙️ ¿Cómo funciona?
1. **Polling Asíncrono de Estado:**
   - Cuando el usuario presiona *"Sincronizar Manualmente Ahora"*, el hook `useSystemSync` envía la petición `POST /api/v1/sync/run` y entra en un bucle de sondeo (polling cada 2 segundos) consultando el estado de la tarea.
2. **Actualización Reactiva de la UI:**
   - Muestra el estado activo (*"Sincronizando..."* con animación giratoria).
   - Al finalizar, recarga automáticamente los logs y refresca las tarjetas de métricas en el Dashboard sin obligar al usuario a recargar la página (`F5`).
3. **Autocompletado y Validación JQL en Vivo:**
   - Componente `JqlEditor.jsx` valida en tiempo real la sintaxis de consultas contra la API del backend.

---

## 8. Automatización 7: Automatizaciones de Infraestructura, Base de Datos y Despliegue

### 📍 Ubicación en el Código:
- **Orquestador:** [`docker-compose.yml`](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/docker-compose.yml)
- **Migraciones Alembic:** [`Mchav-Backend/alembic/`](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/alembic)
- **Arranque del Backend:** Línea de comando en `docker-compose.yml`:
  ```bash
  sh -c "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"
  ```
- **Certificados SSL Automáticos:** [`Mchav-Frontend/Dockerfile`](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Frontend/Dockerfile)

### ⚙️ ¿Cómo funciona?
1. **Migración Automática de Esquema:**
   Al encender el contenedor `mchav_backend`, antes de levantar el servidor web Uvicorn, ejecuta automáticamente `alembic upgrade head`. Si hay nuevas tablas o columnas, la base de datos se actualiza sin intervención manual.
2. **Poblado Inicial (Data Seeding) Automático:**
   En [`Mchav-Backend/app/main.py`](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/app/main.py), la función de inicio verifica si existen los roles predeterminados (`Administrador`, `Líder Técnico`, `Desarrollador`, `Usuario`). Si no existen, los crea automáticamente.
3. **Generación Automática de Certificados SSL:**
   El `Dockerfile` de Frontend genera un certificado SSL autofirmado de respaldo con `openssl` para que Nginx siempre arranque sin fallos en el puerto `443 (HTTPS)`.

---

## 9. Matriz Resumen de Archivos, Triggers y Responsabilidades

| Automatización | Archivo Clave | Disparador (Trigger) | Frecuencia / Condición | Resultado / Acción |
|---|---|---|---|---|
| **Sincronización Diaria Jira** | `app/core/scheduler.py` | APScheduler Cron | Todos los días a las **02:00 AM** | Descarga tareas modificadas de Jira y actualiza la BD. |
| **Sincronización Manual** | `app/api/v1/controllers/sync_controller.py` | Botón en el Frontend (`POST /api/v1/sync/run`) | A demanda del usuario | Inicia ingesta inmediata en segundo plano con bloqueo anti-colisión. |
| **Despacho Mensual de Reportes** | `app/services/monthly_report_dispatcher_service.py` | APScheduler Cron | **1° de cada mes a las 08:00 AM** | Genera PDFs con IA y los envía por correo SMTP a Admins y Líderes. |
| **Detección de Cuellos de Botella** | `app/services/alerts_engine_service.py` | Post-sincronización o consulta de alertas | Automático | Detecta tareas estancadas >48h y exceso de WIP (>3 tareas/dev). |
| **Análisis IA con Gemini** | `app/services/gemini_service.py` | Post-sincronización o botón *"Generar con IA"* | A demanda o por Cron mensual | Diagnósticos en lenguaje natural, riesgos y recomendaciones. |
| **Migración de Base de Datos** | `docker-compose.yml` (`alembic upgrade head`) | Arranque del contenedor Backend | En cada despliegue / reinicio | Sincroniza el esquema relacional de PostgreSQL automáticamente. |
| **Seeding de Roles y Permisos** | `app/main.py` (`lifespan`) | Arranque de FastAPI | En cada inicio | Garantiza la existencia de roles base (`Administrador`, `Usuario`, etc.). |
| **Mapeo Dinámico de Redirección** | `Mchav-Frontend/src/services/api.js` | Detección de `window.location.hostname` | En tiempo de ejecución en el navegador | Rutea peticiones al proxy Nginx en producción y a localhost en local. |
