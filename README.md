# MCHAV Analytics — Backend API

**API REST asíncrona de alto rendimiento construida en Python 3.12 y FastAPI para la ingesta, procesamiento y análisis de métricas operativas de Atlassian Jira.**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.12.0-3776AB?style=flat-square&logo=python)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15.0-4169E1?style=flat-square&logo=postgresql)](https://www.postgresql.org/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0.25-red?style=flat-square)](https://www.sqlalchemy.org/)
[![Alembic](https://img.shields.io/badge/Alembic-1.13.1-orange?style=flat-square)](https://alembic.sqlalchemy.org/)

---

## Visión General del Backend

El Backend de **MCHAV Analytics** implementa los principios de **Clean Architecture** para garantizar el desacoplamiento de capas, la mantenibilidad a largo plazo y la independencia de componentes de infraestructura.

Capacidades principales:
1. **Extracción e Ingesta de Datos Jira:** Integración asíncrona con Atlassian Jira REST API v3, lectura de historiales de cambio (`changelog`), cálculo de tiempos de entrega y pipeline ETL incremental.
2. **Motor de Cálculo de KPIs:** Algoritmos para la medición de Lead Time, Cycle Time, Throughput, Velocidad de Sprints, Eficiencia de Flujo y Trabajo en Progreso (WIP).
3. **Seguridad y Control de Sesión:** Firma de cookies criptográficas stateless mediante **HMAC SHA-256**, soporte de autenticación dual (OAuth 2.0 3LO de Atlassian y API Token) y control RBAC.
4. **Documentación OpenAPI Protegida:** Interfaces Swagger UI (`/docs`) y ReDoc (`/redoc`) resguardadas mediante autenticación básica HTTP.

---

## Documentación Técnica Integrada

Toda la especificación técnica del sistema se encuentra disponible en las siguientes guías especializadas:

* **[Portal de Documentación Principal del Sistema (`/docs`)](../docs/index.md)**
* **[Índice de Documentación del Backend (`docs/index.md`)](docs/index.md)**

### Módulos Técnicos del Backend

| Dominio | Documento | Descripción |
| :--- | :--- | :--- |
| **Arquitectura** | [Clean Architecture](../docs/architecture/clean_architecture.md) | Separación en capas: Dominio, Aplicación, Infraestructura y Controladores. |
| **API REST** | [API & Enrutamiento](../docs/backend/api.md) | Endpoints FastAPI, esquemas Pydantic v2 y controladores HTTP. |
| **Lógica de Negocio** | [Servicios de Aplicación](../docs/backend/services.md) | Algoritmos de negocio y cálculo de indicadores clave (KPIs). |
| **Persistencia** | [Repositorios SQLAlchemy](../docs/backend/repositories.md) | Mapeo objeto-relacional y capa de acceso a datos PostgreSQL. |
| **Modelo de Datos** | [Diagrama ER](../docs/database/er_diagram.md) | Esquema relacional relacional de 8 tablas PostgreSQL en Mermaid. |
| **Seguridad** | [Autenticación & Sesiones](../docs/backend/authentication.md) | Firma y verificación de galletas de sesión con HMAC SHA-256. |
| **Jira ETL** | [Integración Jira API](../docs/integrations/jira_api.md) | Cliente HTTP asíncrono (`Httpx`) y motor de sincronización. |
| **Despliegue** | [Contenedores Docker](../docs/deployment/docker.md) | Especificación de `Dockerfile` y configuración del servidor Uvicorn. |

---

## Requisitos del Sistema

* **Python:** `v3.12.0` o superior.
* **PostgreSQL:** `v15.0` o superior (base de datos relacional activa).
* **Docker & Docker Compose:** *(Opcional, para ejecución contenedorizada)*.

---

## Instalación y Configuración Local

### 1. Clonar el repositorio y posicionarse en el directorio del Backend
```bash
git clone https://github.com/Mchav-Analytics/Mchav-Analytics-Backend.git
cd Mchav-Analytics-Backend
```

### 2. Creación y activación del entorno virtual
```bash
# Crear entorno virtual
python -m venv venv

# Activar en Windows PowerShell / CMD:
.\venv\Scripts\activate

# Activar en Linux / macOS:
source venv/bin/activate
```

### 3. Instalación de dependencias
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configuración de variables de entorno (`.env`)
Cree un archivo `.env` en la raíz del proyecto tomando como base `.env.example`:

```bash
cp .env.example .env
```

Configure las variables de acuerdo a los parámetros del entorno:

```env
# 1. Configuración de Base de Datos PostgreSQL
DATABASE_URL=postgresql://postgres:TU_CONTRASEÑA@localhost:5432/mchav_db

# 2. Configuración de Aplicación y URLs
FRONTEND_URL=http://localhost:5173
SESSION_SECRET_KEY=mchav_super_secret_key_prod_2026

# 3. Integración OAuth 2.0 con Atlassian Jira
JIRA_CLIENT_ID=tu_jira_client_id
JIRA_CLIENT_SECRET=tu_jira_client_secret
JIRA_CALLBACK_URL=http://localhost:8000/api/auth/callback

# 4. Credenciales de Conexión por API Token (Fallback)
JIRA_DOMAIN=https://tuempresa.atlassian.net
JIRA_EMAIL=usuario@empresa.com
JIRA_API_TOKEN=ATATT3xFfGF0...

# 5. Seguridad de la Documentación FastAPI (/docs)
DOCS_USER=admin
DOCS_PASSWORD=MchavDocs2026!Sec#Admin
```

---

## Migraciones de Base de Datos (Alembic)

Para aplicar la estructura de tablas relacionales en PostgreSQL:

```bash
alembic upgrade head
```

---

## Ejecución del Servicio Backend

Para iniciar el servidor ASGI Uvicorn en entorno de desarrollo:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Endpoints y Documentación Interactiva

* **Swagger UI:** [`http://localhost:8000/docs`](http://localhost:8000/docs) *(Requiere autenticación)*
* **ReDoc:** [`http://localhost:8000/redoc`](http://localhost:8000/redoc)
* **Verificación de Estado (Healthcheck):** [`http://localhost:8000/health`](http://localhost:8000/health)

---

## Scripts de Poblamiento y Simulación

El módulo incluye scripts para la generación de datos de prueba y la validación de escenarios:

1. **Poblamiento Local de Métricas ([`seed_prueba_asd.py`](seed_prueba_asd.py)):**
   Genera un historial simulado de 6 sprints, 39 tickets, métricas de velocidad y registros de transiciones en PostgreSQL.
   ```bash
   python seed_prueba_asd.py
   ```

2. **Poblamiento Directo en Atlassian Jira Cloud ([`populate_jira_cloud_asd.py`](populate_jira_cloud_asd.py)):**
   Crea tableros, sprints y tickets en la nube de Atlassian Jira a través de la API REST v3 y ejecuta una sincronización ETL automática.
   ```bash
   python populate_jira_cloud_asd.py
   ```

---

## Generación de API Token de Jira

1. Ingrese a la consola de administración de Atlassian: [https://id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Inicie sesión con la cuenta correspondiente.
3. Seleccione **"Crear API token"**.
4. Defina una etiqueta identificadora (`MCHAV-Analytics-Token`).
5. Copie el token generado y péguelo en la variable `JIRA_API_TOKEN` en el archivo `.env`.

---

## Dependencias de Software

| Librería | Versión | Función |
| :--- | :--- | :--- |
| **`fastapi`** | `^0.109.0` | Framework web asíncrono para el desarrollo de la API REST |
| **`uvicorn`** | `^0.27.0` | Servidor ASGI para ejecución de alto rendimiento |
| **`sqlalchemy`** | `^2.0.25` | Mapeo objeto-relacional (ORM) para PostgreSQL |
| **`psycopg2-binary`** | `^2.9.9` | Controlador nativo de conexión a PostgreSQL |
| **`alembic`** | `^1.13.1` | Gestión de versiones y migraciones de esquema de base de datos |
| **`httpx`** | `^0.26.0` | Cliente HTTP asíncrono para consumo de Atlassian Jira REST API v3 |
| **`pydantic`** | `^2.6.0` | Validación estricta de esquemas DTO y tipado de datos |
| **`python-dotenv`** | `^1.0.0` | Carga de variables de entorno desde archivo `.env` |
| **`pytest`** | `^8.0.0` | Suite para ejecución de pruebas unitarias e integración |

---

## Estructura Física del Proyecto (`app/`)

```text
app/
├── api/                   # Controladores REST, endpoints HTTP y dependencias (deps.py)
├── core/                  # Configuración global, seguridad HMAC, hashing y constantes
├── db/                    # Sesión SQLAlchemy (session.py) y clase Base (base.py)
├── domain/                # Modelos ORM SQLAlchemy y Entidades puras de negocio
├── dtos/                  # Esquemas de validación y serialización de Pydantic v2
├── repositories/          # Clases de acceso a datos relacionales (CRUD)
├── services/              # Casos de uso de negocio y motor de cálculo de KPIs
└── main.py                # Punto de entrada de la aplicación FastAPI y Middlewares
```
