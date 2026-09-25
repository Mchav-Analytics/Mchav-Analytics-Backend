import requests
print("--- /api/v1/projects/PROJ-01/kpis ---")
try:
    r = requests.get("http://localhost:8000/api/v1/projects/PROJ-01/kpis?limit=1", headers={"Authorization": "Bearer local_token"})
    print(r.json())
except Exception as e:
    print(e)
print("--- /api/v1/developers/valen/scorecard ---")
try:
    r = requests.get("http://localhost:8000/api/v1/developers/valen/scorecard?proyecto_id=PROJ-01", headers={"Authorization": "Bearer local_token"})
    print(r.json())
except Exception as e:
    print(e)
