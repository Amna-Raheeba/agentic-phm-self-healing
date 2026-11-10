"""Data helpers for the Streamlit dashboard.

Everything here is plain Python with no Streamlit import, so it can be
unit-tested without a browser session (see tests/test_dashboard_helpers.py).
The dashboard itself (app.py) is a thin shell over these functions plus the
real pipeline: every number it shows comes out of
``phm_agents.graph.run_pipeline`` — nothing is hardcoded.
"""
from __future__ import annotations

import csv
import io
from pathlib import Path

from phm_agents.config import Config
from phm_agents.data.generator import generate_run
from phm_agents.graph import run_pipeline
from phm_agents.state import PHMState, SensorReading

SENSOR_COLUMNS = ["temperature_c", "vibration_mm_s", "pressure_kpa", "load_pct"]
SCENARIOS = ("faulty", "healthy")


def window_from_csv_text(text: str) -> list[SensorReading]:
    """Parse an uploaded CSV window (same columns as the pipeline expects).

    Raises ValueError with a readable message on a bad header or bad row,
    so the dashboard can show the problem instead of crashing.
    """
    reader = csv.DictReader(io.StringIO(text))
    required = {"cycle", *SENSOR_COLUMNS}
    if reader.fieldnames is None or not required.issubset(set(reader.fieldnames)):
        raise ValueError(
            f"CSV must have columns: {', '.join(sorted(required))} "
            f"(got: {', '.join(reader.fieldnames or []) or 'none'})"
        )
    rows: list[SensorReading] = []
    for i, r in enumerate(reader, start=2):  # line 1 is the header
        try:
            rows.append({
                "cycle": int(r["cycle"]),
                "temperature_c": float(r["temperature_c"]),
                "vibration_mm_s": float(r["vibration_mm_s"]),
                "pressure_kpa": float(r["pressure_kpa"]),
                "load_pct": float(r["load_pct"]),
            })
        except (TypeError, ValueError) as exc:
            raise ValueError(f"line {i}: non-numeric value ({exc})") from exc
    if len(rows) < 5:
        raise ValueError(f"window too short: {len(rows)} rows (the monitor needs at least 5)")
    return rows


def run_scenario(scenario: str = "faulty", approve: bool = False,
                 seed: int = 42, cycles: int = 80,
                 window: list[SensorReading] | None = None,
                 run_id: str | None = None) -> PHMState:
    """Run the real pipeline for one dashboard scenario and return full state.

    ``approve=True`` supplies an approver, mirroring the CLI's --auto-approve;
    with no approver a high-risk run stays ``pending``, exactly as in the CLI.
    """
    if window is None:
        if scenario not in SCENARIOS:
            raise ValueError(f"unknown scenario {scenario!r}, expected one of {SCENARIOS}")
        window = generate_run(seed=seed, cycles=cycles, faulty=(scenario == "faulty"))
    approver = (lambda s: True) if approve else None
    return run_pipeline(window, run_id=run_id or f"dashboard-{scenario}",
                        config=Config.from_env(), approver=approver)


def chart_data(window: list[SensorReading], sensors: list[str] | None = None) -> dict[str, list[float]]:
    """Sensor series for a line chart: ``{sensor: [value per cycle]}``."""
    cols = sensors or SENSOR_COLUMNS
    return {c: [float(r[c]) for r in window] for c in cols}


def metric_summary(state: PHMState) -> dict:
    """The headline numbers for the metric cards, pulled from the report."""
    report = state.get("report", {})
    interval = report.get("rul_interval") or {}
    return {
        "health_index": report.get("health_index"),
        "rul_estimate_cycles": report.get("rul_estimate_cycles"),
        "interval_level": interval.get("level"),
        "interval_lower": interval.get("lower"),
        "interval_upper": interval.get("upper"),
        "interval_text": (
            f"[{interval['lower']:.0f}, {interval['upper']:.0f}]" if interval else "n/a"
        ),
        "risk_level": report.get("risk_level"),
        "risk_score": report.get("risk_score"),
        "approval_status": report.get("approval_status"),
        "disposition": report.get("disposition"),
        "escalated": bool(report.get("rul_interval_escalated")),
    }


def contributors_chart(state: PHMState) -> dict[str, float]:
    """Per-sensor health loss as ``{sensor: loss}`` for a bar chart."""
    return {c["sensor"]: float(c["loss"]) for c in state.get("contributing_sensors", [])}


def repair_options_table(state: PHMState) -> list[dict]:
    """Counterfactual options joined with their failure-imagination outcome.

    The no-action scenario is included as the first row: a repair option is
    only meaningful against the baseline of doing nothing.
    """
    imagination = {s["action"]: s for s in state.get("failure_imagination", [])}
    rows: list[dict] = []
    baseline = next((s for s in state.get("failure_imagination", [])
                     if s.get("scenario") == "no_action"), None)
    if baseline is not None:
        rows.append({
            "action": baseline["action"], "target_sensor": "—",
            "est_rul_gain_cycles": 0.0, "cost_usd": 0.0, "downtime_h": 0.0,
            "imagined_failure_cycle": _failure_text(baseline),
            "cycles_bought": 0, "health_at_horizon": baseline.get("health_at_horizon"),
        })
    for plan in state.get("counterfactuals", []):
        imagined = imagination.get(plan["action"], {})
        rows.append({
            "action": plan["action"], "target_sensor": plan.get("target_sensor"),
            "est_rul_gain_cycles": plan.get("estimated_rul_gain_cycles"),
            "cost_usd": plan.get("estimated_cost_usd"), "downtime_h": plan.get("downtime_h"),
            "imagined_failure_cycle": _failure_text(imagined) if imagined else "n/a",
            "cycles_bought": imagined.get("cycles_bought"),
            "health_at_horizon": imagined.get("health_at_horizon"),
        })
    return rows


def _failure_text(scenario: dict) -> str:
    cycle = scenario.get("imagined_failure_cycle")
    if cycle is None:
        return f"survives {scenario.get('horizon_cycles', 120)}-cycle horizon"
    return f"+{cycle} cycles"


def trace_rows(state: PHMState) -> list[dict]:
    """Run trace events (node timings) as plain rows for display."""
    return list(state.get("trace", []))


def load_coverage_table(path: str | Path) -> list[dict]:
    """Read results/conformal_coverage.csv if present; [] when it is not.

    Values are converted to float/int where they parse, so the dashboard can
    show a real table instead of strings.
    """
    p = Path(path)
    if not p.exists():
        return []
    with p.open(newline="") as f:
        rows = []
        for raw in csv.DictReader(f):
            row = {}
            for k, v in raw.items():
                try:
                    row[k] = int(v)
                except (TypeError, ValueError):
                    try:
                        row[k] = float(v)  # type: ignore[arg-type]
                    except (TypeError, ValueError):
                        row[k] = v
            rows.append(row)
        return rows
