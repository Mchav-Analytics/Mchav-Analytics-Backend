# Documento de Diseño de Software (SDD)
**Proyecto:** MCHAV Analytics (Backend)

| Versión | Fecha | Autor | Descripción de los Cambios |
|---------|-------|-------|----------------------------|
| 1.0     | 2026-08-31 | Equipo de Arquitectura | Creación inicial del Documento de Diseño de Software consolidado. |

---

Este documento sirve como la fuente centralizada de diseño técnico, consolidando las directrices arquitectónicas, el diseño de datos, estrategias de pruebas y las consideraciones transversales del sistema MCHAV Analytics.

## 1. Introducción y Propósito
MCHAV Analytics es un sistema diseñado para la sincronización, procesamiento y visualización de métricas ágiles y de ingeniería extraídas directamente desde Jira. El backend actúa como el motor central que gestiona la autenticación, la extracción ETL (Extract, Transform, Load) y el cálculo inmutable de KPIs históricos (Lead Time, Cycle Time, Velocity, etc.).

## 2. Visión General de la Arquitectura (High-Level Design)
El sistema utiliza una arquitectura **API-First (REST)** orientada a servicios y acoplada a una **Single Page Application (SPA)** en el frontend.

```text
  [ Cliente Web / Navegador ]
             │
             │ HTTP (JSON / Cookies Firmadas)
             ▼
  [ Nginx Proxy Inverso ]
        │            │
        │ /          │ /api/v1/
        ▼            ▼
  [ React SPA ]   [ FastAPI Backend (Python) ]
  (Frontend)      ├── Controllers (HTTP Routers)
                  ├── Services (Lógica ETL, Cálculos KPIs)
                  ├── Datasources (Jira API Client)
                  └── Repositories (SQLAlchemy ORM)
                         │
                         ▼
                  [ PostgreSQL 15 DB ]
```

### Stack Tecnológico Justificado
- **FastAPI (Python 3.12):** Elegido por su velocidad asíncrona, validación estricta de esquemas (Pydantic) y auto-generación de documentación.
- **PostgreSQL 15:** Base de datos relacional elegida por su soporte a transacciones ACID, crucial para mantener el historial inmutable de auditoría y estados.
- **React + Vite:** Rendimiento de recarga rápida y ecosistema rico para visualización de gráficas.
- **Docker Compose:** Garantiza un entorno predecible e idéntico entre desarrollo, pruebas y producción.

## 3. Patrón de Diseño: Clean Architecture (Low-Level Design)
El backend implementa **Clean Architecture**, aislando completamente las reglas de negocio de los detalles del framework o la infraestructura:

- `core/`: Infraestructura transversal (Conexión DB, Variables `.env`, Hashing, Caché).
- `datasources/`: Adaptadores externos (Cliente HTTP para Jira REST API v3).
- `schemas/`: Validaciones estrictas de entrada/salida (DTOs con Pydantic).
- `models/`: Entidades relacionales del dominio (ORM SQLAlchemy).
- `repositories/`: Capa de persistencia que aísla las consultas SQL de la lógica.
- `services/`: Casos de uso de negocio y lógica core (Motor ETL, OAuth, Cálculos).
- `api/v1/`: Controladores (Endpoints HTTP) e inyección de dependencias (`deps.py`).

## 4. Diseño de Base de Datos y Modelo de Datos
El sistema utiliza un enfoque relacional inmutable para garantizar la trazabilidad forense de los tickets:

- **Entidades de Dominio:** `usuarios`, `roles`, `proyectos`, `sprints`, `issues`.
- **Trazabilidad (`transiciones_estado_issue`):** Registra cada movimiento de estado (`estado_anterior` -> `estado_nuevo` con su `fecha_cambio`). Es la base fundamental del cálculo exacto del Cycle Time.
- **Métricas (`kpis_historicos`):** Almacena las "fotos" inmutables de KPIs (Velocidad, Lead/Cycle Time promedio) calculadas por proyecto/sprint.
- **Auditoría (`logs_sincronizacion`):** Rastrea las ejecuciones del pipeline ETL en segundo plano (`SUCCESS`, `ERROR`, `issues_procesados`).

