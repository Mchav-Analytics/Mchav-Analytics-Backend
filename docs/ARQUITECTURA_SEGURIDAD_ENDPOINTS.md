# Arquitectura de Seguridad en Endpoints — MCHAV Analytics 🛡️🔒

Este documento detalla técnicamente el funcionamiento de la seguridad, autenticación, protección de endpoints y salvaguarda de documentación en la API Backend de **MCHAV Analytics**.

---

## 📑 Índice

1. [Resumen de la Arquitectura de Seguridad](#1-resumen-de-la-arquitectura-de-seguridad)
2. [Capa 1: Cookies Firmadas con HMAC SHA-256 (`HTTP-Only` + `SameSite=Lax`)](#2-capa-1-cookies-firmadas-con-hmac-sha-256-http-only--samesitelax)
3. [Capa 2: Inyección de Dependencias y Guardias de Endpoints](#3-capa-2-inyección-de-dependencias-y-guardias-de-endpoints)
4. [Capa 3: Protección CSRF en el Flujo OAuth 2.0](#4-capa-3-protección-csrf-en-el-flujo-oauth-2-0)
5. [Capa 4: Protección de Documentación Swagger / OpenAPI (`HTTP Basic Auth`)](#5-capa-4-protección-de-documentación-swagger--openapi-http-basic-auth)
6. [Flujo Completo de Ejecución de una Petición Protegida](#6-flujo-completo-de-ejecución-de-una-petición-protegida)

---

## 1. Resumen de la Arquitectura de Seguridad

La arquitectura de seguridad de MCHAV Analytics sigue los estándares **OWASP** para aplicaciones web modernas. Se compone de 4 capas defensivas independientes:

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                          APLICACIÓN FRONTEND                            │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                     (Petición HTTP con Cookie HTTP-Only)
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ CAPA 4: HTTP Basic Auth (Protección de /docs y Swagger UI)             │
├─────────────────────────────────────────────────────────────────────────┤
│ CAPA 3: Protección CSRF OAuth 2.0 (Validación de 'state' de un solo uso)│
├─────────────────────────────────────────────────────────────────────────┤
│ CAPA 2: Guardias de Inyección de Dependencias (FastAPI Depends)        │
├─────────────────────────────────────────────────────────────────────────┤
│ CAPA 1: Firma Criptográfica HMAC SHA-256 en Cookies de Sesión           │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       CONTROLADOR / SERVICIO (BD)                       │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Capa 1: Cookies Firmadas con HMAC SHA-256 (`HTTP-Only` + `SameSite=Lax`)

📂 **Ubicación en código:** [`app/core/security.py`](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/app/core/security.py)

### ❓ ¿Por qué no usamos tokens JWT almacenados en `localStorage`?
Almacenar tokens en `localStorage` expone la sesión a ataques de tipo **XSS (Cross-Site Scripting)**: cualquier script de tercero malicioso inyectado en el frontend puede leer `localStorage` y robar la sesión del usuario.

### 🛡️ Solución Implementada
Usamos cookies de sesión firmadas con atributos de máxima seguridad:

* **`HTTP-Only`**: La cookie **NO puede ser leída por JavaScript** desde el navegador (`document.cookie` retorna vacío para esta cookie). Si un atacante inyecta script, no puede robar la sesión.
* **`SameSite=Lax`**: Previene ataques **CSRF (Cross-Site Request Forgery)** asegurando que el navegador no envíe la cookie en peticiones cross-site no deseadas.
* **Firma HMAC SHA-256**: El ID de usuario se combina con la clave secreta `SESSION_SECRET_KEY` para producir una firma digital (`ID.HASH_HEX`).
* **Tiempo Constante**: La función `hmac.compare_digest` evita ataques de análisis de tiempo (*Timing Attacks*).

### 💻 Código Fuente Explicado:

```python
def sign_session_id(user_id: int) -> str:
    """Toma un ID (ej: 5) y retorna '5.e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'"""
    user_id_str = str(user_id)
    signature = hmac.new(SESSION_SECRET_KEY, user_id_str.encode(), hashlib.sha256).hexdigest()
    return f"{user_id_str}.{signature}"

def verify_session_id(signed_value: str) -> int | None:
    """Verifica si la firma es válida. Si la cookie fue manipulada, retorna None."""
    if not signed_value:
        return None
    try:
        user_id_str, signature = signed_value.split(".", 1)
        expected_signature = hmac.new(SESSION_SECRET_KEY, user_id_str.encode(), hashlib.sha256).hexdigest()
        if hmac.compare_digest(signature, expected_signature):
            return int(user_id_str)
    except Exception:
        pass
    return None
```

---

## 3. Capa 2: Inyección de Dependencias y Guardias de Endpoints

📂 **Ubicación en código:** [`app/api/v1/deps.py`](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/app/api/v1/deps.py)

En lugar de un middleware global genérico, cada endpoint en FastAPI inyecta funciones de validación mediante `Depends()`:

### 💻 Código Fuente Explicado:

```python
def get_current_user_id(request: Request) -> int:
    """1. Extrae la cookie 'session_id' de la petición HTTP y verifica su firma HMAC."""
    signed_session = request.cookies.get("session_id")
    if not signed_session:
        raise HTTPException(status_code=401, detail="No autenticado")
    user_id = verify_session_id(signed_session)
    if not user_id:
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada")
    return user_id

def check_user_exists(db: Session, user_id: int):
    """2. Confirma en la base de datos que el usuario exista y siga activo."""
    user = user_repo.get(db, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    return user
```

### 💻 Aplicación en un Controlador:
En [`app/api/v1/controllers/jira_controller.py`](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/app/api/v1/controllers/jira_controller.py#L57-L64):

```python
@router.get("/metrics")
async def get_jira_metrics(request: Request, db: Session = Depends(get_db)):
    # La petición debe pasar obligatoriamente por ambas verificaciones
    user_id = get_current_user_id(request) # Lanza 401 si no hay cookie o firma es mala
    user = check_user_exists(db, user_id)  # Lanza 401 si el usuario no está en BD
    ...
```

---

## 4. Capa 3: Protección CSRF en el Flujo OAuth 2.0

📂 **Ubicación en código:** [`app/services/auth_service.py`](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/app/services/auth_service.py#L22-L35)

Durante la autenticación con Atlassian Jira mediante OAuth 2.0 (3LO):

1. **Generación del Estado**: Cuando el usuario hace clic en "Iniciar Sesión", el servidor genera un token aleatorio seguro de 16 bytes (`state`) y lo guarda en memoria (`_oauth_states`).
2. **Construcción de URL**: La URL de autorización envía este `state` a Atlassian: `https://auth.atlassian.com/authorize?...&state=XYZ123`.
3. **Consumo de Un Solo Uso**: Al recibir el callback de Atlassian (`/api/auth/callback?code=...&state=XYZ123`), el servidor valida que el `state` esté en memoria y **lo elimina inmediatamente**.
4. Si un atacante intenta inyectar una petición de callback falsa o reutilizar un estado, el servidor rechaza la transacción con `HTTP 400 Bad Request`.

---

## 5. Capa 4: Protección de Documentación Swagger / OpenAPI (`HTTP Basic Auth`)

📂 **Ubicación en código:** [`app/main.py`](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/app/main.py#L15-L47)

### ❓ El Riesgo de la Documentación Pública
FastAPI genera por defecto la interfaz Swagger en `http://localhost:8000/docs`. Si se deja abierta en producción:
* Cualquier persona o bot scanner puede listar todos los endpoints privados del sistema.
* Un atacante puede analizar los parámetros y esquemas de respuesta para buscar vulnerabilidades.
* Permite probar peticiones interactivas sin salir del navegador (*"Try it out"*).

### 🛡️ Solución Implementada
Desactivamos las URLs automáticas y creamos rutas personalizadas protegidas por **HTTP Basic Auth**:

```python
# 1. Desactivar rutas públicas automáticas
app = FastAPI(
    title="MCHAV Analytics API",
    docs_url=None,       # 🚫 Oculta /docs público
    redoc_url=None,      # 🚫 Oculta /redoc público
    openapi_url=None     # 🚫 Oculta el JSON del mapa de la API
)

security = HTTPBasic()

# 2. Función guardiana de credenciales
def get_current_username(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, DOCS_USER)
    correct_password = secrets.compare_digest(credentials.password, DOCS_PASSWORD)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales de acceso a la documentación incorrectas",
            headers={"WWW-Authenticate": "Basic"}, # Dispara emergente en el navegador
        )
    return credentials.username

# 3. Endpoints protegidos explícitamente
@app.get("/docs", include_in_schema=False)
async def get_documentation(username: str = Depends(get_current_username)):
    return get_swagger_ui_html(openapi_url="/openapi.json", title="MCHAV Analytics API Docs")
```

Las credenciales de acceso a `/docs` se configuran en el archivo `.env`:
```env
DOCS_USER=admin
DOCS_PASSWORD=MchavDocs2026!Sec#Admin
```

---

## 6. Flujo Completo de Ejecución de una Petición Protegida

```text
1. Cliente envía petición HTTP GET /api/jira/metrics
   Cookie Header: session_id=1.a8f9e2b...
         │
         ▼
2. FastAPI recibe la petición y evalúa dependencias `Depends(...)`
         │
         ▼
3. `get_current_user_id()` extrae la cookie `session_id`
   └─► Separa ID (1) y Hash (a8f9e2b...)
   └─► Recalcula HMAC-SHA256(1, SESSION_SECRET_KEY)
   └─► Compara firmas con hmac.compare_digest()
         │
         ├──► Firma Inválida / Cookie Ausente ──► Lanza HTTP 401 Unauthorized ❌
         │
         ▼ (Firma Válida)
4. `check_user_exists()` consulta la Base de Datos
   └─► query(User).get(1)
         │
         ├──► Usuario Inexistente / Inactivo  ──► Lanza HTTP 401 Unauthorized ❌
         │
         ▼ (Usuario Válido)
5. Controlador `get_jira_metrics()` ejecuta la lógica de negocio y retorna respuesta HTTP 200 OK ✅
```
