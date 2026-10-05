import sys
sys.path.insert(0, '.')
from app.core.database import SessionLocal
import app.models as models

db = SessionLocal()
try:
    project_id = '10000'
    
    # 1. Buscar sprint activo
    sprint = db.query(models.Sprint).filter(
        models.Sprint.id_proyecto == project_id,
        models.Sprint.estado == 'active'
    ).first()
    
    if not sprint:
        sprint = db.query(models.Sprint).filter(
            models.Sprint.id_proyecto == project_id,
            models.Sprint.estado == 'closed'
        ).order_by(models.Sprint.fecha_fin.desc()).first()
    
    if not sprint:
        print("NO HAY SPRINT!")
    else:
        print(f"Sprint: id={sprint.id_sprint}, nombre={sprint.nombre}, estado={sprint.estado}")
        print(f"  fecha_inicio={sprint.fecha_inicio}, fecha_fin={sprint.fecha_fin}")
        
        # 2. Issues del sprint
        issues = db.query(models.Issue).filter(models.Issue.id_sprint == sprint.id_sprint).all()
        print(f"\nIssues con id_sprint={sprint.id_sprint}: {len(issues)}")
        
        # Ver todos los issues del proyecto
        all_issues = db.query(models.Issue).filter(models.Issue.id_proyecto == project_id).all()
        print(f"Issues totales del proyecto: {len(all_issues)}")
        
        # Ver distribucion de id_sprint
        sprint_ids = {}
        for i in all_issues:
            k = i.id_sprint or 'None'
            sprint_ids[k] = sprint_ids.get(k, 0) + 1
        print(f"\nDistribucion id_sprint:")
        for k, v in sorted(sprint_ids.items(), key=lambda x: -x[1])[:5]:
            print(f"  id_sprint={k}: {v} issues")
        
        # Ver issues resueltos del sprint
        done_statuses = {"done", "listo", "resuelto", "resolved", "cerrado", "closed", "finalizado", "completado"}
        for issue in issues[:5]:
            status = (issue.status_actual or "").lower().strip()
            in_done = status in done_statuses
            print(f"\n  Issue {issue.key_issue}: status='{issue.status_actual}' lower='{status}' in_done={in_done} resolved_at={issue.resolved_at}")

finally:
    db.close()
    print("\nDone.")
