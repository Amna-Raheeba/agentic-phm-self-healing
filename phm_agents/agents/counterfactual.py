"""Counterfactual planner: 'what would have to change for the risk to drop?'

Generates concrete, costed interventions per top contributing sensor and
estimates the RUL gain with the same heuristic the diagnosis used — so the
numbers are internally consistent, if simplified. Each plan is then also
run through failure imagination (agents/failure_imagination.py) to get an
imagined failure cycle per scenario.
"""
from __future__ import annotations
from ..config import Config
from ..state import PHMState, Counterfactual
from .failure_imagination import imagine_failures

ACTIONS = {
    "vibration_mm_s": ("Inspect and replace bearing / re-balance rotor", 1200.0, 6.0),
    "temperature_c": ("Clean cooling path and replace thermal paste / coolant flush", 450.0, 3.0),
    "pressure_kpa": ("Inspect seals and pressure regulator, replace filter", 700.0, 4.0),
}

def counterfactual_node(state: PHMState, config: Config | None = None) -> PHMState:
    cfg = config or Config()
    plans: list[Counterfactual] = []
    if state.get("risk_level") in ("high", "critical"):
        for contrib in state.get("contributing_sensors", [])[:2]:
            if contrib["loss"] < 0.25: continue
            sensor = contrib["sensor"]
            action, cost, downtime = ACTIONS.get(sensor, ("Schedule targeted inspection", 300.0, 2.0))
            # Removing this sensor's loss would restore `loss * weight` of health.
            gain = round(contrib["loss"] * 55, 1)  # heuristic cycles, labelled as estimate in report
            plans.append({"action": action, "target_sensor": sensor,
                          "expected_change_pct": round(-contrib["loss"] * 60, 1),
                          "estimated_rul_gain_cycles": gain, "estimated_cost_usd": cost,
                          "downtime_h": downtime,
                          "rationale": f"{sensor} accounts for the largest health loss (loss={contrib['loss']}, z={contrib['z']})."})
        # Cheapest operational lever, always worth listing alongside a repair.
        plans.append({"action": "Reduce load by 15% until maintenance window", "target_sensor": "load_pct",
                      "expected_change_pct": -15.0, "estimated_rul_gain_cycles": 12.0,
                      "estimated_cost_usd": 0.0, "downtime_h": 0.0,
                      "rationale": "Lower load slows degradation progression with no downtime; it buys time, it does not fix the fault."})
    state["counterfactuals"] = plans
    # Failure imagination: roll the window forward under no action and under
    # each plan, so the report can compare imagined failure cycles, not just
    # point RUL gains. Stored on state; the report renders the summary.
    state["failure_imagination"] = imagine_failures(
        state["sensor_window"], plans, horizon=cfg.imagination_horizon_cycles,
        failure_health=cfg.imagination_failure_health, baseline_cycles=cfg.baseline_cycles) if plans else []
    state["approval_required"] = bool(plans) and cfg.require_approval_for_high_risk
    if state["approval_required"] and state.get("approval_status") not in ("approved", "rejected"):
        state["approval_status"] = "pending"
    elif not state["approval_required"]:
        state["approval_status"] = "not_required"
    state["step_count"] = state.get("step_count", 0) + 1
    return state

def apply_approval(state: PHMState, approved: bool, approved_by: str = "operator") -> PHMState:
    """Human-in-the-loop gate. No repair is 'scheduled' until this is approved."""
    state["approval_status"] = "approved" if approved else "rejected"
    state["approved_by"] = approved_by if approved else ""
    return state
