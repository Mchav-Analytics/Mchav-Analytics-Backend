from services.jira import JiraService

print("Iniciando prueba modular...")
service = JiraService()
resultado = service.verificar_proyecto("SCRUM")

if resultado:
    print(f"¡Éxito modular! Proyecto encontrado: {resultado.get('name')}")
else:
    print("No se pudo obtener la información con la nueva estructura.")