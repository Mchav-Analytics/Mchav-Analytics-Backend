import os
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

# Carga las variables del archivo .env
load_dotenv()

# 1. Configuración de credenciales de Jira (leídas desde tu archivo .env)
JIRA_URL = os.getenv("JIRA_BASE_URL")
JIRA_USER = os.getenv("JIRA_EMAIL")
JIRA_TOKEN = os.getenv("JIRA_API_TOKEN")

# Autenticación básica requerida por Atlassian
auth = HTTPBasicAuth(JIRA_USER, JIRA_TOKEN)

headers = {
    "Accept": "application/json"
}

# 2. Función para obtener los detalles del proyecto
def get_jira_project(project_key: str):
    """
    Consulta los detalles de un proyecto en Jira usando su clave (e.g., 'SCRUM')
    """
    if not JIRA_URL or not JIRA_USER or not JIRA_TOKEN:
        print("Error: Faltan variables de entorno de Jira en el archivo .env")
        return None

    url = f"{JIRA_URL}/rest/api/3/project/{project_key}"
    
    try:
        response = requests.get(url, auth=auth, headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error al consultar Jira: Código {response.status_code}")
            print(response.text)
            return None
            
    except Exception as e:
        print(f"Error de conexión con la API de Jira: {e}")
        return None

# 3. Bloque de prueba local
if __name__ == "__main__":
    print("Probando conexión con Jira para el proyecto 'SCRUM'...")
    proyecto = get_jira_project("SCRUM")
    
    if proyecto:
        print("¡Conexión exitosa con Jira!")
        print(f"Nombre del Proyecto: {proyecto.get('name')}")
        print(f"ID del Proyecto: {proyecto.get('id')}")
    else:
        print("No se pudo obtener la información del proyecto.")