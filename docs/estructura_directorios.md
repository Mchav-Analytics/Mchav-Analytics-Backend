# Estructura de Directorios (MCHAV Analytics) 📁

Este documento sirve como un mapa rápido para entender la **Clean Architecture** y la modularidad tanto del Backend como del Frontend.

---

## ⚙️ Backend (FastAPI + PostgreSQL)

El backend utiliza una arquitectura en capas estrictamente tipada.

```text
Mchav-Backend/
├── .env                     # Variables de entorno locales (NO COMITEAR)
├── requirements.txt         # Dependencias de Python
├── README.md                # Documentación principal del proyecto
├── Dockerfile               # Receta de construcción para contenedores
├── app/                     # CÓDIGO FUENTE PRINCIPAL
│   ├── main.py              # Punto de entrada de FastAPI
│   ├── api/                 # CAPA DE CONTROLADORES (Routers)
│   │   └── v1/
│   │       ├── api.py       # Enrutador maestro (aglutina todos los sub-routers)
│   │       └── endpoints/   # Rutas HTTP
│   │           ├── auth.py
│   │           ├── jira.py
│   │           ├── jql_queries.py
│   │           └── projects.py
│   ├── core/                # CAPA DE CONFIGURACIÓN Y SEGURIDAD
│   │   ├── config.py        # Carga de variables de entorno (dotenv)
│   │   ├── database.py      # Conexión a PostgreSQL (SQLAlchemy Engine)
│   │   ├── jql_config.py    # Consultas JQL parametrizadas
│   │   └── security.py      # Firmas HMAC y validación de tokens
│   ├── schemas/             # CAPA DE VALIDACIÓN (Pydantic)
│   │   └── jql.py
│   ├── services/            # CAPA DE REGLAS DE NEGOCIO
│   │   ├── jira_sync.py     # Lógica de sincronización con API de Atlassian
│   │   └── kpi.py           # Motor matemático de cálculo de métricas
│   └── models/              # CAPA DE PERSISTENCIA (Modelos ORM Modulares)
│       ├── __init__.py      # Patrón Fachada (exporta todos los dominios)
│       ├── auth.py          # Tablas User y Role
│       ├── jira.py          # Tablas Proyecto, Sprint, Issue, Transiciones
│       └── metrics.py       # Tablas KpisHistoricos y Logs
├── docs/                    # DOCUMENTACIÓN TÉCNICA
│   ├── analisis_entregables.md
│   ├── autenticacion_hmac.md
│   ├── controladores_vs_servicios.md
│   ├── estructura_directorios.md  <-- ESTE ARCHIVO
│   ├── frontend_architecture_guide.md
│   ├── mapeo_datos_jira.md
│   ├── seguridad_endpoints_vs_middleware.md
│   ├── swagger_jira_tutorial.md
│   └── technical_documentation.md
└── tests/                   # CAPA DE TESTING AUTOMATIZADO
    ├── __init__.py
    └── test_security.py     # Pruebas unitarias de HMAC y Sesiones
```

---

## 🌐 Frontend (React + Vite)

El frontend sigue un enfoque minimalista basado en vistas (`views/`) y componentes reusables (`components/`).

```text
Mchav-Frontend/
├── .env                     # Variables de entorno locales
├── package.json             # Dependencias de Node.js
├── vite.config.js           # Configuración del empaquetador Vite
├── tailwind.config.js       # Configuración de estilos CSS (Tailwind)
├── public/                  # Recursos estáticos servidos directamente
│   ├── favicon.svg
│   └── icons.svg
└── src/                     # CÓDIGO FUENTE PRINCIPAL
    ├── App.jsx              # Enrutador principal de React Router DOM
    ├── index.css            # Estilos globales (Tailwind Directives)
    ├── main.jsx             # Punto de entrada de React (createRoot)
    ├── assets/              # Imágenes y gráficos
    │   └── hero.png
    ├── components/          # COMPONENTES UI REUTILIZABLES
    │   └── common/
    │       ├── Logo.jsx
    │       ├── MainLayout.jsx
    │       ├── Sidebar.jsx
    │       └── Topbar.jsx
    ├── services/            # SERVICIOS DE COMUNICACIÓN
    │   └── api.js           # Instancia de Axios (interceptores y llamadas HTTP)
    └── views/               # PÁGINAS COMPLETAS DE LA APLICACIÓN
        ├── admin/           # Vistas de Configuración
        │   ├── SystemSyncTab.tsx
        │   └── UserManagementTab.tsx
        ├── auth/            # Vistas de Autenticación
        │   └── LoginView.jsx
        └── common/          # Vistas Generales
            └── DashboardView.jsx
```
