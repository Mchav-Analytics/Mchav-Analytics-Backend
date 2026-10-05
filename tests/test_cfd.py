import sys
sys.path.insert(0, '.')
from app.core.database import SessionLocal
import app.models as models
from app.services.flow_service import FlowStateCategorizer, get_issue_flow_timeline, calculate_cfd_and_wip

db = SessionLocal()
try:
    # Test categorizer con estados reales
    cat = FlowStateCategorizer(db, '10000')
    estados = ['Finalizado', 'En curso', 'Por hacer', 'Listo']
    print("Categorización de estados reales:")
    for e in estados:
        print(f'  "{e}" -> {cat.categorize_state(e)}')

    print()

    # Test CFD completo
    result = calculate_cfd_and_wip(db, '10000')
    cfd = result['cfd']
    wip = result['wip']

    print(f'WIP total: {wip["total"]}')

    # Mostrar dias con datos
    dias_con_datos = [d for d in cfd if any(d.get(v, 0) > 0 for v in ['Active','Waiting','Blocked','Done','To Do'])]
    print(f'Dias con datos: {len(dias_con_datos)} de {len(cfd)}')

    if dias_con_datos:
        for d in dias_con_datos[:5]:
            print(f'  {d}')
    else:
        print('  Todos los dias siguen en 0 - revisando issue de muestra...')
        issue = db.query(models.Issue).filter(models.Issue.id_proyecto == '10000').first()
        timeline = get_issue_flow_timeline(issue)
        print(f'  Timeline issue {issue.key_issue}:')
        for t in timeline:
            print(f'    estado={t["state"]}, start={t["start"]}, end={t["end"]}')

finally:
    db.close()
    print("Done.")
