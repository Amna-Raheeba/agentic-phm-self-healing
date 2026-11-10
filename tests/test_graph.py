from phm_agents.data.generator import generate_run
from phm_agents.graph import run_pipeline

def test_high_risk_run_goes_through_counterfactual_and_approval():
    state = run_pipeline(generate_run(seed=42, cycles=80, faulty=True), run_id="t-high", approver=lambda s: True)
    assert state["risk_level"] in ("high", "critical")
    assert state["counterfactuals"], "high risk should produce repair options"
    assert state["approval_status"] == "approved"
    assert "Repair authorised" in state["report"]["disposition"]

def test_high_risk_without_approver_stays_pending():
    state = run_pipeline(generate_run(seed=42, cycles=80, faulty=True), run_id="t-pending")
    assert state["approval_status"] == "pending"
    assert "AWAITING HUMAN APPROVAL" in state["report"]["disposition"]

def test_healthy_run_skips_counterfactual():
    state = run_pipeline(generate_run(seed=42, cycles=80, faulty=False), run_id="t-ok")
    assert state["risk_level"] in ("low", "medium")
    assert state["counterfactuals"] == []
    assert state["approval_status"] == "not_required"
    assert state["report"]["run_id"] == "t-ok"
