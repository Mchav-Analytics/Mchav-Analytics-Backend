import random
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
import app.models as models
from app.services.kpi import calculate_and_save_kpis

def fake_history():
    db = SessionLocal()
    try:
        proyecto = db.query(models.Proyecto).filter(models.Proyecto.key_proyecto == "PA").first()
        if not proyecto:
            print("Proyecto PA no encontrado en DB.")
            return
            
        print("Limpiando KPIs y Sprints anteriores...")
        db.query(models.KpisHistoricos).filter(models.KpisHistoricos.id_proyecto == proyecto.id_proyecto).delete()
        db.query(models.Sprint).filter(models.Sprint.id_proyecto == proyecto.id_proyecto).delete()
        db.commit()
        
        print("Creando 4 Sprints historicos falsos...")
        sprints_falsos = []
        now = datetime.now(timezone.utc)
        
        for i in range(1, 5):
            # Sprint 1: hace 8 semanas, Sprint 2: hace 6 semanas...
            semanas_atras = (5 - i) * 2
            fecha_inicio = now - timedelta(weeks=semanas_atras)
            fecha_fin = fecha_inicio + timedelta(days=14)
            
            sprint_id = f"fake_sprint_{i}"
            sprint = models.Sprint(
                id_sprint=sprint_id,
                id_proyecto=proyecto.id_proyecto,
                nombre=f"Sprint {i} (Historico)",
                estado="closed" if i < 4 else "active",
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                fecha_finalizacion=fecha_fin if i < 4 else None
            )
            db.add(sprint)
            sprints_falsos.append(sprint)
            
        db.commit()
        
        issues = db.query(models.Issue).filter(models.Issue.id_proyecto == proyecto.id_proyecto).all()
        print(f"Modificando fechas de {len(issues)} issues en la base de datos local...")
        
        for issue in issues:
            # Asignar a un sprint falso
            sprint_asignado = random.choice(sprints_falsos)
            issue.id_sprint = sprint_asignado.id_sprint
            
            # Asociar en tabla intermedia (many-to-many)
            issue.sprints.clear()
            issue.sprints.append(sprint_asignado)
            
            # Generar una fecha de creación realista dentro del sprint
            dias_offset = random.randint(1, 10)
            nuevo_created = sprint_asignado.fecha_inicio + timedelta(days=dias_offset)
            issue.created_at = nuevo_created
            
            if issue.status_actual.lower() in ["listo", "done", "terminado"]:
                # Resolved 2 a 12 días después de creado
                dias_resolucion = random.randint(2, 12)
                issue.resolved_at = nuevo_created + timedelta(days=dias_resolucion)
                
            # Ajustar transiciones en el historial
            transiciones = db.query(models.TransicionEstadoIssue).filter(models.TransicionEstadoIssue.id_jira == issue.id_jira).all()
            for t in transiciones:
                # Transición a "En Curso" (Lead -> Cycle)
                if t.estado_nuevo in ["En curso", "In Progress", "21"]:
                    t.fecha_cambio = nuevo_created + timedelta(hours=random.randint(4, 48))
                
                # Transición a "Listo"
                if t.estado_nuevo in ["Listo", "Done", "41"]:
                    t.fecha_cambio = issue.resolved_at if issue.resolved_at else (nuevo_created + timedelta(days=random.randint(2, 12)))
                    
        db.commit()
        print("Fechas y Sprints inyectados con exito en la DB.")
        
        print("Recalculando KPIs...")
        calculate_and_save_kpis(db, proyecto.id_proyecto)
        print("KPIs recalculados a la perfeccion. Abre tu Dashboard!")
        
    finally:
        db.close()

if __name__ == "__main__":
    fake_history()
