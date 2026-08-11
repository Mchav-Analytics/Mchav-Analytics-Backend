# Protección de Endpoints: Middlewares vs Inyección de Dependencias 🛡️

En nuestro backend de FastAPI, **Sí tenemos los endpoints protegidos**, pero hemos decidido **NO usar "Middlewares"** globales para la autenticación. 

En su lugar, empleamos un patrón mucho más granular, moderno y afín al framework de FastAPI llamado **Inyección de Dependencias** (o llamadas directas de seguridad por ruta). A continuación, se detalla el razonamiento detrás de esta decisión técnica.

---

## 🛑 ¿Por qué NO usamos Middlewares para Autenticación?

Un Middleware actúa como un "guardia de seguridad gigante" parado en la puerta principal del servidor. Revisa las credenciales de **todas** las peticiones que entran, sin importar a qué ruta específica se dirijan.

### El Problema en FastAPI
1. **Falta de Contexto:** El middleware se ejecuta en un punto tan temprano del ciclo de vida de la petición que FastAPI ni siquiera sabe a qué endpoint se dirige el usuario. 
2. **Excepciones Engorrosas:** Si requieres rutas públicas (como el Login `/auth/login`) o rutas de sistema a sistema (como el Webhook de Jira `/api/v1/jira/webhook` que no envía cookies de sesión), tendrías que llenar el middleware de condicionales `if` ("Si la ruta contiene 'webhook', entonces sáltate la seguridad"). Esto es frágil y difícil de mantener.
3. **Incompatibilidad con Swagger:** Los middlewares globales no se comunican de forma nativa con el autogenerador de Swagger (OpenAPI) de FastAPI, por lo que tus rutas seguras no aparecerán con el "candadito" en la interfaz visual.

---

## 🟢 Nuestra Solución: Seguridad por Ruta (Granular)

En lugar del guardia global, hemos colocado un "escáner de huellas digitales" **exclusivamente en las puertas de las rutas que requieren protección**.

Si observas el archivo de controladores (`app/api/v1/endpoints/jira.py`), verás que cada ruta segura inicia exigiendo la identidad del usuario mediante una función de validación:

```python
@router.post("/sync")
async def trigger_jira_sync(request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # ⬇️ Esta línea es nuestro escudo de seguridad (Escáner de huella)
    user_id = get_current_user_id(request)
    
    # Si la cookie (HMAC) es inválida o no existe, la función get_current_user_id() 
    # detiene la ejecución inmediatamente y lanza un Error HTTP 401 (Unauthorized). 
    # El código de abajo JAMÁS se ejecutará si el usuario es un impostor.
    
    background_tasks.add_task(run_jira_sync_task, user_id)
    return {"message": "Sincronización iniciada en segundo plano"}
```

### Ventajas de esta Arquitectura
1. **Control Granular Perfecto:** Podemos tener endpoints 100% públicos mezclados con endpoints ultrasecretos en el mismo archivo sin necesidad de escribir complejas reglas de exclusión.
2. **Seguro contra Webhooks de Terceros:** La ruta del Webhook de Jira (`POST /webhook`) no contiene esta validación de usuario porque los servidores automáticos de Atlassian no poseen nuestra cookie de sesión HMAC. Si hubiéramos implementado un Middleware, el webhook rebotaría contra el servidor constantemente.
3. **Escalabilidad hacia `Depends()`:** Este patrón es el paso previo a la verdadera "Inyección de Dependencias" (`Depends`) de FastAPI. Si en el futuro requerimos roles avanzados (Ej: "Solo Administradores pueden sincronizar"), podemos transformar `get_current_user_id` en una dependencia inyectable que bloquee peticiones basadas en niveles de acceso y que se refleje instantáneamente en la interfaz de Swagger.
