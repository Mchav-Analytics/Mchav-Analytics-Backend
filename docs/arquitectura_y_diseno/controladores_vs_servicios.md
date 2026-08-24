# Arquitectura: Controladores vs Servicios 🏛️

En nuestra arquitectura de backend (FastAPI), separamos las responsabilidades usando un patrón muy limpio que divide el código en dos carpetas clave: **Endpoints (Controladores)** y **Servicios (Services)**. 

El propósito de esta separación es mantener el código organizado, testeable y escalable.

---

## 🚪 1. Los Controladores (La recepción del hotel)
📍 **Ubicación:** Carpeta `app/api/v1/endpoints/`

En FastAPI no los llamamos explícitamente "controllers", sino `endpoints` o `routers`. Imagínalos como los recepcionistas del sistema.

* **Su trabajo:** Recibir la petición HTTP de React (el Frontend) o de Jira (el Webhook), extraer los parámetros de la URL, verificar que el usuario tenga sesión válida, y devolver un código de éxito (200) o de error (400, 500).
* **Lo que NO deben hacer:** No deben tener cálculos matemáticos gigantes ni código de cientos de líneas. Si el trabajo es pesado, deben delegar la tarea a un *Servicio*.

### Ejemplo de Controlador (`app/api/v1/endpoints/jira.py`):
```python
@router.post("/sync")
async def trigger_jira_sync(request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    user = check_user_exists(db, get_current_user_id(request))
    
    # El Controlador (Recepcionista) NO hace el trabajo sucio. 
    # Simplemente le pasa la tarea pesada al "Servicio" y despide al cliente rápido.
    background_tasks.add_task(run_jira_sync_task, user.id_usuario)
    
    return {"message": "Sincronización iniciada en segundo plano"}
```

---

## ⚙️ 2. Los Servicios (La cocina del restaurante)
📍 **Ubicación:** Carpeta `app/services/`

Aquí es donde vive el código largo, complejo y la verdadera "lógica de negocio".

* **Su trabajo:** Hacer los cálculos matemáticos (como el Cycle Time), procesar miles de líneas de texto, o conectarse a otros servidores (como la API externa de Jira).
* En nuestro proyecto tenemos dos servicios principales:
  1. `jira_sync.py`: Se encarga de conectarse con Atlassian, mapear el JSON gigantesco y guardarlo en la base de datos PostgreSQL.
  2. `kpi.py`: Es nuestra calculadora gigante. Se encarga de recorrer todos los tickets de la base de datos, sumar los días que estuvieron en "In Progress", y guardar esos promedios (Lead Time, Throughput, etc.).

### Ejemplo de Servicio (`app/services/kpi.py`):
```python
# Esta es una función de un SERVICIO. Nota que no tiene @router ni sabe nada de HTTP.
def calculate_and_save_kpis(db: Session, project_id: str):
    tickets = db.query(Issue).filter(Issue.id_proyecto == project_id).all()
    # ... hace toda la matemática pesada (Lead Time, Cycle Time, Throughput)
    # ...
    db.add(kpi_calculado)
    db.commit()
```

---

## 🤝 ¿Cómo se conectan? (El Flujo Unidireccional)

La regla de oro de nuestra arquitectura es que **la información viaja en una sola dirección**:

1. **Petición Externa:** El Frontend manda un HTTP POST o GET.
2. **Recepción:** El **Controlador** (`endpoints/jira.py`) lo recibe, saca los datos de la petición y autentica al usuario.
3. **Delegación:** El Controlador llama a la función correspondiente del **Servicio** (ej. `services/jira_sync.py`).
4. **Procesamiento:** El Servicio hace el trabajo pesado y modifica la **Base de Datos** usando los modelos (`models.py`).
5. **Respuesta:** El Controlador le dice al Frontend: *"Listo, todo salió bien"*.

### ¿Por qué hacerlo así?
Esta separación te permite, por ejemplo, cambiar mañana de React a una App Móvil en Android, o crear un bot de Discord que pida métricas, **sin tener que tocar la carpeta `services/`**. La lógica matemática sigue siendo exactamente la misma sin importar qué "recepcionista" atienda al cliente.
