import pytest

from app.services.kpi import KpiService


class FakeIssue:
    def __init__(self, status: str, story_points: int | None = None):
        self.status = status
        self.story_points = story_points


class FakeKpiService(KpiService):
    def __init__(self):
        pass

    def _sprint_issues(self, sprint_id: int):
        return [
            FakeIssue("Done", 5),
            FakeIssue("Done", 3),
            FakeIssue("In Progress", 8),
        ]


def test_calculate_velocity_sums_done_story_points():
    service = FakeKpiService()
    assert service.calculate_velocity(1) == 8.0


def test_calculate_completion_rate():
    service = FakeKpiService()
    assert service.calculate_completion_rate(1) == pytest.approx(66.67, rel=0.01)
