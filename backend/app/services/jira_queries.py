"""Consultas JQL reutilizables para métricas y sincronización."""


def project_issues_jql(project_key: str) -> str:
    return f'project = "{project_key}" ORDER BY updated DESC'


def open_issues_jql(project_key: str) -> str:
    return f'project = "{project_key}" AND resolution = Unresolved ORDER BY priority DESC'


def resolved_in_period_jql(project_key: str, days: int = 30) -> str:
    return (
        f'project = "{project_key}" AND resolved >= -{days}d '
        "ORDER BY resolved DESC"
    )


def sprint_scope_jql(project_key: str, sprint_name: str) -> str:
    return (
        f'project = "{project_key}" AND sprint = "{sprint_name}" '
        "ORDER BY status ASC"
    )
