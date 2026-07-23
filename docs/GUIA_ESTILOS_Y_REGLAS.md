# Documento de Estilos, Reglas y Convenciones de Desarrollo 🎨📐

Este documento establece las directrices de codificación, estándares de estilo, convención de nombres y buenas prácticas que todos los desarrolladores deben cumplir al contribuir al proyecto **MCHAV Analytics**.

---

## 📑 Índices de Secciones
1. [Principios Generales de Desarrollo](#1-principios-generales-de-desarrollo)
2. [Reglas y Convenciones del Backend (Python / FastAPI)](#2-reglas-y-convenciones-del-backend-python--fastapi)
3. [Reglas y Convenciones del Frontend (React / Tailwind CSS)](#3-reglas-y-convenciones-del-frontend-react--tailwind-css)
4. [Estructura de Nombrado de Archivos por Capas](#4-estructura-de-nombrado-de-archivos-por-capas)
5. [Estándares de Git y Control de Versiones](#5-estándares-de-git-y-control-de-versiones)

---

## 1. Principios Generales de Desarrollo

* **Responsabilidad Única (SRP):** Cada archivo, clase o función debe tener una sola responsabilidad bien definida.
* **Sin Parches Superficiales (No Symptoms Patching):** Ante un error de ejecución o fallo en pruebas, se debe diagnosticar la causa raíz inspeccionando los logs, en lugar de tragar excepciones silenciosamente o retornar datos vacíos ficticios.
* **Ubicación Estricta de Importaciones (Import Rules):** Todas las sentencias `import` y `from ... import ...` deben estar ubicadas **estrictamente al inicio de cada archivo** (líneas 1 a 20). Queda prohibido escribir importaciones dentro del cuerpo de funciones o métodos.
* **Manejo Seguro de Transacciones (Rollback Handling):** Ante una excepción en operaciones de base de datos o en tareas ETL en segundo plano, se debe invocar `db.rollback()` antes de registrar logs de auditoría para evitar estados de transacción abortada (`PendingRollbackError`).
* **Verificación con Pruebas Automatizadas:** Todo cambio en la lógica de negocio o backend debe ser verificado ejecutando la suite de pruebas unitarias (`pytest`).
* **Seguridad Primero:** Ninguna clave secreta, contraseña o API Token debe escribirse directamente en el código fuente (`hardcoded`). Todo debe provenir del archivo `.env`.

---

## 2. Reglas y Convenciones del Backend (Python / FastAPI)

### 2.1 Estilo de Código Python (PEP 8)
* Seguir la guía estándar **PEP 8**.
* Usar `snake_case` para nombres de variables, funciones y métodos:
  ```python
  def calculate_and_save_kpis(db: Session, proyecto_id: str):
      ...
  ```
* Usar `PascalCase` para nombres de clases y modelos de SQLAlchemy / Pydantic:
  ```python
  class JiraDatasource:
      ...
      
  class UserResponse(BaseModel):
      ...
  ```
* Usar `UPPER_SNAKE_CASE` para constantes globales:
  ```python
  AUTHORIZATION_BASE_URL = "https://auth.atlassian.com/authorize"
  ```

### 2.2 Tipado Estricto (Type Hinting) y DTOs
* Todas las funciones públicas deben incluir anotaciones de tipo (`Type Hints`):
  ```python
  async def get_sync_logs(limit: int = 20, offset: int = 0, db: Session = Depends(get_db)) -> List[SyncLogResponse]:
      ...
  ```
* Toda petición o respuesta de API debe estar validada mediante un esquema DTO en Pydantic (`app/schemas/`).

### 2.3 Separación de Capas (Clean Architecture)
* **Controladores (`app/api/v1/controllers/`):** Deben ser delgados ("thin controllers"). Solo reciben parámetros de la petición HTTP, llaman a los servicios e inyectan dependencias mediante `app/api/v1/deps.py`.
* **Servicios (`app/services/`):** Contienen la lógica de negocio pura, cálculo de KPIs y la orquestación ETL en segundo plano (`run_jira_sync_task`).
* **Fuentes de Datos (`app/datasources/`):** Contienen únicamente las peticiones de cliente HTTP de bajo nivel a APIs externas como Jira REST API v3 (`/search/jql`).
* **Repositorios (`app/repositories/`):** Contienen las consultas SQL puras encapsuladas con SQLAlchemy.

---

## 3. Reglas y Convenciones del Frontend (React / Tailwind CSS)

### 3.1 Componentes Funcionales
* Usar exclusivamente **Componentes Funcionales de React** con Hooks (`useState`, `useEffect`, `useMemo`, `useRef`).
* Nombres de componentes en `PascalCase` y nombres de archivos coincidentes:
  ```jsx
  // DatePickerDropdown.jsx
  export default function DatePickerDropdown({ dateFilter, setDateFilter }) {
    ...
  }
  ```

### 3.2 Estilos con Tailwind CSS + Vanilla CSS Variables
* Usar utilidades de **Tailwind CSS** para maquetación, espaciados y estados responsivos (`flex`, `grid`, `p-4`, `rounded-2xl`, `hover:bg-slate-100`).
* Para colores del tema corporativo y compatibilidad entre Modo Claro y Oscuro, combinar clases de Tailwind con variables de CSS globales (`var(--input-bg)`, `var(--border-color)`).
* Usar la librería `lucide-react` para mantener una iconografía coherente y limpia en toda la aplicación.

---

## 4. Estructura de Nombrado de Archivos por Capas

Para garantizar que el propósito de cada archivo sea evidente de inmediato, se deben cumplir los siguientes sufijos de nombrado:

| Capa | Ubicación | Sufijo / Patrón de Nombre | Ejemplo |
| :--- | :--- | :--- | :--- |
| **Controlador HTTP** | `app/api/v1/controllers/` | `*_controller.py` | `auth_controller.py`, `jira_controller.py`, `projects_controller.py` |
| **Servicio de Negocio** | `app/services/` | `*_service.py` | `auth_service.py`, `jira_sync_service.py` |
| **Fuente de Datos** | `app/datasources/` | `*_datasource.py` | `jira_datasource.py` |
| **Esquema / DTO** | `app/schemas/` | `*_schema.py` | `auth_schema.py`, `project_schema.py` |
| **Repositorio SQL** | `app/repositories/` | `*_repo.py` / `*_repository.py` | `user_repo.py`, `project_repo.py`, `jira_repo.py` |

---

## 5. Estándares de Git y Control de Versiones

### 5.1 Convención de Mensajes de Commit (Conventional Commits)
Los commits deben escribirse en minúsculas utilizando un prefijo descriptivo:

* **`feat:`** Nuevas características o funcionalidades.  
  *Ejemplo:* `feat: agregar selector de calendario por dia, mes y ano`
* **`fix:`** Corrección de errores o bugs.  
  *Ejemplo:* `fix: corregir manejo de rate limit 429 en callback de oauth`
* **`refactor:`** Cambios de estructura o Clean Architecture sin modificar comportamiento externo.  
  *Ejemplo:* `refactor: separar logica de endpoints a controllers y services`
* **`perf:`** Mejoras significativas de rendimiento.  
  *Ejemplo:* `perf: optimizar sincronizacion de jira con expand=changelog en JQL`
* **`docs:`** Cambios o creación de documentación.  
  *Ejemplo:* `docs: actualizar README y guias de arquitectura`

### 5.2 Protección de Archivos Sensibles
* Queda **estrictamente prohibido** subir los siguientes elementos a Git:
  * Archivos `.env` o secretos de producción.
  * Carpetas de entornos virtuales (`venv/`, `env/`).
  * Archivos compilados o distribuciones (`dist/`, `build/`, `__pycache__/`, `*.pyc`).
