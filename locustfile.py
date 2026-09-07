# ============================================================================
# LOCUSTFILE — PRUEBAS DE CARGA Y ESTRÉS PARA MCHAV ANALYTICS API (SEMANA 4)
# ============================================================================
# Simula el comportamiento concurrente de usuarios ejecutando consultas de:
# 1. Monitoreo de Salud / Diagnóstico (/healthz)
# 2. Listado de Proyectos (/api/v1/projects)
# 3. Métricas de Salud del Sprint (/api/v1/projects/PROJ-01/health)
# 4. Matriz 4 Cuadrantes (/api/v1/developers/matrix)
# 5. Listado de Desarrolladores (/api/v1/developers)
# 6. Auditoría de Sync Logs (/api/v1/jira/sync/logs)

from locust import HttpUser, task, between

class AnalyticsUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        """Inicialización de sesión simulada"""
        self.client.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })

    @task(3)
    def test_health_check(self):
        """Consulta periódica del estado del servidor y latencia"""
        self.client.get("/healthz", name="01. Health Check (/healthz)")

    @task(5)
    def test_get_projects(self):
        """Consulta del catálogo de proyectos activos"""
        self.client.get("/api/v1/projects", name="02. Listar Proyectos (/projects)")

    @task(4)
    def test_sprint_health_dashboard(self):
        """Consulta del Dashboard de Salud del Sprint y Predictibilidad"""
        self.client.get(
            "/api/v1/projects/PROJ-01/health", 
            name="03. Salud del Sprint (/projects/{id}/health)"
        )

    @task(4)
    def test_team_matrix_dashboard(self):
        """Consulta de la Matriz de Rendimiento de 4 Cuadrantes"""
        self.client.get(
            "/api/v1/developers/matrix?proyecto_id=PROJ-01", 
            name="04. Matriz 4 Cuadrantes (/developers/matrix)"
        )

    @task(2)
    def test_developers_list(self):
        """Consulta de la lista de desarrolladores"""
        self.client.get(
            "/api/v1/developers", 
            name="05. Lista Desarrolladores (/developers)"
        )

    @task(2)
    def test_sync_logs(self):
        """Consulta del historial de auditoría de sincronización ETL"""
        self.client.get("/api/v1/jira/sync/logs", name="06. Sync Logs (/jira/sync/logs)")