## 5. Integración con Jira y Estrategia ETL
El núcleo analítico del sistema depende de una ingesta de datos eficiente:
1. **Consumo de API:** Se utiliza el endpoint unificado `/search/jql` (Jira Cloud REST API v3) con un fallback automático a POST si el query es muy largo.
2. **Carga Optimizada (`expand=changelog`):** Se extrae el historial completo de transiciones de los issues en una sola petición paginada, reduciendo masivamente la carga de red (hasta 98%).
3. **Manejo de Transacciones:** Las tareas ETL corren como `BackgroundTasks` asíncronas con sesiones de BD aisladas (`SessionLocal`) que hacen rollback automático ante excepciones críticas.

## 6. Consideraciones Transversales y Requisitos No Funcionales (NFRs)

### 6.1 Seguridad y Autenticación
- **Flujo Dual OAuth 2.0 / API Token:** Autenticación visual vía SSO Atlassian; uso de API Tokens cifrados para tareas ETL de fondo previniendo bloqueos por Rate Limit.
- **Sesiones HTTP-Only:** Se utilizan cookies protegidas contra ataques XSS con directiva `SameSite=Lax`, cifradas mediante HMAC SHA-256 (`sign_session_id`).
- **Endpoint Security:** Documentación OpenAPI protegida por HTTP Basic Auth. Prevención de CSRF mediante estado temporal validado.

### 6.2 Rendimiento, Escalabilidad y Caché
- **Caché en Memoria (`ShortLivedCache`):** Implementación con TTL de 60 segundos para evitar ahogar la base de datos y la API de Jira ante recargas continuas del dashboard.
- **Non-blocking I/O:** El uso nativo de `async/await` en FastAPI garantiza soporte concurrente elevado sin bloquear hilos.

### 6.3 Manejo de Errores y Resiliencia
- **Respuestas Estandarizadas:** Todo error retorna una estructura JSON predecible: `{"detail": "Mensaje", "code": "ERROR_CODE"}`.
- **Códigos HTTP consistentes:** 400 (Bad Request), 401 (No Autenticado), 403 (No Autorizado por RBAC), 404 (Recurso no encontrado), 429 (Too Many Requests), 500 (Error Interno manejado genéricamente).
- **Log Centralizado:** Trazabilidad de fallos a través del sistema estándar de logging de Python, guardando trazas completas sin exponer detalles sensibles al frontend.

## 7. Estrategia de Pruebas (Testing Strategy)
Para garantizar la viabilidad y mantenimiento a largo plazo:
- **Frontend (Vitest & RTL):** Pruebas unitarias de componentes, hooks y servicios visuales, manteniendo una cobertura mínima del 90% en la capa de conexión API y vistas críticas.
- **Frontend (Playwright):** End-to-End (E2E) simulando comportamientos reales sobre navegadores Chromium y WebKit.
- **Backend (Pytest):** Aserciones unitarias sobre los `services/` garantizando precisión matemática absoluta en el motor de cálculo de KPIs (Lead/Cycle Time).

## 8. Análisis de Riesgos y Limitaciones Técnicas (Trade-offs)
| Riesgo Identificado | Impacto | Estrategia de Mitigación |
|---------------------|---------|--------------------------|
| **Dependencia de Uptime Jira API** | Alto (Bloquea sincronización) | Los datos ya sincronizados se consumen directo de Postgres. Si la API de Jira cae, el sistema avisa visualmente al usuario pero los Dashboards siguen renderizando los KPIs históricos almacenados localmente. |
| **Volumen de Datos Masivo (ETL)** | Medio (Degradación BD) | Implementación de paginación exhaustiva (max 100 issues por lote) e índices combinados en las tablas relacionales. |
| **Límites de Peticiones (Rate Limit)** | Alto (Ban temporal) | El motor ETL implementa algoritmos de *Exponential Backoff* al recibir errores HTTP 429, pausando la ejecución de la cola y reanudando minutos después. |

## 9. Despliegue y Contenedores
Toda la infraestructura está provisionada a través de Docker Compose (`docker-compose.yml`), encapsulando 3 contenedores altamente cohesionados:
- `db` (Postgres 15) con comprobación dinámica de salud y volúmenes montados localmente.
- `backend` (FastAPI) que auto-aplica las migraciones `alembic upgrade head` en su script de arranque.
- `frontend` (Nginx+React) configurado con un proxy inverso interno que redirige silenciosamente las peticiones HTTP/WS de `/api/v1/` hacia el contenedor del backend, evitando problemas de CORS.
