# Documento de Arquitectura y Decisiones Técnicas del Proyecto 🏛️📘

Este documento registra de manera integral la **Arquitectura del Sistema**, el diseño de componentes, las decisiones tecnológicas adoptadas y las justificaciones de ingeniería para la plataforma **MCHAV Analytics**.

---

## 📑 Índice General
1. [Visión General de la Arquitectura](#1-visión-general-de-la-arquitectura)
2. [Patrón de Diseño: Clean Architecture (Backend)](#2-patrón-de-diseño-clean-architecture-backend)
3. [Diseño de Base de Datos y Modelo Entidad-Relación](#3-diseño-de-base-de-datos-y-modelo-entidad-relación)
4. [Estrategia de Seguridad y Autenticación](#4-estrategia-de-seguridad-y-autenticación)
5. [Estrategia de Extracción de Datos e Integración con Jira](#5-estrategia-de-extracción-de-datos-e-integración-con-jira)
6. [Arquitectura del Frontend (React SPA)](#6-arquitectura-del-frontend-react-spa)
7. [Rendimiento, Caché y Procesamiento Asíncrono](#7-rendimiento-caché-y-procesamiento-asíncrono)
8. [Despliegue Multi-Contenedor (Docker Compose)](#8-despliegue-multi-contenedor-docker-compose)

---

## 1. Visión General de la Arquitectura

**MCHAV Analytics** utiliza una arquitectura desacoplada basada en el modelo **API-First (REST) + Single Page Application (SPA)**:

```text
  [ Cliente Web / Navegador ]
             │
             │ HTTP (JSON / Cookies Firmadas)
             ▼
  [ Nginx Proxy Inverso ]
        │            │
        │ /          │ /api/
        ▼            ▼
  [ React SPA ]   [ FastAPI Backend (Python) ]
  (Frontend)      ├── Controllers (HTTP Routers & deps.py)
                  ├── Services (Casos de Uso, KPIs & ETL)
                  ├── Datasources (Jira API Client v3 /search/jql)
                  └── Repositories (SQLAlchemy ORM Repositories)
                         │
                         ▼
                  [ PostgreSQL 15 BD ]
```

### Justificación Tecnológica:
* **FastAPI (Python 3.12):** Elegido por su velocidad de ejecución asíncrona (`asyncio`), documentación interactiva Swagger nativa protegida por HTTP Basic Auth y validación estricta de esquemas DTO mediante Pydantic.
* **React + Vite (JavaScript):** Elegido por su rapidez de renderizado reactivo, modularidad de componentes y bundling optimizado con Vite.
* **PostgreSQL 15:** Base de datos relacional robusta seleccionada para almacenar el historial inmutable de auditoría, transiciones de estado y cálculo de KPIs.
* **Docker Compose:** Orquestación de contenedores para despliegues portables sin fricción en cualquier servidor.

---

## 2. Patrón de Diseño: Clean Architecture (Backend)

El Backend de FastAPI implementa **Clean Architecture** (Arquitectura Limpia), separando la infraestructura de la lógica de negocio a través de capas concéntricas:

```text
app/
├── core/                # ⚙️ INFRAESTRUCTURA: Conexión DB, .env, Hashing de Seguridad y Caché
├── datasources/         # 🔌 FUENTES DE DATOS: Cliente HTTP para Jira REST API v3 (/search/jql)
├── schemas/             # 📄 ESQUEMAS DTO: Validaciones Pydantic de entrada/salida
├── models/              # 🗄️ PERSISTENCIA ORM: Entidades relacionales SQLAlchemy
├── repositories/        # 📦 ACCESO A DATOS: Consultas SQL encapsuladas
├── services/            # 🧠 CASOS DE USO: Cálculo de Lead/Cycle Time, OAuth y Motor ETL
└── api/v1/
    ├── deps.py          # 🔑 DEPENDENCIAS: Inyección centralizada de sesión y usuario
    └── controllers/     # 🎮 CONTROLADORES HTTP: Enrutadores FastAPI
```

---

## 3. Diseño de Base de Datos y Modelo Entidad-Relación

La base de datos relacional en PostgreSQL está gestionada mediante **Alembic** para versionamiento de esquemas y auto-migraciones de arranque (`startup_event` en `main.py`).

### Modelos de Entidad Principales:

1. **`usuarios` (`User`):** Registra los usuarios del sistema, credenciales Atlassian (`cloud_id`, `jira_account_id`), tokens de acceso y API Token personal.
2. **`roles` (`Role`):** Control de acceso basado en roles (`Administrador`, `Analista`, `Líder`).
3. **`proyectos` (`Proyecto`):** Mapeo de proyectos sincronizados (`key_proyecto`, `nombre`, `id_board`, `estado`).
4. **`sprints` (`Sprint`):** Registro de sprints Agile (`nombre`, `estado`, `fecha_inicio`, `fecha_fin`, `fecha_finalizacion`).
5. **`issues` (`Issue`):** Información de historias, bugs y tareas sincronizadas (`key_issue`, `summary`, `status_actual`, `created_at`, `resolved_at`, `story_points`).
6. **`transiciones_estado_issue` (`TransicionEstadoIssue`):** Historial inmutable de movimientos de estado (`estado_anterior`, `estado_nuevo`, `fecha_cambio`). Permite calcular el **Cycle Time** exacto.
7. **`kpis_historicos` (`KpisHistoricos`):** Métricas calculadas e inmutables por proyecto y sprint (**Lead Time medio**, **Cycle Time medio**, **Throughput**, **Velocidad**, **WIP actual**).
8. **`logs_sincronizacion` (`LogsSincronizacion`):** Auditoría ETL de tareas ejecutadas (`RUNNING`, `SUCCESS`, `ERROR`, `issues_procesados`, `tiempo_ejecucion_segundos`, `detalle_error`).

---

## 4. Estrategia de Seguridad y Autenticación

1. **Autenticación Doble (OAuth 2.0 + API Token Fallback):**
   * **OAuth 2.0 con Atlassian:** Inicio de sesión único (SSO) mediante `https://auth.atlassian.com`.
   * **API Token Basic Auth:** Canal prioritario para la extracción masiva de tickets sin bloqueos por Rate Limit.
2. **Protección de Sesión por Cookies Firmadas (HMAC SHA-256):**
   * Las sesiones de usuario utilizan cookies `HTTP-Only` con SameSite `Lax` y firmas criptográficas (`sign_session_id`).
3. **Protección HTTP Basic Auth en Documentación OpenAPI:**
   * La interfaz Swagger/ReDoc (`/docs`, `/redoc`, `/openapi.json`) está protegida por credenciales de administrador (`DOCS_USER` / `DOCS_PASSWORD`).
4. **Protección CSRF OAuth:**
   * Generación y validación de tokens de estado de un solo uso (`_oauth_states`).

---

## 5. Estrategia de Extracción de Datos e Integración con Jira

1. **Migración Atlassian Change 2046 (`/search/jql`):**
   * Cumplimiento con la nueva API recomendada de Jira Cloud REST v3, implementando un mecanismo de reserva (*fallback*) inteligente entre `GET /search/jql`, `POST /search/jql` y `GET /search`.
2. **Extracción Masiva de Historial (`expand=changelog`):**
   * Eliminación de peticiones HTTP en bucle. El historial de transiciones de estados viene incrustado directamente en los resultados paginados de la consulta JQL, reduciendo el tiempo ETL en un 98%.
3. **Aislamiento de Sesión en Tareas de Segundo Plano:**
   * Las tareas `BackgroundTasks` abren una sesión independiente `SessionLocal()` con manejo de `db.rollback()` automático ante excepciones, evitando errores de sesión cerrada o `PendingRollbackError`.
4. **Filtrado Estricto por `projectKey`:**
   * Los tableros y sprints se filtran estrictamente por la clave del proyecto para evitar fuga de métricas entre distintos proyectos.

---

## 6. Arquitectura del Frontend (React SPA)

* **Estructura Modular de Vistas y Componentes:**
  * `src/views/auth/LoginView.jsx`: Pantalla de inicio de sesión.
  * `src/views/common/DashboardView.jsx`: Tablero principal con gráficos interactivos Recharts y filtros dinámicos.
  * `src/views/admin/SystemSyncTab.tsx`: Panel de control de sincronización manual/CRON y tabla de auditoría.
  * `src/components/common/DatePickerDropdown.jsx`: Selector de rango de fechas.
  * `src/components/common/ProjectPickerDropdown.jsx`: Selector visual de proyectos.

---

## 7. Rendimiento, Caché y Procesamiento Asíncrono

1. **Procesamiento Asíncrono de Tareas (`BackgroundTasks`):**
   * La sincronización ETL corre de forma no bloqueante sin congelar la interfaz de usuario.
2. **Caché en Memoria de Corta Duración (`ShortLivedCache`):**
   * Las métricas rápidas de JQL utilizan una caché en memoria con TTL de 60 segundos por usuario.

---

## 8. Despliegue Multi-Contenedor (Docker Compose)

La infraestructura utiliza Docker Compose con 3 servicios principales:

* **`db` (PostgreSQL 15 Alpine):** Base de datos relacional con comprobación de salud (`pg_isready`) y volumen persistente `postgres_data`.
* **`backend` (FastAPI):** Imagen construida a partir de `Dockerfile` que ejecuta migraciones automáticas (`alembic upgrade head`) y levanta el servidor Uvicorn en el puerto `8000`.
* **`frontend` (React + Nginx):** Compilación en dos etapas (*multi-stage build*) servida por Nginx en los puertos `80` y `5173`, actuando como proxy inverso de `/api/` hacia el servicio backend.
