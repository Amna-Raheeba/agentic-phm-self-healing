"""Failure imagination: repairs must push the imagined failure later."""
from phm_agents.agents.failure_imagination import imagine_failures
from phm_agents.data.generator import generate_run
from phm_agents.graph import run_pipeline


def _failure_or_horizon(scenario):
    # Surviving the horizon counts as later than any failure inside it.
    return scenario["imagined_failure_cycle"] if scenario["imagined_failure_cycle"] is not None \
        else scenario["horizon_cycles"] + 1


def test_no_action_scenario_only_when_no_repairs():
    scenarios = imagine_failures(generate_run(seed=42, cycles=80, faulty=True), [])
    assert [s["scenario"] for s in scenarios] == ["no_action"]
    assert scenarios[0]["imagined_failure_cycle"] is not None


def test_repairs_imagine_later_failure_than_no_action():
    state = run_pipeline(generate_run(seed=42, cycles=80, faulty=True), run_id="t-fi",
                         approver=lambda s: True)
    scenarios = state["failure_imagination"]
    assert len(scenarios) == 1 + len(state["counterfactuals"])
    no_action = scenarios[0]
    assert no_action["scenario"] == "no_action" and no_action["imagined_failure_cycle"] is not None
    for scenario in scenarios[1:]:
        assert _failure_or_horizon(scenario) > no_action["imagined_failure_cycle"], scenario


def test_imagination_reaches_report():
    state = run_pipeline(generate_run(seed=42, cycles=80, faulty=True), run_id="t-fi-report",
                         approver=lambda s: True)
    assert state["report"]["failure_imagination"] == state["failure_imagination"]
    assert "Failure imagination" in state["report_markdown"]
    assert "No action" in state["report_markdown"]


def test_healthy_run_has_no_imagination():
    state = run_pipeline(generate_run(seed=42, cycles=80, faulty=False), run_id="t-fi-ok")
    assert state["failure_imagination"] == []
    assert "Failure imagination" not in state["report_markdown"]
