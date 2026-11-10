"""Tests for dashboard/helpers.py — plain Python, no Streamlit session needed.

The helpers are imported by file path (dashboard/ is deliberately not a
package) via the repo-root conftest's sys.path setup: dashboard/ itself is
added below so `import helpers` resolves the same way it does in app.py.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "dashboard"))

import helpers  # noqa: E402
from phm_agents.data.generator import generate_run, write_csv  # noqa: E402


def test_window_from_csv_text_roundtrip(tmp_path):
    path = write_csv(generate_run(seed=3, cycles=12, faulty=False), tmp_path / "w.csv")
    rows = helpers.window_from_csv_text(path.read_text())
    assert len(rows) == 12
    assert rows[0]["cycle"] == 1
    assert set(rows[0]) == {"cycle", *helpers.SENSOR_COLUMNS}


def test_window_from_csv_text_rejects_bad_input():
    with pytest.raises(ValueError, match="must have columns"):
        helpers.window_from_csv_text("a,b,c\n1,2,3\n")
    with pytest.raises(ValueError, match="too short"):
        helpers.window_from_csv_text(
            "cycle,temperature_c,vibration_mm_s,pressure_kpa,load_pct\n1,600,3,1480,74\n")


def test_chart_data_matches_window():
    window = generate_run(seed=5, cycles=20, faulty=True)
    data = helpers.chart_data(window, ["temperature_c"])
    assert list(data) == ["temperature_c"]
    assert data["temperature_c"] == [r["temperature_c"] for r in window]
    assert len(helpers.chart_data(window)["pressure_kpa"]) == 20


def test_faulty_run_summary_and_repair_table():
    state = helpers.run_scenario("faulty", approve=False)
    summary = helpers.metric_summary(state)
    assert summary["risk_level"] in ("high", "critical")
    assert summary["approval_status"] == "pending"
    assert summary["interval_text"].startswith("[")
    rows = helpers.repair_options_table(state)
    assert rows[0]["target_sensor"] == "—"  # no-action baseline first
    assert rows[0]["imagined_failure_cycle"] == "+9 cycles"
    repairs = rows[1:]
    assert repairs, "high-risk run should list repair options"
    assert all(r["imagined_failure_cycle"] for r in repairs)
    # Approving changes the disposition, like the dashboard toggle shows.
    approved = helpers.run_scenario("faulty", approve=True)
    assert helpers.metric_summary(approved)["approval_status"] == "approved"


def test_healthy_run_has_no_repairs():
    state = helpers.run_scenario("healthy")
    assert helpers.repair_options_table(state) == []
    assert helpers.metric_summary(state)["approval_status"] == "not_required"
    assert helpers.contributors_chart(state)  # ranking exists, losses just small


def test_load_coverage_table(tmp_path):
    assert helpers.load_coverage_table(tmp_path / "missing.csv") == []
    csv_path = tmp_path / "cov.csv"
    csv_path.write_text("level,half_width,n_calibration,n_test,empirical_coverage\n"
                        "0.9,73.1,120,80,0.938\n")
    rows = helpers.load_coverage_table(csv_path)
    assert rows == [{"level": 0.9, "half_width": 73.1, "n_calibration": 120,
                     "n_test": 80, "empirical_coverage": 0.938}]
    # The real experiment output in the repo root results/ folder parses too.
    repo_csv = Path(__file__).resolve().parent.parent / "results" / "conformal_coverage.csv"
    assert len(helpers.load_coverage_table(repo_csv)) == 3
