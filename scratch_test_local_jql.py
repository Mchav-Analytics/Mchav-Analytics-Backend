import asyncio
import httpx

async def test():
    async with httpx.AsyncClient() as client:
        # Use session_id cookie from the log
        cookies = {"session_id": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwidXNlcl9pZCI6MSwicm9sZSI6bnVsbCwiaWF0IjoxNzg2NzI4MzAwLCJleHAiOjE3ODY3NTcxMDB9.B0PHRk_0hLFYo3kWa6gnU42_Ge9-yRrQ8M-VVA7gafo"}
        headers = {"Authorization": f"Bearer {cookies['session_id']}"}
        res = await client.post(
            "http://localhost:8000/api/v1/jql/execute",
            json={"jql": "project = \"10000\" AND priority in (High, Highest) AND status != \"Done\"", "max_results": 10},
            cookies=cookies,
            headers=headers
        )
        print(f"Status: {res.status_code}")
        print(res.text)

asyncio.run(test())
