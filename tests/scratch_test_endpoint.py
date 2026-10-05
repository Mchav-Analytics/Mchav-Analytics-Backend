import httpx
import asyncio

async def test():
    async with httpx.AsyncClient() as client:
        res = await client.get("http://localhost:8000/api/v1/projects/10000/kpis/issues-detail", params={"assignee_name": "Valentina Montalvo", "limit": 50})
        print(res.status_code)
        if res.status_code == 200:
            print(res.json())
        else:
            print(res.text)

asyncio.run(test())
