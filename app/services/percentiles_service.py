# app/services/percentiles_service.py
import statistics
from collections import defaultdict
from typing import List, Dict, Any

def calculate_percentiles(raw_issues: List[Any]) -> List[Dict[str, Any]]:
    """
    [HU-014] Calcula los percentiles (P25, P50, P75, P90) y promedios para Lead Time y Cycle Time 
    agrupados por tipo de tarea (issue_type).
    
    Args:
        raw_issues: Lista de tuplas/objetos retornada por la consulta SQLAlchemy.
                    Se asume estructura: (issue_type, lead_time, cycle_time)
        
    Returns:
        Lista de diccionarios con las métricas calculadas por tipo de tarea.
    """
    # Usamos defaultdict para agrupar fácilmente los tiempos por tipo de tarea
    grouped_data = defaultdict(lambda: {"lead_times": [], "cycle_times": []})
    
    for row in raw_issues:
        # Extraemos los valores (soportando tanto tuplas como objetos ORM/Row)
        issue_type = row[0]
        lead_time = row[1]
        cycle_time = row[2]
        
        # Estandarizamos el nombre del tipo de tarea (Story, Bug, Epic, etc.)
        i_type = str(issue_type).capitalize() if issue_type else "Desconocido"
        
        # Agregamos los tiempos a las listas correspondientes
        grouped_data[i_type]["lead_times"].append(float(lead_time or 0.0))
        grouped_data[i_type]["cycle_times"].append(float(cycle_time or 0.0))

    results = []
    
    for i_type, times in grouped_data.items():
        lt_list = times["lead_times"]
        ct_list = times["cycle_times"]
        count = len(lt_list)
        
        # [CA-03]: El sistema exige un mínimo de 5 muestras dentro de los últimos 15 días
        has_enough_data = count >= 5
        
        type_result = {
            "issue_type": i_type,
            "has_enough_data": has_enough_data,
            "count": count,
            "lead_time": {},
            "cycle_time": {}
        }
        
        # [CA-02]: Calcular siempre el promedio si hay al menos 1 muestra
        if count > 0:
            type_result["lead_time"]["avg"] = round(statistics.mean(lt_list), 2)
            type_result["cycle_time"]["avg"] = round(statistics.mean(ct_list), 2)
        else:
            type_result["lead_time"]["avg"] = 0.0
            type_result["cycle_time"]["avg"] = 0.0
            
        # [CA-01]: Calcular percentiles solo si cumple el mínimo (CA-03)
        if has_enough_data:
            # statistics.quantiles(data, n=100) divide los datos en 100 intervalos (0 a 99)
            # Retorna 99 cortes. El índice 24 corresponde al P25, el 49 al P50, etc.
            # Usamos method='inclusive' que es más seguro para muestras pequeñas.
            
            # Cálculos para Lead Time
            lt_quantiles = statistics.quantiles(lt_list, n=100, method='inclusive')
            type_result["lead_time"]["p25"] = round(lt_quantiles[24], 2)
            type_result["lead_time"]["p50"] = round(lt_quantiles[49], 2)
            type_result["lead_time"]["p75"] = round(lt_quantiles[74], 2)
            type_result["lead_time"]["p90"] = round(lt_quantiles[89], 2)
            
            # Cálculos para Cycle Time
            ct_quantiles = statistics.quantiles(ct_list, n=100, method='inclusive')
            type_result["cycle_time"]["p25"] = round(ct_quantiles[24], 2)
            type_result["cycle_time"]["p50"] = round(ct_quantiles[49], 2)
            type_result["cycle_time"]["p75"] = round(ct_quantiles[74], 2)
            type_result["cycle_time"]["p90"] = round(ct_quantiles[89], 2)
            
        results.append(type_result)
        
    return results
