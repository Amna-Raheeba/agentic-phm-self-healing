"""Diagnosis agent: RUL + risk level + which sensors are driving the risk.

The contributing-sensor list is the explainability surface: it is derived from
per-sensor loss in the RUL estimator, in the spirit of (but not identical to)
SHAP attributions used in my FYP on a trained model.
"""
from __future__ import annotations
from ..config import Config
from ..state import PHMState
from ..tools.conformal import rul_interval
from ..tools.rul_model import RULEstimator

def risk_level_for(score: float, cfg: Config) -> str:
    if score >= 0.85: return "critical"
    if score >= cfg.high_risk_threshold: return "high"
    if score >= cfg.medium_risk_threshold: return "medium"
    return "low"

def diagnosis_node(state: PHMState, config: Config | None = None) -> PHMState:
    cfg = config or Config()
    result = RULEstimator(cfg.baseline_cycles).predict(state["sensor_window"])
    interval = rul_interval(result.rul_cycles, level=cfg.conformal_level,
                            n_calibration=cfg.conformal_calibration_runs,
                            seed=cfg.conformal_seed, baseline_cycles=cfg.baseline_cycles)
    state.update(health_index=result.health_index, rul_estimate_cycles=result.rul_cycles,
                 risk_score=result.risk_score, risk_level=risk_level_for(result.risk_score, cfg),
                 contributing_sensors=result.contributing,
                 rul_interval={"level": interval.level, "lower": interval.lower,
                               "upper": interval.upper, "half_width": interval.half_width,
                               "n_calibration": interval.n_calibration},
                 # Escalation: the point estimate looks safe-ish, but the
                 # interval's lower bound is already inside the alert window.
                 rul_interval_escalated=bool(result.rul_cycles > cfg.rul_alert_cycles
                                             and interval.lower <= cfg.rul_alert_cycles))
    top = result.contributing[0]["sensor"] if result.contributing else "none"
    state["diagnosis_summary"] = (
        f"Health index {result.health_index:.2f}, estimated RUL {result.rul_cycles:.0f} cycles "
        f"({interval.level:.0%} prediction interval [{interval.lower:.0f}, {interval.upper:.0f}]), "
        f"risk {state['risk_level']} ({result.risk_score:.2f}). Main contributor: {top}.")
    state["step_count"] = state.get("step_count", 0) + 1
    return state
