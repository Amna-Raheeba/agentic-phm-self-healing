"""Diagnosis agent: RUL + risk level + which sensors are driving the risk.

The contributing-sensor list is the explainability surface: it is derived from
per-sensor loss in the RUL estimator, in the spirit of (but not identical to)
SHAP attributions used in my FYP on a trained model.
"""
from __future__ import annotations
from ..config import Config
from ..state import PHMState
from ..tools.rul_model import RULEstimator

def risk_level_for(score: float, cfg: Config) -> str:
    if score >= 0.85: return "critical"
    if score >= cfg.high_risk_threshold: return "high"
    if score >= cfg.medium_risk_threshold: return "medium"
    return "low"

def diagnosis_node(state: PHMState, config: Config | None = None) -> PHMState:
    cfg = config or Config()
    result = RULEstimator(cfg.baseline_cycles).predict(state["sensor_window"])
    state.update(health_index=result.health_index, rul_estimate_cycles=result.rul_cycles,
                 risk_score=result.risk_score, risk_level=risk_level_for(result.risk_score, cfg),
                 contributing_sensors=result.contributing)
    top = result.contributing[0]["sensor"] if result.contributing else "none"
    state["diagnosis_summary"] = (
        f"Health index {result.health_index:.2f}, estimated RUL {result.rul_cycles:.0f} cycles, "
        f"risk {state['risk_level']} ({result.risk_score:.2f}). Main contributor: {top}.")
    state["step_count"] = state.get("step_count", 0) + 1
    return state
