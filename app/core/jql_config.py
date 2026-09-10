# app/core/jql_config.py
# Contrato centralizado de plantillas de consultas JQL (Jira Query Language)
# Define las consultas estructuradas usadas por el motor analítico para la extracción de métricas

class JQLQueries:
    """
    Contrato Centralizado de Consultas JQL para el motor analítico.
    Cada query está parametrizada para inyectar variables dinámicas en tiempo de ejecución.
    """
    
    # Extracción Delta (Vinculado a HU-013 / RF-023)
    # Extrae únicamente los tickets que han sufrido alguna modificación en las últimas 24 horas.
    DELTA_EXTRACTION = "project = '{project_key}' AND updated >= '-24h'"
    
    # Velocidad y Throughput (Vinculado a HU-005 y HU-006 / RF-011 y RF-012)
    # Extrae tickets finalizados pertenecientes a un sprint específico para el cálculo de entregables.
    VELOCITY_THROUGHPUT = "project = '{project_key}' AND status = '{status_done}' AND sprint = {sprint_id}"
    
    # Tiempos de Ciclo (Vinculado a HU-007 y HU-008 / RF-013 y RF-014)
    # Extrae tickets cuya fecha de resolución se encuentra dentro de un rango de fechas determinado.
    TIME_CYCLES = "project = '{project_key}' AND resolutiondate >= '{start_date}' AND resolutiondate <= '{end_date}'"
