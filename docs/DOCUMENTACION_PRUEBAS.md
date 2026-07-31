# 🧪 Documentación Técnica de Pruebas Automatizadas y Cobertura (Pytest)

Este documento contiene la especificación completa de la suite de pruebas unitarias y de integración del sistema **MCHAV Analytics Backend**, desarrollada con **Pytest**, **Pytest-Cov** y **Pytest-Asyncio**.

---

## 📊 Resumen Ejecutivo de Cobertura de Código

| Métrica | Valor Obtenido | Estado |
| :--- | :---: | :---: |
| **Pruebas Automatizadas Ejecutadas** | **94 de 94 Pasadas (100% éxito)** | ✅ |
| **Porcentaje de Cobertura Global (`TOTAL`)** | **90%** | ✅ Meta Alcanzada |
| **Módulos con Cobertura >= 90%** | **17 módulos** | ✅ |
| **Advertencias / Warnings en Consola** | **0 Warnings** | ✅ |
| **Estrategia de Pruebas** | Mocks de `httpx` y `SQLAlchemy` sin dependencias externas | ✅ |

---

## 📑 Reporte de Cobertura por Archivo y Módulo (`pytest-cov`)

```text
Name                                            Stmts   Miss  Cover   Missing
-----------------------------------------------------------------------------
app/__init__.py                                     0      0   100%
app/api/__init__.py                                 0      0   100%
app/api/v1/__init__.py                              0      0   100%
app/api/v1/api.py                                   7      0   100%
app/api/v1/controllers/__init__.py                  5      0   100%
app/api/v1/controllers/auth_controller.py          53      8    85%
app/api/v1/controllers/jira_controller.py         124      9    93%
app/api/v1/controllers/jql_controller.py           22      0   100%
app/api/v1/controllers/projects_controller.py      67      1    99%
app/api/v1/deps.py                                 24      2    92%
app/core/cache.py                                  24      0   100%
app/core/config.py                                 15      0   100%
app/core/database.py                               12      0   100%
app/core/jql_config.py                              4      0   100%
app/core/security.py                               56      7    88%
app/datasources/jira_datasource.py                 63      6    90%
app/main.py                                        59     22    63%
app/models/auth.py                                 34      0   100%
app/models/jira.py                                 57      0   100%
app/models/metrics.py                              27      0   100%
app/repositories/auth_repo.py                      10      0   100%
app/repositories/base.py                           39      4    90%
app/repositories/jira_repo.py                      80     17    79%
app/repositories/metrics_repo.py                   15      2    87%
app/schemas/auth_schema.py                         25      0   100%
app/schemas/jql.py                                 18      0   100%
app/schemas/project_schema.py                      13      0   100%
app/services/auth_service.py                       94      8    91%
app/services/jira_sync_service.py                 189     33    83%
app/services/kpi.py                                58      6    90%
-----------------------------------------------------------------------------
TOTAL                                            1204    125    90%
```

---

## 🧹 Gestión de Advertencias y Deprecaciones (0 Warnings)

Para garantizar una salida limpia e identificar errores de forma precisa, se refactorizó el código base y se configuraron las supresiones en `pytest.ini`:

1. **Migración de `declarative_base` en SQLAlchemy**:
   - `app/core/database.py` fue actualizado desde `sqlalchemy.ext.declarative` hacia `sqlalchemy.orm.declarative_base` para compatibilidad con **SQLAlchemy 2.0+**.

2. **Fechas UTC Conscientes de Zona Horaria (Python 3.12)**:
   - `app/services/jira_sync_service.py` reemplazó todas las invocaciones depreciadas de `datetime.utcnow()` por `datetime.now(timezone.utc)`.

3. **Configuración de Archivos `pytest.ini`**:
   - Se crearon y alinearon archivos `pytest.ini` tanto en la raíz de la workspace (`Proyecto Mchav/pytest.ini`) como en el subdirectorio del backend (`Mchav-Backend/pytest.ini`).
   - Se configuró la sección `filterwarnings` para ignorar advertencias de obsolescencia de librerías de terceros (Pydantic v2, Starlette y HTTPX).

---

## 🛠️ Organización de Archivos de Prueba en `tests/` (Nomenclatura y Archivos .py en Español)

Toda la suite de pruebas (**94 funciones de prueba**) utiliza un esquema de **nombres sencillos y descriptivos en español** tanto para los **archivos `.py`** como para las funciones de prueba, organizados en **13 módulos de prueba** limpios y consolidados:

1. **`tests/test_autenticacion_controlador.py`**:
   - Pruebas para los endpoints de login, callback de Atlassian OAuth, inicio de sesión local y credenciales de Jira API Token.
2. **`tests/test_autenticacion_servicio.py`**:
   - Pruebas para la generación y validación de tokens de estado CSRF, intercambio de tokens con Atlassian y firmado HMAC de sesión.
3. **`tests/test_jira_controlador.py`**:
   - Pruebas para los endpoints de métricas de Jira, webhooks en tiempo real y disparo de sincronizaciones en segundo plano.
4. **`tests/test_jql_controlador.py`**:
   - Pruebas para los endpoints de consulta JQL de extracción delta, velocity, throughput y tiempos de ciclo.
5. **`tests/test_proyectos_controlador.py`**:
   - Pruebas para la consulta de sprints, estados únicos y guardado de reglas de mapeo de proyectos.
6. **`tests/test_kpis_y_metricas.py`**:
   - Pruebas para la consulta de KPIs históricos, listado de proyectos y sprints.
7. **`tests/test_fuente_datos_jira.py`**:
   - Pruebas de la fuente de datos `JiraDatasource` con la estrategia de 3 capas y descarga de historial de transiciones.
8. **`tests/test_sincronizacion_jira.py`**:
   - Pruebas unitarias para el motor de sincronización ETL asíncrono (`run_jira_sync_task`, `sync_projects`, `sync_issues_for_project`).
9. **`tests/test_seguridad_y_permisos.py`**:
   - Pruebas del middleware de autenticación dual (Cookie firmada + Bearer Token), verificación HMAC e inspección de usuarios.
10. **`tests/test_repositorios_y_modelos.py`**:
    - Pruebas para los repositorios ORM (`CRUDBase`, `UserRepo`, `ProjectRepo`, `IssueRepo`, `SprintRepo`, `MappingRepo`, `KpiRepo`).
11. **`tests/test_persistencia_y_paginacion.py`**:
    - Pruebas para la memoria caché TTL (`ShortLivedCache`), persistencia SQLite en memoria y paginación/ordenamiento.
12. **`tests/test_tiempo_de_ciclo.py`**:
    - Pruebas matemáticas y algorítmicas para el cálculo de Lead Time, Cycle Time, Throughput y Velocity.
13. **`tests/test_servidor_principal.py`**:
    - Pruebas para el mensaje de bienvenida en la raíz y la ejecución de eventos de inicio del servidor (`startup_event`).

---

## 🚀 Comandos de Ejecución

Los comandos de prueba se pueden ejecutar indistintamente desde la raíz (`Proyecto Mchav`) o desde la carpeta del backend (`Mchav-Backend`):

### 1. Ejecutar todas las pruebas del Backend:
```bash
pytest
```

### 2. Ejecutar pruebas con reporte de cobertura en consola:
```bash
pytest --cov=app --cov-report=term-missing
```

### 3. Generar reporte HTML navegable de cobertura:
```bash
pytest --cov=app --cov-report=html
```
*(Abre el archivo `htmlcov/index.html` en tu navegador para ver la línea exacta probada por cada test).*
