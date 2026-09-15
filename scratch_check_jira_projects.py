import asyncio
import httpx

JIRA_DOMAIN = "https://beltrancamilo592.atlassian.net"
JIRA_EMAIL = "salamancamai12@gmail.com"
JIRA_API_TOKEN = "ATATT3xFfGF0FUyvvODkNNGv_veWIQ3pGUHAikzSK6poMj1t2Y6TKi7qDR3fBb7AaSH7aK6aeYTgIQEBz-_02Wncv2sTxu2sza4tUE9BnMNrW8PRo9vh_I7EzPOqcS0-ReMN1dgp6WLMVpxlEr0mJPx_U8MU3o8pWTMFtckdevroBvs5HKRy0Zg=87A321E0"

async def check_jira_projects():
    auth = (JIRA_EMAIL, JIRA_API_TOKEN)
    url = f"{JIRA_DOMAIN}/rest/api/3/project"
    async with httpx.AsyncClient() as client:
        res = await client.get(url, auth=auth)
        if res.status_code == 200:
            projects = res.json()
            print(f"Total projects in Jira: {len(projects)}")
            for p in projects:
                print(f"- {p['name']} ({p['key']})")
        else:
            print(f"Error {res.status_code}: {res.text}")

asyncio.run(check_jira_projects())
