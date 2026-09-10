# Control de Versiones y Requisitos del Entorno - MCHAV Analytics 📋

Este documento detalla la matriz de versiones y herramientas necesarias para que MCHAV Analytics funcione de forma idéntica, estable y sin errores ("out-of-the-box") en cualquier computadora de desarrollo (Windows, macOS o Linux).

---

## 💻 1. Requisitos del Sistema Operativo
*   **Windows:** Windows 10 u 11 (versión de 64 bits). Se recomienda PowerShell 7+ o Git Bash para ejecutar scripts.
*   **macOS:** macOS Catalina (10.15) o superior.
*   **Linux:** Ubuntu 20.04 LTS o superior (o cualquier distribución compatible con Node.js y Python3).

---

## 🐳 2. Requisitos de Contenedores (Docker - Recomendado)
Si se utiliza el arranque centralizado con Docker Compose (Método 1), estas son las versiones requeridas:
*   **Docker Engine:** Versión `20.10.x` o superior (probado con éxito en la versión `29.5.3`).
*   **Docker Compose:** Versión `2.20.x` o superior.
*   **PostgreSQL (Docker Image):** `postgres:15-alpine` (imagen ultraligera optimizada).

---

## 🛠️ 3. Requisitos de Ejecución Local (Sin Docker)
Si se opta por correr los servidores de desarrollo de manera nativa (Método 2), se deben instalar exactamente estas plataformas:

| Plataforma / Runtime | Versión Mínima | Versión Recomendada | Propósito |
| :--- | :--- | :--- | :--- |
| **Python** | `3.10` | `3.12.x` | Servidor de Backend (FastAPI) |
| **Node.js** | `18.x` | `20.x` (LTS) | Servidor de Frontend (Vite + React) |
| **NPM** (gestor de paquetes) | `9.x` | `10.x` | Instalación de dependencias frontend |
| **PostgreSQL (Local)** | `14.x` | `15.x` o `16.x` | Base de datos relacional local |

---

## 🐍 4. Dependencias del Backend (Python - `requirements.txt`)
Las librerías de Python están acotadas a versiones específicas para evitar conflictos de incompatibilidad:

*   **FastAPI (`0.109.2`):** Framework web asíncrono para endpoints y enrutamiento.
*   **Uvicorn (`0.27.1`):** Servidor ASGI de alto rendimiento para ejecutar FastAPI.
*   **Pydantic (`2.6.1`):** Librería para validación y tipado de esquemas JSON (esenciales para las respuestas API).
*   **HTTPX (`0.26.0`):** Cliente HTTP asíncrono para comunicación con el API de Jira Cloud.
*   **SQLAlchemy (`2.0.x`):** ORM (Object-Relational Mapping) para interactuar con la base de datos relacional.
*   **Psycopg2-binary (`2.9.x`):** Driver nativo para la conexión de Python con PostgreSQL.
*   **Pytest (`8.0.0`):** Framework para ejecución de la suite de 28 pruebas unitarias e integración.
*   **Alembic (`1.13.x`):** Herramienta de control y aplicación de migraciones de la base de datos.
*   **Python-dotenv (`1.0.1`):** Lector de variables de entorno desde el archivo `.env`.

---

## ⚛️ 5. Dependencias del Frontend (React + Vite - `package.json`)
La interfaz web de usuario utiliza las siguientes librerías de Node.js:

*   **React (`^19.2.7`) & React-DOM (`^19.2.7`):** Librería base para la interfaz de componentes interactivos y SPA.
*   **React-Router-Dom (`^7.18.1`):** Manejador de rutas internas del navegador (Login, Dashboard, Auditoría).
*   **Axios (`^1.18.1`):** Cliente HTTP para peticiones Ajax hacia el backend de FastAPI (soporta cookies y CORS).
*   **Recharts (`^3.9.1`):** Librería para la renderización de gráficas interactivas de KPIs (Cycle Time, Velocity).
*   **Lucide-React (`^1.23.0`):** Set de íconos vectoriales modernos y responsivos.
*   **Vite (`^8.1.1`):** Bundler y servidor de desarrollo ultra-rápido para React.
*   **Tailwind CSS (`^4.3.2`):** Framework de CSS utilitario para diseño responsivo y premium.
*   **PostCSS (`^8.5.16`):** Procesador de CSS utilizado por Tailwind.
