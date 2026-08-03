# MCHAV Analytics

> **Plataforma Empresarial para la Extracción, Análisis y Visualización Avanzada de Métricas Ágiles e Indicadores de Rendimiento (KPIs) desde Atlassian Jira Cloud.**

![Python Version](https://img.shields.io/badge/Python-v3.12-blue?logo=python)
![FastAPI Version](https://img.shields.io/badge/FastAPI-v0.109-009688?logo=fastapi)
![React Version](https://img.shields.io/badge/React-v18.2-61DAFB?logo=react)
![PostgreSQL Version](https://img.shields.io/badge/PostgreSQL-v15.0-4169E1?logo=postgresql)
![Pytest Coverage](https://img.shields.io/badge/Pytest_Coverage-90%25-brightgreen?logo=pytest)
![License](https://img.shields.io/badge/License-MIT-green)

---

## Tabla de Contenidos

1. [Descripción General](#descripción-general)
2. [Características Principales](#características-principales)
3. [Tecnologías y Stack Técnico](#tecnologías-y-stack-técnico)
4. [Estructura del Proyecto](#estructura-del-proyecto)
5. [Requisitos Previos](#requisitos-previos)
6. [Configuración de Variables de Entorno (`.env`)](#configuración-de-variables-de-entorno-env)
7. [Instalación y Puesta en Marcha](#instalación-y-puesta-en-marcha)
   * [Opción A: Despliegue con Docker Compose (Recomendado)](#opción-a-despliegue-con-docker-compose-recomendado)
   * [Opción B: Instalación Local Manual](#opción-b-instalación-local-manual)
8. [Guía para Obtener el API Token de Jira](#guía-para-obtener-el-api-token-de-jira)
9. [Generación y Poblamiento de Datos de Prueba](#generación-y-poblamiento-de-datos-de-prueba)
10. [Ejecución de Pruebas Unitarias e Integración (`pytest`)](#ejecución-de-pruebas-unitarias-e-integración-pytest)
11. [Índice de Documentación Oficial](#índice-de-documentación-oficial)
12. [Licencia y Equipo](#licencia-y-equipo)

---

## Descripción General

**MCHAV Analytics** es un sistema web integral diseñado para automatizar la extracción de datos desde **Atlassian Jira Cloud**, procesar el historial de transiciones de estado de tickets y transformar datos crudos en métricas de rendimiento cuantitativas (*Agile Software Delivery KPIs*).

Permite a los líderes técnicos, Scrum Masters y Gerentes de Producto tomar decisiones basadas en datos reales mediante dashboards interactivos, gráficos de velocidad, medición de tiempos de ciclo y tableros de control en tiempo real.

---

## Características Principales

* **Cálculo Automático de Tiempos de Ciclo**: Medición precisa de **Lead Time** (desde la creación del ticket hasta su resolución) y **Cycle Time** (desde que se inicia el desarrollo activo hasta la entrega final).
* **Análisis de Velocidad y Rendimiento**: Cálculo de **Velocity** (puntos de historia completados por sprint) y **Throughput** (cantidad de ítems de trabajo entregados por unidad de tiempo).
* **Sincronización ETL en Tiempo Real**: Consumo asíncrono de la REST API v3 de Jira y recepción de **Webhooks** para actualizar métricas instantáneamente.
* **Configuración Flexible de Mapeos de Estado**: Permite personalizar qué estados de Jira corresponden a las fases base (*To Do*, *In Progress*, *Done*) según el workflow de cada equipo.
* **Autenticación Dual Segura**: Compatible con **OAuth 2.0 (3LO) de Atlassian** y autenticación local basada en **JWT Bearer Tokens** y **Cookies firmadas por HMAC SHA-256**.
* **Optimización mediante Caché TTL**: Caché de memoria de respuesta rápida (`ShortLivedCache`) para reducir la latencia de consultas agregadas y evitar el agotamiento de cuotas (*Rate Limits*) de la API de Jira.

---

## Tecnologías y Stack Técnico

### Backend (`Mchav-Backend`)
* **Lenguaje:** Python `v3.12`
* **Framework Web:** FastAPI `v0.109` (Servidor ASGI Uvicorn)
* **ORM & Base de Datos:** SQLAlchemy `v2.0` (Mapeo objeto-relacional) & PostgreSQL `v15.0`
* **Cliente HTTP Asíncrono:** HTTPX `v0.26` (Estrategia de extracción en 3 capas JQL)
* **Validación de Datos:** Pydantic `v2.6`
* **Suite de Pruebas:** Pytest `v9.1`, Pytest-Cov `v7.1` (90% Cobertura, 94 pruebas)

### Frontend (`Mchav-Frontend`)
* **Librería UI:** React `v18.2`
* **Herramienta de Construcción:** Vite `v5.0`
* **Estilos & Diseño:** Tailwind CSS `v3.4` (Iconos Lucide React)
* **Visualización de Datos:** Recharts `v2.10` (Gráficos interactivos de velocidad, líneas y barras)
* **Cliente HTTP:** Axios `v1.6`

### Infraestructura & Despliegue
* **Contenedores:** Docker `v24+` & Docker Compose `v2+`
* **Proxy Inverso:** Nginx `v1.25`

---

## Estructura del Proyecto

```text
Proyecto Mchav/
├── docker-compose.yml           # Orquestador multi-contenedor (PostgreSQL, Backend, Frontend)
├── pytest.ini                   # Configuración global de la suite de pruebas Pytest
├── start.bat                    # Script de inicio rápido en un clic (Windows)
├── README.md                    # Documentación principal del proyecto
│
├── Mchav-Backend/               # API RESTful en Python FastAPI
│   ├── app/
│   │   ├── api/v1/              # Controladores y Endpoints de la API REST
│   │   ├── core/                # Configuración, Base de Datos, Caché y Seguridad
│   │   ├── datasources/         # Conector HTTP asíncrono con Jira Cloud REST API
│   │   ├── models/              # Modelos de Entidad ORM (SQLAlchemy)
│   │   ├── repositories/        # Capa de Acceso a Datos (Pattern Repository)
│   │   ├── schemas/             # Esquemas de Validación DTO (Pydantic)
│   │   └── services/            # Servicios de Negocio (ETL, cálculo de KPIs y OAuth)
│   ├── tests/                   # Suite de 94 Pruebas Unitarias e Integración (en Español)
│   ├── docs/                    # Guías de Arquitectura y Documentación Técnica Backend
│   └── requirements.txt         # Lista de dependencias de Python
│
├── Mchav-Frontend/              # Aplicación Web React + Vite + Tailwind CSS
│   ├── src/
│   │   ├── components/          # Componentes de UI reutilizables y Gráficos (Recharts)
│   │   ├── pages/               # Páginas de Dashboard, Login, Mapeos y Proyectos
│   │   └── services/            # Clientes de API Axios
│   ├── package.json             # Dependencias del Frontend
│   └── vite.config.js           # Configuración de Vite Bundler
│
└── Mchav Docs/                  # Documentación oficial de negocio (SRS, Project Charter, HUs)
```

---

## Requisitos Previos

Asegúrate de contar con los siguientes componentes instalados en tu sistema:

| Herramienta | Versión Mínima Recomendada | Propósito |
| :--- | :--- | :--- |
| **Docker & Docker Compose** | `v24.0.0` / `v2.20.0` | Despliegue rápido multi-contenedor |
| **Python** | `v3.12.0` | Ejecución del backend FastAPI local |
| **Node.js & npm** | `v18.0.0` / `v9.0.0` | Ejecución y build del frontend React |
| **PostgreSQL** | `v15.0` | Motor de base de datos relacional |
| **Git** | `v2.40.0` | Control de versiones |

---

## Configuración de Variables de Entorno (`.env`)

> [!WARNING]
> **ADVERTENCIA DE SEGURIDAD CRÍTICA:**
> El archivo `.env` contiene credenciales privadas (secretos de sesión, API Tokens y contraseñas de BD). **NUNCA comitees o incluyas el archivo `.env` en repositorios públicos**. Verificatorio mediante `.gitignore`.

Crea un archivo denominado `.env` dentro de la carpeta `Mchav-Backend/` utilizando los siguientes valores de referencia:

```env
# 1. Configuración de Base de Datos PostgreSQL
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/mchav_db

# 2. Configuración de Aplicación y URLs
FRONTEND_URL=http://localhost:5173
SESSION_SECRET_KEY=mchav_super_secret_key_prod_2026

# 3. Integración OAuth 2.0 con Atlassian Jira (Login con App Atlassian)
JIRA_CLIENT_ID=tu_jira_client_id
JIRA_CLIENT_SECRET=tu_jira_client_secret
JIRA_CALLBACK_URL=http://localhost:8000/api/v1/auth/callback

# 4. Credenciales de Extracción por API Token (Conexión Directa)
JIRA_DOMAIN=https://tuempresa.atlassian.net
JIRA_EMAIL=usuario@empresa.com
JIRA_API_TOKEN=ATATT3xFfGF0...

# 5. Seguridad de la Documentación Interactiva FastAPI (/docs)
DOCS_USER=admin
DOCS_PASSWORD=MchavDocs2026!Sec#Admin
```

---

## Instalación y Puesta en Marcha

### Opción A: Despliegue con Docker Compose (Recomendado)

Inicia todos los servicios (Base de Datos PostgreSQL, API Backend FastAPI y Web Frontend) con un solo comando:

```bash
# 1. Clonar el repositorio
git clone https://github.com/Mchav-Analytics/Proyecto-Mchav.git
cd "Proyecto Mchav"

# 2. Construir e iniciar los contenedores en segundo plano
docker compose up --build -d
```

#### Puertos y accesos:
* **Aplicación Web Frontend:** [http://localhost:5173](http://localhost:5173) o [http://localhost](http://localhost)
* **Documentación API Backend (Swagger UI):** [http://localhost:8000/docs](http://localhost:8000/docs)
* **Usuario Administrador Predeterminado:** `admin@mchav.com` / `123456`

---

### Opción B: Instalación Local Manual

#### 1. Iniciar el Backend (FastAPI)
```bash
# Navegar a la carpeta del backend
cd Mchav-Backend

# Crear un entorno virtual
python -m venv venv

# Activar el entorno virtual (Windows)
.\venv\Scripts\activate

# Instalar dependencias de Python
pip install -r requirements.txt

# Ejecutar el servidor en modo desarrollo
uvicorn app.main:app --reload --port 8000
```

#### 2. Iniciar el Frontend (React + Vite)
```bash
# Abrir una nueva terminal y navegar a la carpeta del frontend
cd Mchav-Frontend

# Instalar dependencias de Node.js
npm install

# Iniciar servidor de desarrollo Vite
npm run dev
```

---

## Guía para Obtener el API Token de Jira

1. Ingresa al portal de seguridad de Atlassian: [Atlassian API Tokens](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Inicia sesión con tu cuenta de usuario de Jira Cloud.
3. Haz clic en el botón **"Crear API token"** (*Create API token*).
4. Asigna un nombre descriptivo (ej: `MCHAV-Analytics-Key`).
5. Copia el token generado (`ATATT3xFfGF0...`).
6. Configúralo en la variable `JIRA_API_TOKEN` en el archivo `Mchav-Backend/.env` o directamente en la vista de configuración del dashboard.

---

## Generación y Poblamiento de Datos de Prueba

El proyecto cuenta con scripts automatizados en la suite de pruebas unitarias (`pytest`) que generan datos dinámicos en memoria y tablas de PostgreSQL durante el desarrollo.

---

## Ejecución de Pruebas Unitarias e Integración (`pytest`)

El backend cuenta con una suite completa de **94 pruebas automatizadas** organizadas en 13 módulos con nomenclatura en español, alcanzando una cobertura de código del **90%** sin advertencias (*0 warnings*).

Para ejecutar la suite de pruebas con reporte de cobertura en consola:

```bash
cd Mchav-Backend
pytest --cov=app --cov-report=term-missing
```

### Módulos de Prueba en `Mchav-Backend/tests/`:
* `test_autenticacion_controlador.py`: Endpoints de autenticación local, OAuth y credenciales API.
* `test_autenticacion_servicio.py`: Tokens CSRF, intercambio OAuth y firmado HMAC.
* `test_jira_controlador.py`: Métricas agregadas, webhooks y tareas asíncronas.
* `test_jql_controlador.py`: Endpoints de extracción JQL delta, velocity y tiempos de ciclo.
* `test_proyectos_controlador.py`: Sprints, estados únicos y reglas de mapeo.
* `test_kpis_y_metricas.py`: Consulta de KPIs calculados e historial de proyectos.
* `test_fuente_datos_jira.py`: Conector de 3 capas JQL y changelogs en `JiraDatasource`.
* `test_sincronizacion_jira.py`: Motor ETL de sincronización de proyectos y tickets.
* `test_seguridad_y_permisos.py`: Middleware de seguridad dual (JWT + Cookie firmada).
* `test_repositorios_y_modelos.py`: Repositorios ORM y modelos SQLAlchemy.
* `test_persistencia_y_paginacion.py`: Memoria caché TTL `ShortLivedCache` y paginación.
* `test_tiempo_de_ciclo.py`: Lógica matemática de Lead Time, Cycle Time, Throughput y Velocity.
* `test_servidor_principal.py`: Endpoint raíz `/` y eventos de inicio `startup_event`.

---

## Índice de Documentación Oficial

El proyecto dispone de un amplio cuerpo documental para consulta de arquitectura y mantenimiento:

* [Documento de Arquitectura y Diseño Técnico (General)](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/docs/DOCUMENTO_ARQUITECTURA.md)
* [Arquitectura de Seguridad y Endpoints (Backend)](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/docs/ARQUITECTURA_SEGURIDAD_ENDPOINTS.md)
* [Guía de Despliegue e Implementación](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/docs/GUIA_DESPLIEGUE_E_IMPLEMENTACION.md)
* [Guía de Estilos y Reglas de Código](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/docs/GUIA_ESTILOS_Y_REGLAS.md)
* [Documentación Completa de Pruebas y Cobertura](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/docs/DOCUMENTACION_PRUEBAS.md)
* [Tutorial de Swagger UI y OpenAPI](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/docs/swagger_jira_tutorial.md)
* [Historias de Usuario v1.4](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav%20Docs/Historias_de_Usuario_v1.4.pdf)

---

## Licencia y Equipo

Este proyecto se encuentra distribuido bajo la licencia **MIT**. Desarrollado por el equipo de **MCHAV Analytics** para la gestión moderna de métricas de entrega de software.
