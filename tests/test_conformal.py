"""Split-conformal RUL intervals: sanity, coverage, and pipeline wiring."""
from phm_agents.data.generator import generate_run
from phm_agents.graph import run_pipeline
from phm_agents.tools.conformal import empirical_coverage, rul_interval


def test_interval_brackets_point_and_clips_at_zero():
    iv = rul_interval(20.0, level=0.90)
    assert iv.lower == 0.0  # 20 - half_width < 0, and RUL cannot be negative
    assert iv.upper > 20.0
    assert iv.level == 0.90 and iv.n_calibration > 0


def test_higher_level_means_wider_or_equal_interval():
    widths = [rul_interval(50.0, level=lvl).half_width for lvl in (0.80, 0.90, 0.95)]
    assert widths == sorted(widths)
    assert widths[-1] > widths[0]


def test_empirical_coverage_within_loose_band_of_nominal():
    # Split conformal guarantees marginal coverage in expectation; on a
    # fixed synthetic split we only ask for a loose band, not the nominal
    # value itself — the estimator's bias shows up as width, not misses.
    result = empirical_coverage(0.90, n_calibration=120, cal_seed=2026, n_test=80, test_seed=99)
    assert 0.78 <= result["empirical_coverage"] <= 1.0


def test_pipeline_report_carries_interval():
    state = run_pipeline(generate_run(seed=42, cycles=80, faulty=True), run_id="t-conf",
                         approver=lambda s: True)
    interval = state["report"]["rul_interval"]
    assert interval["level"] == 0.90
    assert interval["lower"] <= state["rul_estimate_cycles"] <= interval["upper"]
    assert "prediction interval" in state["diagnosis_summary"]
    # The demo run's point estimate is itself inside the alert window, so
    # this is urgent on its own — not an interval escalation.
    assert state["rul_interval_escalated"] is False


def test_report_escalates_when_interval_lower_bound_crosses_alert():
    # Mild degradation: point RUL looks comfortable, but the interval's
    # lower bound is inside the alert window — wording must escalate.
    window = generate_run(seed=1, cycles=80, faulty=True, degradation_start=30, severity=0.55)
    state = run_pipeline(window, run_id="t-esc")
    assert state["rul_estimate_cycles"] > 30
    assert state["rul_interval"]["lower"] <= 30
    assert state["rul_interval_escalated"] is True
    assert "ESCALATED" in state["report_markdown"]
