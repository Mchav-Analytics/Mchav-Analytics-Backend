from unittest.mock import MagicMock

import pytest

from app.core.exceptions import NotFoundError
from app.features.jira.models import Project
from app.services.kpi import KpiService
from app.services.project import ProjectService


class FakeSprint:
    id_sprint = 10
    name = "Sprint 1"


class FakeKpiService(KpiService):
    def __init__(self):
        pass

    def _get_sprint(self, sprint_id: int):
        if sprint_id != 10:
            raise NotFoundError("Sprint no encontrado")
        return FakeSprint()

    def get_latest_sprint_kpis(self, sprint_id: int):
        return [
            {
                "kpi_type": "velocity",
                "unit": "pts",
                "metric_value": 12.0,
                "calc_date": None,
            }
        ]


def test_project_service_get_raises_when_missing():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    service = ProjectService(db)

    with pytest.raises(NotFoundError):
        service.get_project(99)


def test_project_service_list_projects_returns_total():
    project = MagicMock(spec=Project)
    db = MagicMock()
    query = db.query.return_value
    query.order_by.return_value = query
    query.count.return_value = 2
    query.offset.return_value.limit.return_value.all.return_value = [project, project]

    service = ProjectService(db)
    rows, total = service.list_projects(page=1, page_size=10)

    assert total == 2
    assert len(rows) == 2


def test_kpi_service_build_sprint_kpis_payload():
    service = FakeKpiService()
    payload = service.build_sprint_kpis_payload(10)

    assert payload["id_sprint"] == 10
    assert payload["sprint_name"] == "Sprint 1"
    assert payload["kpis"][0]["kpi_type"] == "velocity"
