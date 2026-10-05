import asyncio
import httpx

async def test():
    async with httpx.AsyncClient() as client:
        res = await client.post("http://localhost:8000/api/v1/jql/execute", json={"jql": "project = 'SCRUM' AND priority in (High, Highest) AND status != 'Done'", "max_results": 10})
        print(res.status_code)
        import json
        print(json.dumps(res.json(), indent=2))

asyncio.run(test())
