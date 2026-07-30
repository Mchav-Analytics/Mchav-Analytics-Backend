"""Constructor de consultas JQL reutilizables."""


class JqlBuilder:
    @staticmethod
    def project_issues(project_key: str) -> str:
        return f'project = "{project_key}" ORDER BY updated DESC'

    @staticmethod
    def open_issues(project_key: str) -> str:
        return (
            f'project = "{project_key}" AND resolution = Unresolved '
            "ORDER BY priority DESC"
        )

    @staticmethod
    def resolved_in_period(project_key: str, days: int = 30) -> str:
        return (
            f'project = "{project_key}" AND resolved >= -{days}d '
            "ORDER BY resolved DESC"
        )

    @staticmethod
    def sprint_scope(project_key: str, sprint_name: str) -> str:
        return (
            f'project = "{project_key}" AND sprint = "{sprint_name}" '
            "ORDER BY status ASC"
        )
