# MCHAV Analytics 🚀📊

**MCHAV Analytics** es una plataforma web empresarial diseñada para la extracción, análisis y visualización avanzada de métricas ágiles e indicadores clave de rendimiento (KPIs) provenientes de **Atlassian Jira**. 

Proporciona visibilidad en tiempo real sobre el flujo de trabajo de desarrollo de software, midiendo variables como **Lead Time**, **Cycle Time**, **Throughput**, **Velocidad de Sprints** y **Tendencias de Trabajo**.

---

## 📋 Requisitos Previos (Prerequisites)

Para ejecutar e instalar la aplicación localmente o en un entorno de servidor, se requiere contar con las siguientes herramientas instaladas:

* **Docker & Docker Compose:** *(Recomendado para despliegue automatizado multi-contenedor)*.
* **Python:** `v3.12.0` o superior.
* **Node.js:** `v18.0.0` o superior (incluye `npm`).
* **PostgreSQL:** `v15.0` o superior.
* **Git:** Para control de versiones.

---

## 🔐 Variables de Entorno (`.env`)

> ⚠️ **ADVERTENCIA DE SEGURIDAD CRÍTICA:**
> El archivo `.env` contiene credenciales sensibles como contraseñas de base de datos, secretos de sesión y tokens de API. **JAMÁS debes subir o commitear el archivo `.env` a los repositorios de Git**.
> Asegúrate de que `.env` esté incluido en el archivo `.gitignore`. Usar como guía la plantilla `.env.example`.

### Configuración del archivo `.env` del Backend

Crea un archivo llamado `.env` en la raíz de la carpeta `Mchav-Backend/` tomando como referencia los siguientes parámetros:

```env
# 1. Configuración de Base de Datos PostgreSQL
DATABASE_URL=postgresql://postgres:TU_CONTRASEÑA@localhost:5432/mchav_db

# 2. Configuración de Aplicación y URLs
FRONTEND_URL=http://localhost:5173
SESSION_SECRET_KEY=mchav_super_secret_key_prod_2026

# 3. Integración OAuth 2.0 con Atlassian Jira (Login de App)
JIRA_CLIENT_ID=tu_jira_client_id
JIRA_CLIENT_SECRET=tu_jira_client_secret
JIRA_CALLBACK_URL=http://localhost:8000/api/auth/callback

# 4. Credenciales de Extracción por API Token (Fallback sin Rate Limits)
JIRA_DOMAIN=https://tuempresa.atlassian.net
JIRA_EMAIL=usuario@empresa.com
JIRA_API_TOKEN=ATATT3xFfGF0...

# 5. Seguridad de la Documentación FastAPI (/docs)
DOCS_USER=admin
DOCS_PASSWORD=MchavDocs2026!Sec#Admin
```

---

## 🐳 Inicio Rápido con Docker Compose

Para desplegar la aplicación completa (Base de datos PostgreSQL 15, Backend FastAPI y Frontend React + Nginx Proxy) en cualquier máquina con un solo comando:

```bash
# 1. Clonar el repositorio
git clone https://github.com/Mchav-Analytics/Mchav-Analytics-Backend.git

# 2. Iniciar contenedores en segundo plano
docker compose up --build -d
```

* **Aplicación Web Frontend:** `http://localhost:5173` o `http://localhost`
* **Backend API Documentation:** `http://localhost:8000/docs`

---

## 🔑 Guía para Obtener el API Token de Jira

1. Ingresa a: 👉 [https://id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Inicia sesión con tu cuenta de Atlassian.
3. Haz clic en **"Crear API token"** (Create API token).
4. Asigna una etiqueta (ej: `MCHAV-Analytics-Token`).
5. Copia la cadena generada (comienza por `ATATT3xFfGF0...`).
6. Pégala en el archivo `Mchav-Backend/.env` en la variable `JIRA_API_TOKEN`.

---

## 🧪 Scripts de Poblamiento y Generación de Datos de Prueba

El repositorio cuenta con scripts especializados para generar datos de prueba y simulación ágil:

1. **Poblamiento Local de Métricas e Historial ([seed_prueba_asd.py](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/seed_prueba_asd.py)):**
   Genera un historial completo de 6 sprints, 39 tickets, métricas de velocidad y transiciones de estado directamente en la base de datos PostgreSQL local para pruebas inmediatas de desarrollo.
   ```bash
   python seed_prueba_asd.py
   ```

2. **Poblamiento Directo en Atlassian Jira Cloud ([populate_jira_cloud_asd.py](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/populate_jira_cloud_asd.py)):**
   Crea tableros, sprints reales y tickets directamente en la nube de Atlassian Jira a través de la API REST v3 y ejecuta una sincronización ETL automática.
   ```bash
   python populate_jira_cloud_asd.py
   ```

---

## 📚 Librerías y Dependencias del Proyecto

### Backend (`Mchav-Backend`)
Construido bajo **Python 3.12** y arquitectura **Clean Architecture**:

| Librería | Versión | Descripción / Propósito |
| :--- | :--- | :--- |
| **`fastapi`** | `^0.109.0` | Framework web asíncrono de alto rendimiento |
| **`uvicorn`** | `^0.27.0` | Servidor ASGI para ejecución asíncrona |
| **`sqlalchemy`** | `^2.0.25` | ORM de mapeo objeto-relacional para PostgreSQL |
| **`psycopg2-binary`** | `^2.9.9` | Driver nativo de conexión a PostgreSQL |
| **`alembic`** | `^1.13.1` | Herramienta de migraciones de estructura de BD |
| **`httpx`** | `^0.26.0` | Cliente HTTP asíncrono para consumo de la REST API de Jira |
| **`pydantic`** | `^2.6.0` | Validación estricta de esquemas DTO y tipado |
| **`python-dotenv`** | `^1.0.0` | Carga de variables de entorno desde `.env` |
| **`pytest`** | `^8.0.0` | Suite de pruebas unitarias y de integración |

### Frontend (`Mchav-Frontend`)
Construido bajo **React 18**, **Vite** y **Tailwind CSS**:

| Librería | Versión | Descripción / Propósito |
| :--- | :--- | :--- |
| **`react`** / **`react-dom`** | `^18.2.0` | Biblioteca de interfaz de usuario basada en componentes |
| **`vite`** | `^5.0.0` | Bundler y servidor de desarrollo ultra-rápido |
| **`tailwindcss`** | `^3.4.0` | Framework de diseño CSS basado en utilidades |
| **`lucide-react`** | `^0.312.0` | Set de iconos vectoriales modernos |
| **`recharts`** | `^2.10.0` | Renderizado de gráficos interactivos (Lead/Cycle Time, Velocity) |
| **`axios`** | `^1.6.5` | Cliente HTTP con manejo de credenciales y cookies |

---

## 📖 Documentación del Sistema

Para consultar guías detalladas sobre arquitectura, normas de código e implementación:

* 📄 [Documento de Arquitectura y Diseño Técnico](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/docs/DOCUMENTO_ARQUITECTURA.md)
* 📄 [Guía de Despliegue e Implementación en Servidores](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/docs/GUIA_DESPLIEGUE_E_IMPLEMENTACION.md)
* 📄 [Guía de Estilos, Reglas y Convenciones de Código](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/docs/GUIA_ESTILOS_Y_REGLAS.md)
