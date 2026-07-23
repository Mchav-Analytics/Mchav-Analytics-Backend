import asyncio
import httpx
from app.core.database import SessionLocal
import app.models as models
from app.services.jira_sync_service import get_jira_auth_credentials, run_jira_sync_task

async def populate_jira_cloud():
    db = SessionLocal()
    user = db.query(models.User).first()
    if not user:
        print("No hay usuario autenticado en la base de datos.")
        return

    base_jira_url, headers = get_jira_auth_credentials(db, user)
    base_agile_url = base_jira_url.replace("/rest/api/3", "/rest/agile/1.0")

    print(f"Conectando a Jira Cloud en {base_jira_url}...")

    async with httpx.AsyncClient(timeout=60.0) as client:
        # 1. Obtener el tablero del proyecto PA (Prueba ASD)
        boards_res = await client.get(f"{base_agile_url}/board?projectKeyOrId=PA", headers=headers)
        if boards_res.status_code != 200:
            print(f"Error buscando tableros para PA: {boards_res.text}")
            return
            
        boards = boards_res.json().get("values", [])
        if not boards:
            print("No se encontró un tablero Agile para el proyecto PA (Prueba ASD).")
            return
            
        board_id = boards[0].get("id")
        print(f"Tablero encontrado para Prueba ASD (PA): Board ID {board_id}")

        # 2. Crear Sprints reales en Jira Cloud (Nombres < 30 caracteres)
        sprint_names = [
            "PA Sprint 3",
            "PA Sprint 4",
            "PA Sprint 5",
            "PA Sprint 6"
        ]
        
        created_sprints = []
        for name in sprint_names:
            sprint_payload = {
                "name": name,
                "originBoardId": board_id
            }
            res_sp = await client.post(f"{base_agile_url}/sprint", headers=headers, json=sprint_payload)
            if res_sp.status_code in [200, 201]:
                sp_data = res_sp.json()
                created_sprints.append(sp_data)
                print(f" -> Creado Sprint en Jira Cloud: {sp_data.get('name')} (ID: {sp_data.get('id')})")
            else:
                print(f"Advertencia creando sprint '{name}': {res_sp.text}")

        # 3. Crear Tickets reales en Jira Cloud usando el issuetype 'Tarea'
        tasks_pool = [
            "Diseñar interfaz web de métricas de rendimiento",
            "Configurar autenticación OAuth 2.0 con Atlassian",
            "Optimizar consultas SQL en backend de FastAPI",
            "Implementar exportador de reportes en PDF",
            "Configurar contenedor Docker Compose para producción",
            "Integrar sistema de caché en memoria Redis",
            "Refactorizar controladores siguiendo Clean Architecture",
            "Mejorar accesibilidad web WCAG 2.1 AAA",
            "Corregir bug de token en refresco de sesión",
            "Crear script de sincronización automática ETL",
            "Añadir soporte para migración Atlassian Change 2046",
            "Validar llaves foráneas en base de datos PostgreSQL"
        ]

        created_issues_keys = []
        for summary in tasks_pool:
            issue_payload = {
                "fields": {
                    "project": { "key": "PA" },
                    "summary": summary,
                    "issuetype": { "name": "Tarea" },
                    "description": {
                        "type": "doc",
                        "version": 1,
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [
                                    { "type": "text", "text": "Ticket real generado en Jira Cloud para MCHAV Analytics." }
                                ]
                            }
                        ]
                    }
                }
            }
            res_iss = await client.post(f"{base_jira_url}/issue", headers=headers, json=issue_payload)
            if res_iss.status_code in [200, 201]:
                iss_data = res_iss.json()
                created_issues_keys.append(iss_data.get("key"))
                print(f" -> Creado Ticket real en Jira Cloud: {iss_data.get('key')}")
            else:
                print(f"Advertencia creando ticket: {res_iss.text}")

        # 4. Asignar Tickets a Sprints en Jira Cloud
        if created_sprints and created_issues_keys:
            chunk_size = max(1, len(created_issues_keys) // len(created_sprints))
            for idx, sp in enumerate(created_sprints):
                sp_id = sp.get("id")
                assigned_keys = created_issues_keys[idx * chunk_size : (idx + 1) * chunk_size]
                if assigned_keys:
                    move_payload = { "issues": assigned_keys }
                    res_mv = await client.post(f"{base_agile_url}/sprint/{sp_id}/issue", headers=headers, json=move_payload)
                    if res_mv.status_code in [200, 204]:
                        print(f" -> Asignados tickets {assigned_keys} al Sprint {sp.get('name')}")
                    else:
                        print(f"Advertencia asignando tickets a sprint {sp_id}: {res_mv.text}")

    db.close()
    print("\n=== POBLAMIENTO EN JIRA CLOUD FINALIZADO CON ÉXITO ===")

if __name__ == "__main__":
    asyncio.run(populate_jira_cloud())
    print("\nIniciando sincronización ETL automática desde Jira Cloud hacia la base de datos...")
    run_jira_sync_task(1)
