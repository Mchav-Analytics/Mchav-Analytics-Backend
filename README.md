# MCHAV Analytics Backend

> API REST para automatización de KPIs, integración con Jira Cloud y procesamiento de analítica de desarrollo.

![Python](https://img.shields.io/badge/Python-FastAPI-blue?style=for-the-badge\&logo=python)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-316192?style=for-the-badge\&logo=postgresql)
![Docker](https://img.shields.io/badge/Docker-Container-2496ED?style=for-the-badge\&logo=docker)
![Swagger](https://img.shields.io/badge/OpenAPI-Swagger-85EA2D?style=for-the-badge\&logo=swagger)

---

## Descripción

MCHAV Analytics Backend es responsable de:

* Integración con Jira Cloud API
* Procesamiento y cálculo de KPIs
* Exposición de endpoints REST
* Automatización de sincronización de datos
* Seguridad y autenticación JWT

---

## Características

* Integración con Jira REST API v3
* Consultas dinámicas mediante JQL
* Autenticación JWT
* Scheduler de sincronización automática
* Persistencia con PostgreSQL
* Documentación Swagger/OpenAPI
* Clean Architecture
* Servicios dockerizados

---

## KPIs Procesados

* Sprint Velocity
* Lead Time
* Cycle Time
* Throughput
* Reopen Rate

---

## Stack Tecnológico

| Tecnología | Propósito       |
| ---------- | --------------- |
| FastAPI    | API REST        |
| PostgreSQL | Base de datos   |
| SQLAlchemy | ORM             |
| Alembic    | Migraciones     |
| JWT        | Seguridad       |
| Docker     | Contenerización |
| Pytest     | Testing         |

---

## Arquitectura

```bash
app/
├── api/
├── core/
├── models/
├── schemas/
├── services/
├── repositories/
├── scheduler/
├── middleware/
└── tests/
```

---

## Instalación

### Clonar repositorio

```bash
git clone https://github.com/tu-org/mchav-analytics-backend.git
```

---

### Crear entorno virtual

```bash
python -m venv venv
```

---

### Instalar dependencias

```bash
pip install -r requirements.txt
```

---

### Variables de entorno

```env
DATABASE_URL=
JWT_SECRET=
JIRA_BASE_URL=
JIRA_EMAIL=
JIRA_API_TOKEN=
```

---

### Ejecutar servidor

```bash
uvicorn app.main:app --reload
```

---

## Documentación API

Swagger disponible en:

```bash
http://localhost:8000/docs
```

---

## Testing

```bash
pytest
```

---

## Seguridad

* Autenticación JWT
* RBAC Authorization
* Variables de entorno seguras
* Endpoints protegidos
* Validación de tokens

---

## Compatibilidad Cloud

Compatible con:

* Docker
* AWS
* Terraform
* GitHub Actions

---

## Equipo

Desarrollado para Grupo ASD SAS.
