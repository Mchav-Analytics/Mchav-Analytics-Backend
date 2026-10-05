import asyncio
import httpx

async def test():
    async with httpx.AsyncClient() as client:
        res = await client.get("http://localhost:8000/api/v1/projects/10000/sprints")
        print(res.status_code)
        import json
        print(json.dumps(res.json()[:2], indent=2))

asyncio.run(test())
