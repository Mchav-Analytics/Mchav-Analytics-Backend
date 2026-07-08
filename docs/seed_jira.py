import json
import random
import time
import urllib.request
import urllib.error
import base64

# ==========================================
# 🛑 CONFIGURACIÓN
# ==========================================
JIRA_URL = "https://beltrancamilo592.atlassian.net"
JIRA_EMAIL = "salamancamai12@gmail.com"
JIRA_API_TOKEN = "<TU_API_TOKEN_AQUI>"
PROJECT_KEY = "PA" 

# ==========================================
# DATOS DE PRUEBA
# ==========================================
TITLES = [
    "Implementar login de usuarios", "Corregir bug de pasarela",
    "Diseñar vista de métricas", "Optimizar queries ETL",
    "Redactar documentación técnica", "Configurar CI/CD",
    "Crear endpoints en FastAPI", "Actualizar Tailwind CSS a v4",
    "Refactorizar Sidebar", "Investigar caída del servidor nocturno",
    "Integración con API de Atlassian", "Sincronizador automático no funciona",
    "Añadir paginación a la tabla de logs", "Mejorar accesibilidad WCAG"
]

def get_headers():
    auth_str = f"{JIRA_EMAIL}:{JIRA_API_TOKEN}"
    b64_auth_str = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")
    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Basic {b64_auth_str}"
    }

def create_jira_issue(summary, issue_type="Tarea"):
    url = f"{JIRA_URL}/rest/api/3/issue"
    
    # Asignar Story Points aleatorios (1, 2, 3, 5, 8)
    story_points = random.choice([1, 2, 3, 5, 8])

    data = {
        "fields": {
            "project": {"key": PROJECT_KEY},
            "summary": summary,
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {"type": "text", "text": f"Este ticket simula tener {story_points} Story Points. Generado por script."}
                        ]
                    }
                ]
            },
            "issuetype": {"name": issue_type},
            "customfield_10016": float(story_points) # Campo exacto de Story Points en Jira Cloud
        }
    }

    json_data = json.dumps(data).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=json_data, headers=get_headers(), method="POST")
        with urllib.request.urlopen(req) as response:
            if response.status == 201:
                res_body = json.loads(response.read().decode('utf-8'))
                issue_key = res_body.get("key")
                print(f"\n[NUEVO] Creado {issue_key} ({issue_type}) con {story_points} Puntos")
                return issue_key
    except urllib.error.HTTPError as e:
        print(f"[ERROR] HTTP {e.code} al crear: {e.read().decode('utf-8')}")
    except Exception as e:
        print(f"[ERROR INTERNO] {str(e)}")
    return None

def transition_issue(issue_key, transition_id, transition_name):
    url = f"{JIRA_URL}/rest/api/3/issue/{issue_key}/transitions"
    data = {
        "transition": {
            "id": transition_id
        }
    }
    json_data = json.dumps(data).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=json_data, headers=get_headers(), method="POST")
        with urllib.request.urlopen(req) as response:
            if response.status == 204:
                print(f"   -> Movido exitosamente a '{transition_name}'")
    except urllib.error.HTTPError as e:
        print(f"   -> [ERROR] No se pudo mover a {transition_name}: HTTP {e.code}")
    except Exception as e:
        pass

if __name__ == "__main__":
    print("="*50)
    print(f"Iniciando generador AVANZADO de datos en {PROJECT_KEY}...")
    print("="*50)

    for i in range(40):
        summary = f"{random.choice(TITLES)} (Simulacion #{random.randint(1000, 9999)})"
        issue_type = random.choice(["Tarea", "Tarea", "Historia", "Error"])
        
        issue_key = create_jira_issue(summary, issue_type)
        if issue_key:
            # Aumentamos la probabilidad de "In Progress" para que la métrica de tickets activos suba
            estado_destino = random.choice(["To Do", "To Do", "In Progress", "In Progress", "In Progress", "In Progress", "Done", "Done"])
            
            time.sleep(0.5)
            
            if estado_destino in ["In Progress", "Done"]:
                transition_issue(issue_key, "21", "En curso")
                time.sleep(0.5)
                
            if estado_destino == "Done":
                transition_issue(issue_key, "41", "Listo")
                
            time.sleep(0.5)
            
    print("\n==================================================")
    print("Proceso finalizado! Los tickets ahora tienen Story Points y distintos estados de progreso.")
