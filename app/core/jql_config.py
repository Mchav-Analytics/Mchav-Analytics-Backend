class JQLQueries:
    """
    Contrato Centralizado de Consultas JQL para el motor analítico.
    Cada query está parametrizada para inyectar variables dinámicas.
    """
    
    # Extracción Delta (Vinculado a HU-013 / RF-023)
    # Extrae los tickets modificados en las últimas 24 horas.
    DELTA_EXTRACTION = "project = '{project_key}' AND updated >= '-24h'"
    
    # Velocidad y Throughput (Vinculado a HU-005 y HU-006 / RF-011 y RF-012)
    # Extrae tickets finalizados en un sprint específico.
    VELOCITY_THROUGHPUT = "project = '{project_key}' AND status = '{status_done}' AND sprint = {sprint_id}"
    
    # Tiempos de Ciclo (Vinculado a HU-007 y HU-008 / RF-013 y RF-014)
    # Extrae tickets resueltos en un rango de fechas.
    TIME_CYCLES = "project = '{project_key}' AND resolutiondate >= '{start_date}' AND resolutiondate <= '{end_date}'"
