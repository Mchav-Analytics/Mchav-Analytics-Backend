🚀 QUANTARA

Plataforma inteligente para gestión y visualización de KPIs de equipos de desarrollo mediante integración con Jira Cloud.

📌 Descripción

QUANTARA es una plataforma web desarrollada para automatizar el cálculo, almacenamiento y visualización de KPIs de equipos de desarrollo utilizando la API REST de Jira Cloud.

El sistema permite transformar datos técnicos en información estratégica mediante dashboards interactivos, métricas automatizadas y reportes inteligentes para líderes de proyecto y directivos.

🎯 Objetivo

Centralizar el análisis de productividad y desempeño de equipos de desarrollo mediante métricas obtenidas desde Jira usando consultas JQL y procesamiento automatizado de datos.

⚡ Características Principales

✅ Integración con Jira Cloud API v3
✅ Consultas dinámicas usando JQL
✅ Dashboards interactivos en tiempo real
✅ Cálculo automático de KPIs
✅ Autenticación segura con JWT
✅ Exportación de reportes PDF
✅ Scheduler para sincronización automática
✅ Infraestructura como código con Terraform
✅ Despliegue contenerizado con Docker
✅ Arquitectura cloud-ready sobre AWS

📊 KPIs Soportados

- Sprint Velocity
- Lead Time
- Cycle Time
- Throughput
- Reopen Rate
- Resolution Rate

🏗️ Arquitectura General

- **Jira Cloud**
  - REST API v3
  - Envía datos a la capa backend
- **FastAPI Backend**
  - KPI Processing
  - Recibe datos Jira y calcula métricas
  - Exposición de API para el frontend
- **PostgreSQL**
  - Historical Data
  - Almacenamiento de métricas y eventos
- **React Frontend**
  - Interactive Charts
  - Visualización de KPIs y dashboards
- **Usuarios**
  - Managers / Leads
  - Consumo de información estratégica

🛠️ Stack Tecnológico

- Backend: Python + FastAPI
- Frontend: React + TypeScript
- Database: PostgreSQL
- Cloud: AWS
- IaC: Terraform
- Containers: Docker
- Charts: Chart.js
- Auth: JWT
- Version Control: Git + GitHub

🔐 Seguridad

- Autenticación basada en JWT
- Control de acceso por roles
- Variables de entorno seguras
- Protección de rutas en frontend
- Arquitectura desacoplada

👥 Roles del Sistema

- Admin: Gestión completa del sistema
- Manager: Visualización y análisis de KPIs
- Developer: Consulta de métricas individuales

🚀 Instalación

1️⃣ Clonar repositorio

```bash
git clone https://github.com/kamiloo1/QUANTARA.git
cd QUANTARA
```

2️⃣ Variables de entorno

Crear archivo `.env`

```text
JIRA_BASE_URL=
JIRA_EMAIL=
JIRA_API_TOKEN=
DATABASE_URL=
JWT_SECRET=
```

3️⃣ Levantar contenedores

```bash
docker-compose up --build
```

📂 Estructura del Proyecto

quantara/
│
├── backend/
├── frontend/
├── infrastructure/
├── database/
├── docs/
├── docker-compose.yml

📁 Documentación

La carpeta `Documentacion QUANTARA/` contiene la documentación adicional del proyecto, incluyendo instrucciones, diagramas y una guía de uso general.
