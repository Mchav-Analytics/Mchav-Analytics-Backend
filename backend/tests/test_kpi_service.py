"""Pruebas de open_issues KPI y estados done."""

from unittest.mock import MagicMock

import pytest

from app.services.kpi_service import KpiService


class FakeIssue:
    def __init__(self, status: str, story_points: int | None = None):
        self.status = status
        self.story_points = story_points


def _service_with_issues(issues: list[FakeIssue] | None = None) -> KpiService:
    service = KpiService.__new__(KpiService)
    service.kpis = MagicMock()
    service.kpis.list_issues_by_sprint.return_value = issues or [
        FakeIssue("Done", 5),
        FakeIssue("Done", 3),
        FakeIssue("In Progress", 8),
    ]
    return service


def test_calculate_velocity_sums_done_story_points():
    assert _service_with_issues().calculate_velocity(1) == 8.0


def test_calculate_completion_rate():
    assert _service_with_issues().calculate_completion_rate(1) == pytest.approx(
        66.67, rel=0.01
    )


def test_calculate_open_issues():
    assert _service_with_issues().calculate_open_issues(1) == 1.0


def test_velocity_zero_when_no_done_issues():
    assert _service_with_issues([FakeIssue("To Do", 5)]).calculate_velocity(1) == 0.0
