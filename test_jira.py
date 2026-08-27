import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

domain = os.getenv('JIRA_DOMAIN')
email = os.getenv('JIRA_EMAIL')
token = os.getenv('JIRA_API_TOKEN')

from app.core.security import decrypt_jira_token
raw_token = decrypt_jira_token(token)

import base64
creds = base64.b64encode(f"{email}:{raw_token}".encode()).decode()
headers = {"Authorization": f"Basic {creds}", "Accept": "application/json"}

async def main():
    async with httpx.AsyncClient() as client:
        res = await client.get(f"{domain}/rest/api/3/project", headers=headers)
        projects = res.json()
        print("PROYECTOS EN JIRA:")
        for p in projects:
            print(f"- ID: {p.get('id')}, Key: {p.get('key')}, Name: {p.get('name')}")

if __name__ == "__main__":
    asyncio.run(main())
