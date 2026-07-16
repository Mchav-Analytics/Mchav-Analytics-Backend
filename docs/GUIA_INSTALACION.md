# Guía de Instalación y Arranque - MCHAV Analytics 🚀

Este documento detalla el paso a paso exacto para que un nuevo desarrollador pueda levantar el proyecto (Backend, Frontend y Base de Datos) en su propia computadora desde cero.

---

## ⚡ Método 1: Arranque Centralizado con Docker (Recomendado para Compañeros)
Si tu compañero tiene Docker Desktop instalado en su PC, no es necesario que instale Python, Node.js ni configure PostgreSQL localmente:

1. Abre **Docker Desktop** y espera a que el servicio esté activo (ícono verde).
2. Abre la terminal en la raíz del proyecto (`c:\Users\msalamanca\Desktop\Proyecto Mchav`) y ejecuta:
   ```bash
   docker-compose up --build -d
   ```
3. ¡Listo! El entorno completo se levantará en contenedores aislados:
   *   **Frontend Web:** [http://localhost](http://localhost) (puerto 80)
   *   **Backend OpenAPI:** [http://localhost:8000/docs](http://localhost:8000/docs)
4. Para apagar los servicios:
   ```bash
   docker-compose down
   ```

---

## ⚡ Método 2: Arranque Rápido con Windows Script (Desarrollo Local)
Si prefieres correr el proyecto localmente sin Docker, puedes iniciar ambos servidores (Vite y FastAPI) en un solo clic:

1. Abre la raíz del proyecto (`c:\Users\msalamanca\Desktop\Proyecto Mchav`).
2. Ejecuta el archivo script por lotes:
   ```powershell
   .\start.bat
   ```
3. Se abrirán dos terminales independientes de forma paralela: una para el frontend (Vite) y otra para el backend (Uvicorn).

---

## 📌 3. Requisitos Previos para Instalación Manual
Si tu compañero desea realizar la instalación manual y depurar el código localmente, debe tener instalado:
- **Git:** Para clonar los repositorios.
- **Python (3.10 o superior):** Para ejecutar el Backend (FastAPI).
- **Node.js (18+ o superior):** Para ejecutar el Frontend (React + Vite).
- **PostgreSQL:** Sistema de base de datos relacional.


---

## 🛠️ 2. Configuración de la Base de Datos (PostgreSQL)
El backend requiere una base de datos local para almacenar los usuarios y métricas.

1. Abre `pgAdmin` o tu terminal de PostgreSQL (`psql`).
2. Crea una nueva base de datos llamada **mchav_db**:
   ```sql
   CREATE DATABASE mchav_db;
   ```
3. Asegúrate de conocer tu usuario (suele ser `postgres`) y tu contraseña.

---

## ⚙️ 3. Instalación del Backend (FastAPI)

Abre una terminal y ejecuta los siguientes comandos ordenadamente:

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/Mchav-Analytics/Mchav-Analytics-Backend.git
   cd Mchav-Analytics-Backend
   ```

2. **Crear y activar un Entorno Virtual (Recomendado):**
   * En Windows:
     ```bash
     python -m venv venv
     venv\Scripts\activate
     ```
   * En Mac/Linux:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. **Instalar dependencias de Python:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar Variables de Entorno:**
   Crea un archivo llamado `.env` en la raíz de la carpeta `Mchav-Analytics-Backend` y copia el siguiente contenido. **Importante:** Actualiza la contraseña de la base de datos según lo que pusiste en PostgreSQL.
   ```ini
   JIRA_CLIENT_ID=5HDr6UuSqHaqWNdIsrLzEdsgfwaccDo0
   JIRA_CLIENT_SECRET=ATOAoRkxhfANEAjO3VLewZj82b65fxNZVBDmer06y_gssGMl-aBo3JQ7c2Xt1iq2bA2KFDF55C94
   JIRA_CALLBACK_URL=http://localhost:8000/api/auth/callback
   FRONTEND_URL=http://localhost:5173
   DATABASE_URL=postgresql://postgres:TU_CONTRASEÑA_AQUI@localhost:5432/mchav_db
   ```

5. **Levantar el Servidor Backend:**
   ```bash
   uvicorn app.main:app --reload
   ```
   *El backend quedará corriendo en: `http://localhost:8000`*
   *Puedes ver la documentación de la API en: `http://localhost:8000/docs`*

---

## 🌐 4. Instalación del Frontend (React)

Abre **otra terminal nueva** (sin cerrar la del backend) y ejecuta:

1. **Clonar el repositorio:**
   ```bash
   cd ..   # (Para salir de la carpeta del backend)
   git clone https://github.com/Mchav-Analytics/Mchav-Analytics-Frontend.git
   cd Mchav-Analytics-Frontend
   ```

2. **Instalar paquetes de Node (NPM):**
   ```bash
   npm install
   ```

3. **Configurar Variables de Entorno (Opcional si usa las de defecto):**
   Crea un archivo `.env` en la raíz de la carpeta frontend:
   ```ini
   VITE_API_BASE_URL=http://localhost:8000/api/v1
   VITE_API_AUTH_URL=http://localhost:8000/api/auth
   ```

4. **Levantar el Servidor Frontend:**
   ```bash
   npm run dev
   ```
   *El frontend quedará corriendo en: `http://localhost:5173`*

---

## 🔒 5. Permisos de Atlassian (Error de Login)

Si cuando tu compañero intenta iniciar sesión le sale el error: *"Esta aplicación está en desarrollo; solo el propietario puede otorgarle acceso"*.

Deberás darle acceso manualmente como desarrollador/tester:
1. Ingresa tú (como creador) a [developer.atlassian.com/console/myapps](https://developer.atlassian.com/console/myapps).
2. Selecciona la aplicación de **MCHAV Analytics**.
3. Ve a **Distribution** -> **Sharing** (o "Authorization").
4. Agrega el correo electrónico de Atlassian de tu compañero a la lista de usuarios permitidos.
5. ¡Listo! Ya podrá entrar a `http://localhost:5173` y conectarse con éxito.
