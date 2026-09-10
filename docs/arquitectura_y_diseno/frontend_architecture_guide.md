# 📘 Guía Maestra del Frontend (Arquitectura MCHAV)

Este documento explica **paso a paso y archivo por archivo** cómo funciona toda la cara visible de tu aplicación (el Frontend en React) y cómo se comunica con el motor interno (el Backend en FastAPI). Úsalo como tu mapa de estudio para entender o modificar el código en el futuro.

---

## 🏗️ 1. Estructura General

El proyecto Frontend está construido con **React (Vite)** y utiliza **TailwindCSS** para los estilos. Todo el código vive en la carpeta `src/`.

La comunicación fluye así:
`Tus Clics en la UI` ➡️ `Manejadores de Eventos (App.jsx)` ➡️ `Servicio API (api.js)` ➡️ `Backend (Python/FastAPI)`.

---

## 🔌 2. El Puente de Comunicación: `src/services/api.js`

Este es el archivo **más importante** para entender cómo el Frontend habla con el Backend. 
No hacemos peticiones web ("fetch") crudas en cada botón; en su lugar, centralizamos todas las llamadas a la API de FastAPI aquí usando **Axios**.

```javascript
// Ejemplo de cómo se ve el código en api.js
import axios from 'axios';

// 1. Configuramos la dirección base del Backend
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

// 2. Creamos módulos para cada "Tema" de la aplicación:
export const projectService = {
  // Pide al backend la lista de proyectos en la base de datos PostgreSQL
  getProjects: () => axios.get(`${API_URL}/projects/`).then(res => res.data),
  
  // Pide al backend los KPIs calculados de un proyecto en específico
  getKpis: (projectId) => axios.get(`${API_URL}/projects/${projectId}/kpis`).then(res => res.data),
};
```
**¿Por qué es clave?** Si alguna vez el backend cambia una URL (ej. de `/projects/` a `/proyectos/`), solo tienes que cambiarlo aquí, y toda la interfaz web se actualizará automáticamente.

---

## 🧠 3. El Cerebro del Estado: `src/App.jsx`

Si `api.js` es el puente, `App.jsx` es el **Cerebro**. 
Es el componente Padre de toda la aplicación web (después del Login).

**Responsabilidades principales:**
1. **Control de Rutas:** Decide si estás en la pantalla de inicio de sesión (`/`) o en la aplicación principal (`/dashboard`).
2. **Memoria Global (States):** Guarda los datos que se descargan del backend usando `useState`.
   - `const [kpis, setKpis] = useState([]);` (Guarda las estadísticas)
   - `const [activeTab, setActiveTab] = useState('dashboard');` (Guarda qué pestaña de la barra lateral estás viendo).
3. **Filtros e Inteligencia:** Aquí vive la lógica del filtro de fechas (el menú de "Últimos 30 días" que arreglamos hoy).

**¿Cómo funciona un ciclo de vida aquí?**
1. Cuando abres la página, el `useEffect` (un hook de React que se ejecuta al cargar) dispara la función `fetchProjects()`.
2. `fetchProjects` usa `api.js` para llamar al backend.
3. El backend responde con un JSON de proyectos.
4. `App.jsx` guarda esos proyectos en `setProjects(data)`.
5. Al guardarlos, React "reacciona" (de ahí su nombre) y le inyecta esos proyectos a la barra superior (`Topbar.jsx`) para que los muestre en el menú desplegable.

---

## 🖼️ 4. Las Vistas (Views)

La carpeta `src/views/` contiene los "pantallazos" grandes de la aplicación. `App.jsx` decide cuál mostrar dependiendo del botón de la barra lateral que oprimas.

### A. `DashboardView.jsx` (El panel de métricas)
Este archivo se encarga 100% de la **visualización**. No descarga datos; simplemente recibe los `kpis` que `App.jsx` ya descargó y los dibuja usando la librería **Recharts**.
* Contiene componentes personalizados como `InfoTooltip` (las burbujas educativas) y `TrendBadge` (las flechas rojas y verdes de rendimiento).
* Mapea los datos del backend a gráficos: 
  `<Area dataKey="cycle_time_promedio_dias" />` le dice al gráfico que busque esa palabra exacta en el JSON que mandó el backend y dibuje una línea con ese valor.

### B. `SystemSyncTab.tsx` (La Auditoría ETL)
Es la pestaña "Sincronización". 
* Cuando oprimes el botón morado gigante ("Sincronizar Manualmente Ahora"), este archivo llama a `jiraService.triggerSync()`.
* Esto envía un `POST /api/jira/sync` al backend. 
* El backend de Python arranca un "Background Task" (Tarea en segundo plano) y empieza a robarse los datos de Jira.

### C. `UserManagementTab.tsx`
El panel de "Seguridad y RBAC". Aquí se muestra la tabla de usuarios, roles y contraseñas. Interactúa con las rutas `/users/` del backend para crear o editar compañeros de equipo.

---

## 🧩 5. Componentes Reutilizables (Components)

La carpeta `src/components/common/` guarda las piezas de Lego de la interfaz que se repiten en todos lados.

* **`MainLayout.jsx`**: Es el "marco" de la página. Tiene a la izquierda el `Sidebar`, arriba el `Topbar` y en el centro un hueco (`{children}`) donde `App.jsx` mete la vista correspondiente (Dashboard, Users, etc.).
* **`Sidebar.jsx`**: La barra lateral oscura. Solo tiene botones que cambian la variable `activeTab` de `App.jsx`.
* **`Topbar.jsx`**: La barra superior. Aquí es donde están los filtros desplegables de Proyecto y Fecha.

---

## 🔄 El Flujo Completo: Un Ejemplo Práctico (Filtro de Fechas)

Para que entiendas cómo se conecta todo, veamos qué pasó cuando creamos el filtro de "Últimos 30 días":

1. **El Usuario Interactúa (`Topbar.jsx`)**: Seleccionas "Últimos 30 días" en el menú desplegable. El `onChange` de React captura tu clic y ejecuta `setDateFilter('30d')`.
2. **El Cerebro lo Procesa (`App.jsx`)**: Como `App.jsx` es el dueño de la variable `dateFilter`, se da cuenta del cambio. Ejecuta un bloque inteligente llamado `useMemo`.
3. **El Cerebro Filtra**: El `useMemo` revisa la enorme lista de `kpis` (que trajo del backend previamente) y esconde todos los que tienen una fecha mayor a 30 días. Luego crea una nueva sublista llamada `filteredKpis`.
4. **La Vista se Actualiza (`DashboardView.jsx`)**: `App.jsx` le dice a `DashboardView`: *"Oye, aquí están los nuevos KPIs filtrados"*. El `DashboardView` recibe la nueva lista y la inyecta automáticamente en `<ComposedChart data={filteredKpis}>`.
5. **Resultado Visual**: El gráfico se anima y contrae sus barras en milisegundos sin necesidad de molestar al backend de nuevo.

---

## 🚀 Resumen del Backend Asociado (FastAPI)

Todo lo anterior no serviría de nada sin el backend. El archivo clave en Python que alimenta todo esto es:
* **`app/api/v1/endpoints/projects.py`**: Aquí viven las rutas `@router.get("/{proyecto_id}/kpis")`. Cuando la UI pide datos, esta función hace un `SELECT * FROM kpis_historicos WHERE id_proyecto = X` en la base de datos PostgreSQL y devuelve un JSON al frontend.

---

*Estudia este documento junto con el código fuente. Si entiendes la relación `App.jsx` -> `Views` -> `api.js` -> `FastAPI`, ¡ya dominas el 90% de la arquitectura de la aplicación!*
