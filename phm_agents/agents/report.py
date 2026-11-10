"""Report agent: assembles the final, auditable run report."""
from __future__ import annotations
from ..state import PHMState

def report_node(state: PHMState) -> PHMState:
    plans = state.get("counterfactuals", [])
    status = state.get("approval_status", "not_required")
    if plans and status == "pending":
        disposition = "AWAITING HUMAN APPROVAL — no repair action is authorised yet."
    elif plans and status == "approved":
        disposition = f"Repair authorised by {state.get('approved_by') or 'operator'}."
    elif plans and status == "rejected":
        disposition = "Repair REJECTED by human reviewer — monitor only, re-check next window."
    else:
        disposition = "No repair required for this window — continue monitoring."
    report = {
        "run_id": state.get("run_id", "unknown"),
        "risk_level": state.get("risk_level"), "risk_score": state.get("risk_score"),
        "health_index": state.get("health_index"), "rul_estimate_cycles": state.get("rul_estimate_cycles"),
        "diagnosis_summary": state.get("diagnosis_summary"),
        "anomalies": state.get("anomalies", []), "contributing_sensors": state.get("contributing_sensors", []),
        "counterfactuals": plans, "approval_status": status, "disposition": disposition,
        "data_note": "Synthetic sensor window (C-MAPSS-style degradation shape). Not real engine data.",
    }
    lines = [f"# PHM Report — {report['run_id']}", "", report["diagnosis_summary"] or "", "",
             f"**Disposition:** {disposition}", "", "## Counterfactual repair options"]
    lines += [f"- {p['action']} (target: {p['target_sensor']}, est. RUL gain ~{p['estimated_rul_gain_cycles']} cycles, "
              f"${p['estimated_cost_usd']:.0f}, {p['downtime_h']}h downtime) — {p['rationale']}" for p in plans] or ["- None."]
    state["report"] = report
    state["report_markdown"] = "\n".join(lines)
    state["step_count"] = state.get("step_count", 0) + 1
    return state
