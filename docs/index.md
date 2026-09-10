# 📚 Portal de Documentación del Backend — MCHAV Analytics

Bienvenido al centro principal de documentación técnica, guías de despliegue, sustentación pedagógica y arquitectura del **Backend de MCHAV Analytics**.

> 🌐 **[Navegar al Portal de Documentación Central del Sistema (`/docs`)](../../docs/index.md)**

---

## ⚡ Visión General del Backend

* **Lenguaje & Framework:** Python 3.12 | FastAPI (ASGI Asíncrono)
* **Persistencia & ORM:** PostgreSQL 15 | SQLAlchemy ORM | Migraciones con Alembic
* **Seguridad:** Cookies Firmadas Criptográficamente con HMAC SHA-256 | HTTP Basic Auth para OpenAPI
* **Integración Jira:** Jira Cloud REST API v3 (`/search/jql` + `expand=changelog`) | OAuth 2.0 (3LO) + Fallback API Token

---

## 🗺️ Rutas Recomendadas de Lectura por Rol

### 🚀 1. Para Desarrollo y Onboarding Backend
1. 📄 **[Guía de Instalación Rápida](guias_y_despliegue/GUIA_INSTALACION.md)** — Configura el entorno local con Python y Docker.
2. 📄 **[Estructura de Directorios](arquitectura_y_diseno/estructura_directorios.md)** — Comprende la disposición física de `app/`.
3. 📄 **[Controladores vs Servicios](arquitectura_y_diseno/controladores_vs_servicios.md)** — Entiende la separación de responsabilidades HTTP y lógica de negocio.
4. 📄 **[Tutorial de Swagger UI](jira_y_tutoriales/swagger_jira_tutorial.md)** — Aprende a probar endpoints interactivamente.

### 🎓 2. Para Evaluación y Sustentación Académica
1. 📄 **[Checklist de Entregables (Syllabus)](entregables_y_sustentacion/analisis_entregables.md)** — Consulta el semáforo de cumplimiento (100% verde 🟢).
2. 📄 **[Guía Completa de Entregables](entregables_y_sustentacion/GUIA_ENTREGABLES_COMPLETA.md)** — Revisa el detalle hito a hito de las Fases 1 y 2.
3. 📄 **[Sustentación Técnica del Proyecto](entregables_y_sustentacion/sustentacion_proyecto.md)** — Resumen técnico ejecutivo de ingeniería.
4. 📄 **[Tutorial de Sustentación Pedagógica](entregables_y_sustentacion/tutorial_sustentacion_completa.md)** — Explicación conceptual profunda de KPIs y algoritmos.

### 🔒 3. Para Seguridad e Infraestructura
1. 📄 **[Autenticación HMAC SHA-256](seguridad_y_autenticacion/autenticacion_hmac.md)** — Mecanismo stateless de firma de cookies de sesión.
2. 📄 **[Seguridad de Endpoints vs Middleware](seguridad_y_autenticacion/seguridad_endpoints_vs_middleware.md)** — Estrategias de autorización y guardias de seguridad.
3. 📄 **[Guía de Despliegue en Servidores](guias_y_despliegue/GUIA_DESPLIEGUE_E_IMPLEMENTACION.md)** — Despliegue con Nginx, Uvicorn y PostgreSQL Docker.

---

## 🗂️ Catálogo Completo por Categorías

```text
Mchav-Analytics-Backend/docs/
├── index.md                              # 🎯 Índice Principal Backend
├── entregables_y_sustentacion/           # 🎓 Entregables, Syllabus y Evaluaciones
├── guias_y_despliegue/                   # ⚡ Instalación, Servidores y Requisitos
├── arquitectura_y_diseno/                # 🏛️ Documento de Arquitectura y Reglas
├── seguridad_y_autenticacion/            # 🔒 Seguridad HMAC y Middleware
└── jira_y_tutoriales/                    # 🔌 Jira API v3, Mapeos y Swagger
```

---

### 🎓 Categoría 1: Entregables y Sustentación (`entregables_y_sustentacion/`)

* 📄 **[Checklist de Entregables del Syllabus](entregables_y_sustentacion/analisis_entregables.md)**  
  *Resumen:* Matriz tipo semáforo que audita el cumplimiento del 100% de las tareas requeridas en las Fases 1 y 2 del proyecto.  
  *Uso:* Verificación de requisitos cumplidos.

* 📄 **[Guía de Entregables Completa](entregables_y_sustentacion/GUIA_ENTREGABLES_COMPLETA.md)**  
  *Resumen:* Manual extenso con evidencias de código, configuraciones de endpoints y explicaciones detalladas por cada semana de trabajo.  
  *Uso:* Consulta de entregables para evaluadores y auditores.

* 📄 **[Sustentación Técnica del Proyecto](entregables_y_sustentacion/sustentacion_proyecto.md)**  
  *Resumen:* Documento sintético y de alto nivel enfocado en las decisiones de diseño de software, patrones de arquitectura y resolución de cuellos de botella.  
  *Uso:* Preparación para defensas técnicas de ingeniería.

* 📄 **[Tutorial de Sustentación Pedagógica Completa](entregables_y_sustentacion/tutorial_sustentacion_completa.md)**  
  *Resumen:* Guía ilustrativa paso a paso con matemáticas aplicadas de Lead/Cycle Time, resolución de N+1 queries en SQL y ejemplos conceptuales.  
  *Uso:* Aprendizaje pedagógico y preparación de demostraciones.

---

### ⚡ Categoría 2: Guías e Instalación (`guias_y_despliegue/`)

