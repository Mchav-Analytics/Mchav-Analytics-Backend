import sys
import os

sys.path.insert(0, os.path.abspath("."))

from app.services.gemini_service import generate_report_insights

metrics = {
    "velocity": 50,
    "throughput": 10,
    "cycleTime": 3.5,
    "blockedDays": 2,
    "bugs": 1,
    "totalScope": 60,
    "sprintHealth": 85,
    "p50": 2,
    "p85": 4,
    "p95": 5,
    "plannedIssues": 12
}

try:
    res = generate_report_insights(metrics, {}, "proyecto")
    print(res.get("markdown"))
except Exception as e:
    print("Error:", e)
