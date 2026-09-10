# Guía de Despliegue e Implementación en el Sistema 🛠️📦

Este documento detalla el procedimiento paso a paso para realizar la implementación y despliegue del proyecto **MCHAV Analytics** en entornos de desarrollo, pruebas (Staging) o producción.

---

## 📑 Índice de Contenidos
1. [Requisitos del Entorno](#1-requisitos-del-entorno)
2. [Despliegue Recomendado: Docker Compose (Multi-Contenedor)](#despliegue-recomendado-docker-compose-multi-contenedor)
3. [Despliegue Manual Paso a Paso](#despliegue-manual-paso-a-paso)
   * [Paso 1: Configuración de PostgreSQL](#paso-1-configuración-de-postgresql)
   * [Paso 2: Instalación del Backend FastAPI](#paso-2-instalación-del-backend-fastapi)
   * [Paso 3: Auto-Migraciones de Estructura de BD](#paso-3-auto-migraciones-de-estructura-de-bd)
   * [Paso 4: Compilación del Frontend React](#paso-4-compilación-del-frontend-react)
   * [Paso 5: Servidor Nginx Proxy Inverso](#paso-5-servidor-nginx-proxy-inverso)
   * [Paso 6: Daemon Systemd en Servidores Linux](#paso-6-daemon-systemd-en-servidores-linux)
4. [Verificación e Inspección de Salud (Health Checks)](#verificación-e-inspección-de-salud-health-checks)

---

## 1. Requisitos del Entorno

Asegúrate de contar con un servidor de aplicaciones (Linux Ubuntu 22.04 LTS, Windows Server 2022 o contenedor Docker) con las siguientes características mínimas:

* **CPU:** 2 Cores vCPU
* **RAM:** 4 GB RAM
* **Disco:** 20 GB SSD
* **Software:** Docker & Docker Compose **o** (Python 3.12, Node.js 18 LTS, PostgreSQL 15, Nginx).

---

## Despliegue Recomendado: Docker Compose (Multi-Contenedor)

Es el método **más rápido, portable y seguro** para poner en marcha la solución completa en cualquier servidor o computadora de desarrollo.

### 1. Clonar el repositorio y copiar la plantilla de configuración:
```bash
git clone https://github.com/Mchav-Analytics/Mchav-Analytics-Backend.git
cd "Proyecto Mchav"
cp Mchav-Backend/.env.example Mchav-Backend/.env
```

### 2. Ajustar credenciales en `Mchav-Backend/.env`:
Edita las variables de entorno de Jira (`JIRA_CLIENT_ID`, `JIRA_CLIENT_SECRET`, `JIRA_API_TOKEN`, `JIRA_DOMAIN`, `JIRA_EMAIL`).

### 3. Iniciar la infraestructura multi-contenedor:
```bash
docker compose up --build -d
```

### Servicios Desplegados:
* **`mchav_db` (PostgreSQL 15 Alpine):** Base de datos relacional con comprobación de salud continua (`pg_isready`).
* **`mchav_backend` (FastAPI + Uvicorn):** Servidor API que ejecuta migraciones de Alembic (`alembic upgrade head`) y auto-migraciones de esquemas en el puerto `8000`.
* **`mchav_frontend` (React + Nginx):** Servidor web de producción que actúa como proxy inverso de `/api/` en los puertos `80` y `5173`.

---

## Despliegue Manual Paso a Paso

Si no deseas utilizar Docker, sigue esta guía para realizar la instalación manual directa en el sistema operativo:

### Paso 1: Configuración de PostgreSQL
1. Conéctate a PostgreSQL con el usuario administrador:
   ```bash
   sudo -u postgres psql
   ```
2. Crea la base de datos y el usuario dedicado:
   ```sql
   CREATE DATABASE mchav_db;
   CREATE USER mchav_user WITH PASSWORD 'TuPasswordSeguro2026!';
   GRANT ALL PRIVILEGES ON DATABASE mchav_db TO mchav_user;
   \q
   ```

### Paso 2: Instalación del Backend FastAPI
1. Entra a la carpeta del backend:
   ```bash
   cd Mchav-Backend
   python3.12 -m venv venv
   source venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
2. Crea el archivo `.env` en la raíz de `Mchav-Backend/` con la configuración de la base de datos y credenciales de Jira.

### Paso 3: Auto-Migraciones de Estructura de BD
Ejecuta las migraciones relacionales con Alembic:
```bash
alembic upgrade head
```

### Paso 4: Compilación del Frontend React
1. Navega a `Mchav-Frontend/`:
   ```bash
   cd ../Mchav-Frontend
   npm install
   npm run build
   ```
   Esto generará los activos optimizados en `dist/`.

### Paso 5: Servidor Nginx Proxy Inverso
Ejemplo de configuración de Nginx (`/etc/nginx/sites-available/mchav`):

```nginx
server {
    listen 80;
    server_name tu-dominio.com;

    location / {
        root /var/www/Mchav-Frontend/dist;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /docs {
        proxy_pass http://127.0.0.1:8000/docs;
        proxy_set_header Host $host;
    }
}
```

### Paso 6: Daemon Systemd en Servidores Linux
Crea el archivo `/etc/systemd/system/mchav-backend.service`:

```ini
[Unit]
Description=Servicio Backend FastAPI MCHAV Analytics
After=network.target postgresql.service

[Service]
User=ubuntu
WorkingDirectory=/var/www/Mchav-Backend
ExecStart=/var/www/Mchav-Backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Habilita e inicia el servicio:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now mchav-backend
```

---

## Verificación e Inspección de Salud (Health Checks)

1. **Backend Status:**  
   ```bash
   curl http://localhost:8000/
   # Respuesta esperada: {"message": "Bienvenido a la API de MCHAV Analytics"}
   ```
2. **Suite de Pruebas Unitarias e Integración:**  
   ```bash
   pytest
   # Resultado esperado: 28 passed in 2.30s
   ```
