import asyncio
from app.core.database import SessionLocal
from app.services.jira_sync import get_jira_auth_credentials
from app.models.auth import User
from app.datasources.jira_datasource import JiraDatasource

async def test_jql():
    db = SessionLocal()
    # Get Valentina user
    user = db.query(User).filter(User.email == 'valentina1025m@gmail.com').first()
    if not user:
        print("User not found")
        return
        
    base_url, headers = get_jira_auth_credentials(db, user)
    jira_ds = JiraDatasource(base_url, headers)
    
    # Try getting issues assigned to her by email
    jql_email = 'project = "10000" AND assignee = "valentina1025m@gmail.com"'
    res_email = await jira_ds.search_issues(jql_email)
    print("Results for email:", len(res_email.get('issues', [])))

    # Try getting issues using currentUser()
    jql_current = 'project = "10000" AND assignee = currentUser()'
    res_current = await jira_ds.search_issues(jql_current)
    print("Results for currentUser:", len(res_current.get('issues', [])))

    # Try getting all issues to see who is assigned
    jql_all = 'project = "10000"'
    res_all = await jira_ds.search_issues(jql_all, max_results=5)
    for issue in res_all.get('issues', []):
        assignee = issue['fields'].get('assignee')
        if assignee:
            print("Found issue assigned to:", assignee.get('emailAddress'), assignee.get('displayName'), assignee.get('accountId'))
        else:
            print("Unassigned issue")

asyncio.run(test_jql())
