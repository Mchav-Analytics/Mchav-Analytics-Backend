import pytest
from app.services.percentiles_service import calculate_percentiles

def test_calculate_percentiles_empty():
    results = calculate_percentiles([])
    assert results == []

def test_calculate_percentiles_insufficient_data():
    raw_issues = [
        ("Story", 2.0, 1.5),
        ("Story", 4.0, 3.0),
        ("Story", 6.0, 4.5)
    ]
    results = calculate_percentiles(raw_issues)
    assert len(results) == 1
    item = results[0]
    assert item["issue_type"] == "Story"
    assert item["count"] == 3
    assert item["has_enough_data"] is False
    assert item["lead_time"]["avg"] == 4.0
    assert item["cycle_time"]["avg"] == 3.0
    assert "p50" not in item["lead_time"]

def test_calculate_percentiles_sufficient_data():
    raw_issues = [
        ("Bug", 1.0 + i, 0.5 + i) for i in range(10)
    ]
    results = calculate_percentiles(raw_issues)
    assert len(results) == 1
    item = results[0]
    assert item["issue_type"] == "Bug"
    assert item["count"] == 10
    assert item["has_enough_data"] is True
    assert item["lead_time"]["avg"] == 5.5
    assert "p25" in item["lead_time"]
    assert "p50" in item["lead_time"]
    assert "p75" in item["lead_time"]
    assert "p90" in item["lead_time"]

def test_calculate_percentiles_null_handling():
    raw_issues = [
        (None, None, None)
    ]
    results = calculate_percentiles(raw_issues)
    assert len(results) == 1
    assert results[0]["issue_type"] == "Desconocido"
    assert results[0]["lead_time"]["avg"] == 0.0
