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
    interval = state.get("rul_interval") or {}
    escalated = bool(state.get("rul_interval_escalated"))
    imagination = state.get("failure_imagination", [])
    report = {
        "run_id": state.get("run_id", "unknown"),
        "risk_level": state.get("risk_level"), "risk_score": state.get("risk_score"),
        "health_index": state.get("health_index"), "rul_estimate_cycles": state.get("rul_estimate_cycles"),
        "rul_interval": interval or None, "rul_interval_escalated": escalated,
        "failure_imagination": imagination,
        "diagnosis_summary": state.get("diagnosis_summary"),
        "anomalies": state.get("anomalies", []), "contributing_sensors": state.get("contributing_sensors", []),
        "counterfactuals": plans, "approval_status": status, "disposition": disposition,
        "data_note": "Synthetic sensor window (C-MAPSS-style degradation shape). Not real engine data.",
    }
    lines = [f"# PHM Report — {report['run_id']}", "", report["diagnosis_summary"] or "", ""]
    if escalated and interval:
        lines += [f"**ESCALATED — plan on the interval, not the point estimate:** the point RUL is "
                  f"{state.get('rul_estimate_cycles', 0):.0f} cycles, but the {interval['level']:.0%} prediction "
                  f"interval reaches down to {interval['lower']:.0f} cycles, inside the alert window. "
                  f"Treat this asset as urgent until a new window proves otherwise.", ""]
    lines += [f"**Disposition:** {disposition}", "", "## Counterfactual repair options"]
    lines += [f"- {p['action']} (target: {p['target_sensor']}, est. RUL gain ~{p['estimated_rul_gain_cycles']} cycles, "
              f"${p['estimated_cost_usd']:.0f}, {p['downtime_h']}h downtime) — {p['rationale']}" for p in plans] or ["- None."]
    if imagination:
        lines += ["", "## Failure imagination (simulated trajectories)"]
        for s in imagination:
            if s["imagined_failure_cycle"] is not None:
                when = f"imagined failure at cycle +{s['imagined_failure_cycle']}"
            else:
                when = f"no failure imagined within the {s.get('horizon_cycles', 120)}-cycle horizon"
            bought = f" — buys ~{s['cycles_bought']} cycles vs no action" if s.get("cycles_bought") else ""
            lines.append(f"- {s['action']}: {when}{bought}; imagined health at horizon {s.get('health_at_horizon')}")
    state["report"] = report
    state["report_markdown"] = "\n".join(lines)
    state["step_count"] = state.get("step_count", 0) + 1
    return state
