"""Graph state. TypedDict so the same shape works with LangGraph if installed."""
from __future__ import annotations
from typing import Any, TypedDict

class SensorReading(TypedDict):
    cycle: int
    temperature_c: float
    vibration_mm_s: float
    pressure_kpa: float
    load_pct: float

class Counterfactual(TypedDict, total=False):
    action: str
    target_sensor: str
    expected_change_pct: float
    estimated_rul_gain_cycles: float
    estimated_cost_usd: float
    downtime_h: float
    rationale: str

class PHMState(TypedDict, total=False):
    run_id: str
    sensor_window: list[SensorReading]
    sensor_stats: dict[str, dict[str, float]]
    anomalies: list[dict[str, Any]]
    health_index: float
    rul_estimate_cycles: float
    risk_score: float
    risk_level: str  # low | medium | high | critical
    contributing_sensors: list[dict[str, Any]]
    diagnosis_summary: str
    counterfactuals: list[Counterfactual]
    approval_required: bool
    approval_status: str  # not_required | pending | approved | rejected
    approved_by: str
    report: dict[str, Any]
    report_markdown: str
    trace: list[dict[str, Any]]
    errors: list[str]
    step_count: int
