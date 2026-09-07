# ============================================================================
# TEST DE RENDIMIENTO Y CONCURRENCIA AUTOMATIZADO (SEMANA 4)
# ============================================================================
# Simula 50 usuarios concurrentes golpeando la API simultáneamente
# Valida la tasa de errores (0%) y el percentil P95 de latencia (< 500ms).

import pytest
import time
import concurrent.futures
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_jwt_token

client = TestClient(app)
auth_token = create_jwt_token(user_id=1, role="Administrador")

def make_single_request(endpoint: str):
    start = time.time()
    res = client.get(
        endpoint,
        headers={"Authorization": f"Bearer {auth_token}"},
        cookies={"session_id": auth_token}
    )
    elapsed_ms = (time.time() - start) * 1000
    if res.status_code != 200:
        print(f"FAILED REQ: {endpoint} -> Status {res.status_code}: {res.text[:150]}")
    return endpoint, res.status_code, elapsed_ms, res.headers.get("x-process-time")

def test_healthz_endpoint_status_and_latency():
    """Valida que /healthz responda 200 OK y contenga la cabecera X-Process-Time"""
    res = client.get("/healthz")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ["ok", "degraded"]
    assert data["database"] == "connected"
    assert "X-Process-Time" in res.headers

def test_concurrent_load_simulation():
    """Simula 50 usuarios concurrentes enviando solicitudes autenticadas simultáneas"""
    endpoints = [
        "/healthz",
        "/api/v1/projects",
        "/api/v1/projects/PROJ-01/health",
        "/api/v1/developers/matrix?proyecto_id=PROJ-01",
        "/api/v1/jira/sync/logs",
        "/api/v1/developers"
    ]
    
    num_concurrent_users = 50
    requests_to_make = [endpoints[i % len(endpoints)] for i in range(num_concurrent_users)]
    
    latencies = []
    status_codes = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(make_single_request, ep) for ep in requests_to_make]
        for future in concurrent.futures.as_completed(futures):
            ep, status, elapsed, process_time_header = future.result()
            status_codes.append(status)
            latencies.append(elapsed)

    # 1. Tasa de error debe ser 0% (todos status 200 OK)
    success_rate = (status_codes.count(200) / len(status_codes)) * 100
    assert success_rate == 100.0, f"Error rate en prueba de carga: {100 - success_rate}%"

    # 2. Percentil P95 debe ser inferior a 500ms
    latencies.sort()
    p95_index = int(len(latencies) * 0.95)
    p95_latency = latencies[p95_index]
    avg_latency = sum(latencies) / len(latencies)

    print(f"\n[METRICAS PRUEBA DE CARGA] Concurrencia: {num_concurrent_users} reqs | Promedio: {avg_latency:.2f}ms | P95: {p95_latency:.2f}ms")
    assert p95_latency < 500.0, f"P95 latency demasiado alta: {p95_latency:.2f}ms"
