import asyncio
import httpx
import base64
import json

JIRA_DOMAIN = "https://beltrancamilo592.atlassian.net"
JIRA_EMAIL = "salamancamai12@gmail.com"
JIRA_API_TOKEN = "ATATT3xFfGF0FUyvvODkNNGv_veWIQ3pGUHAikzSK6poMj1t2Y6TKi7qDR3fBb7AaSH7aK6aeYTgIQEBz-_02Wncv2sTxu2sza4tUE9BnMNrW8PRo9vh_I7EzPOqcS0-ReMN1dgp6WLMVpxlEr0mJPx_U8MU3o8pWTMFtckdevroBvs5HKRy0Zg=87A321E0"

async def test():
    token = base64.b64encode(f"{JIRA_EMAIL}:{JIRA_API_TOKEN}".encode()).decode()
    headers = {
        "Authorization": f"Basic {token}",
        "Accept": "application/json"
    }
    
    jql = "project = \"10000\" AND priority in (High, Highest) AND status != \"Done\" ORDER BY priority DESC, created DESC"
    
    payload = {
        "jql": jql,
        "maxResults": 1,
        "fields": ["summary", "priority"]
    }
    
    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"{JIRA_DOMAIN}/rest/api/3/search/jql",
            headers=headers,
            json=payload
        )
        data = res.json()
        print(json.dumps(data, indent=2))

asyncio.run(test())
