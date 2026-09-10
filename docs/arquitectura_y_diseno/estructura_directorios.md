# Estructura de Directorios del Sistema (Backend & Frontend)

## Objetivo
Proporcionar un mapa compacto y claro de la estructura de carpetas y archivos principales de la solución **MCHAV Analytics**.

## Responsabilidad
Servir como referencia rápida para la ubicación de módulos del backend, frontend, base de datos e infraestructura.

## Flujo
- **`Mchav-Analytics-Backend/`**: API REST asíncrona en Python 3.12 (FastAPI), SQLAlchemy ORM, Alembic y PostgreSQL.
- **`Mchav-Analytics-Frontend/`**: Cliente SPA en React 18 (Vite, Tailwind CSS, Recharts) y Nginx Proxy Inverso.
- **`docs/`**: Portal central de documentación técnica del sistema.

## Componentes relacionados
- [Mchav-Analytics-Backend/app/main.py](file:///c:/Users/vhoyos/Desktop/Prueba2/Mchav-Analytics-Backend/app/main.py)
- [Mchav-Analytics-Frontend/src/App.jsx](file:///c:/Users/vhoyos/Desktop/Prueba2/Mchav-Analytics-Frontend/src/App.jsx)
- [docker-compose.yml](file:///c:/Users/vhoyos/Desktop/Prueba2/Mchav-Analytics-Frontend/docker-compose.yml)

## Ejemplo

### Estructura Resumida por Archivos y Módulos (`mchv/`)

```text
Prueba2/
├── docker-compose.yml
├── Mchav-Analytics-Backend/
│   ├── app/
│   │   ├── main.py                    → Punto de entrada ASGI FastAPI y startup events
│   │   ├── core/                      → Configuración (.env), BD engine y Hashing HMAC
│   │   ├── api/v1/                    → Presentación HTTP (Routers, deps.py, Controllers)
│   │   ├── services/                  → Negocio (KPIs Lead/Cycle Time & Motor ETL)
│   │   ├── repositories/              → Acceso a datos (SQLAlchemy ORM Repositories)
│   │   ├── models/                    → Persistencia ORM (User, Sprint, Issue, Transiciones)
│   │   ├── schemas/                   → DTOs y Contratos de Validación (Pydantic v2)
│   │   └── datasources/               → Cliente HTTP Jira REST API v3 (httpx)
│   ├── alembic/                       → Migraciones de base de datos PostgreSQL
│   ├── tests/                         → Suite de pruebas unitarias pytest
│   ├── seed_prueba_asd.py             → Script de poblamiento local (6 Sprints, 39 Tickets)
│   ├── populate_jira_cloud_asd.py     → Script de poblamiento directo Jira Cloud API
│   └── Dockerfile                     → Dockerfile Backend (Python 3.12 + Uvicorn)
│
└── Mchav-Analytics-Frontend/
    ├── nginx.conf                     → Proxy Inverso Nginx (/api -> Backend:8000)
    ├── Dockerfile                     → Multi-stage build (React + Nginx)
    └── src/                           → React SPA alineado con la API
        ├── App.jsx                    → Router dinámico React SPA, Layout y Guardias
        ├── views/                     → Vistas (Login | Dashboard | Admin Tabs)
        ├── components/                → Componentes UI reutilizables (Sidebar, Topbar, Modales)
        └── services/                  → Cliente Axios configurado con Cookies HMAC
```

## Buenas prácticas
- Mantener la separación estricta entre carpetas de infraestructura, backend y frontend.
- Documentar las rutas de archivos de forma unívoca con sus responsabilidades descriptivas.

## Errores comunes
- Colocar archivos de controladores directamente en la carpeta raíz del backend.
- Omitir la descripción de los módulos auxiliares de datasources o scripts de poblamiento.