* 📄 **[Guía de Instalación y Arranque Local](guias_y_despliegue/GUIA_INSTALACION.md)**  
  *Resumen:* Guía rápida para clonar el repositorio, configurar entornos virtuales Python 3.12, variables `.env` y levantar servicios con Docker Compose.  
  *Uso:* Configuración inicial en máquinas de desarrollo.

* 📄 **[Guía de Despliegue e Implementación](guias_y_despliegue/GUIA_DESPLIEGUE_E_IMPLEMENTACION.md)**  
  *Resumen:* Instrucciones para el aprovisionamiento de servidores de producción, configuración de Nginx Proxy Inverso, Uvicorn ASGI y PostgreSQL.  
  *Uso:* Despliegue en entornos de staging o producción.

* 📄 **[Control de Versiones y Requisitos de Entorno](guias_y_despliegue/versionamiento_tecnologias.md)**  
  *Resumen:* Tabla comparativa de versiones de Python, Node.js, PostgreSQL y librerías clave (`fastapi`, `sqlalchemy`, `pydantic`).  
  *Uso:* Garantizar la compatibilidad del entorno de ejecución.

---

### 🏛️ Categoría 3: Arquitectura y Diseño (`arquitectura_y_diseno/`)

* 📄 **[Documento de Arquitectura y Decisiones Técnicas](arquitectura_y_diseno/DOCUMENTO_ARQUITECTURA.md)**  
  *Resumen:* Documento maestro de arquitectura que registra el diseño en capas concéntricas (Clean Architecture), modelo relacional y flujo de datos.  
  *Uso:* Referencia principal del diseño de software backend.

* 📄 **[Documentación Técnica General del Backend](arquitectura_y_diseno/technical_documentation.md)**  
  *Resumen:* Especificación exhaustiva de módulos internos, capa de servicios, repositorios SQL, Pydantic DTOs y clientes HTTP.  
  *Uso:* Comprensión profunda del código fuente.

* 📄 **[Estructura de Directorios](arquitectura_y_diseno/estructura_directorios.md)**  
  *Resumen:* Explicación carpeta por carpeta del rol de `core/`, `api/`, `services/`, `repositories/`, `models/`, `schemas/` y `datasources/`.  
  *Uso:* Orientación para organizar nuevos módulos en el backend.

* 📄 **[Controladores vs Servicios](arquitectura_y_diseno/controladores_vs_servicios.md)**  
  *Resumen:* Guía sobre la frontera entre controladores HTTP (FastAPI Routers) y servicios de aplicación (Casos de Uso de negocio).  
  *Uso:* Evitar acoplamiento y fugas de lógica de negocio a la capa web.

* 📄 **[Guía de Arquitectura del Frontend](arquitectura_y_diseno/frontend_architecture_guide.md)**  
  *Resumen:* Descripción del cliente web en React SPA, comunicación con el backend vía Axios y gestión de estado visual.  
  *Uso:* Entender la integración del backend con la interfaz de usuario.

* 📄 **[Guía de Estilos y Reglas de Código](arquitectura_y_diseno/GUIA_ESTILOS_Y_REGLAS.md)**  
  *Resumen:* Estándares de calidad de código PEP 8, tipeado estricto con Type Hints, manejo de excepciones y formato.  
  *Uso:* Mantener consistencia estilística en las contribuciones de código.

---

### 🔒 Categoría 4: Seguridad y Autenticación (`seguridad_y_autenticacion/`)

* 📄 **[Autenticación con HMAC SHA-256 (Firmado de Cookies)](seguridad_y_autenticacion/autenticacion_hmac.md)**  
  *Resumen:* Análisis profundo del esquema de seguridad stateless mediante firmado criptográfico de cookies con HMAC SHA-256 para prevenir secuestro de sesión y adulteración de ID.  
  *Uso:* Auditoría de seguridad y mantenimiento del módulo de autenticación.

* 📄 **[Seguridad de Endpoints vs Middleware](seguridad_y_autenticacion/seguridad_endpoints_vs_middleware.md)**  
  *Resumen:* Comparativa entre aplicar autorizaciones en middlewares globales vs inyección de dependencias `Depends()` en endpoints específicos.  
  *Uso:* Elección de estrategias de seguridad para nuevas rutas.

---

### 🔌 Categoría 5: Integración Jira y Tutoriales (`jira_y_tutoriales/`)

* 📄 **[Mapeo de Datos de Jira](jira_y_tutoriales/mapeo_datos_jira.md)**  
  *Resumen:* Detalle exacto del mapeo entre los objetos JSON/Changelog retornado por Jira Cloud REST API v3 y las tablas relacionales de PostgreSQL.  
  *Uso:* Mantenimiento y extensión de la sincronización ETL.

* 📄 **[Tutorial de Swagger y Conexión de API](jira_y_tutoriales/swagger_jira_tutorial.md)**  
  *Resumen:* Guía interactiva paso a paso para utilizar la interfaz OpenAPI Swagger protegida por credenciales Basic Auth para probar los endpoints del backend.  
  *Uso:* Pruebas manuales de la API REST.

---

## 💻 Comandos Rápidos de Desarrollo

```bash
# 1. Iniciar servidor de desarrollo backend
uvicorn app.main:app --reload --port 8000

# 2. Ejecutar migraciones de base de datos Alembic
alembic upgrade head

# 3. Ejecutar suite de pruebas unitarias con cobertura
pytest --cov=app tests/

# 4. Generar datos de prueba locales (6 sprints, 39 tickets)
python seed_prueba_asd.py

# 5. Desplegar aplicación completa en contenedores Docker
docker compose up --build -d
```

---

> 🚀 **¿Buscas los nuevos diagramas en Mermaid y ADRs del sistema?**  
> Visita el portal global unificado en **[docs/index.md](../../docs/index.md)**.
