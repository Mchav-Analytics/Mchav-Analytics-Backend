import asyncio
import httpx

async def test():
    async with httpx.AsyncClient() as client:
        # test with project 10000, sprint 117 (Sprint 6)
        res = await client.get("http://localhost:8000/api/v1/projects/10000/sprints/117/health")
        print(res.status_code)
        import json
        print(json.dumps(res.json(), indent=2))

asyncio.run(test())
