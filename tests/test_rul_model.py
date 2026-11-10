from phm_agents.data.generator import generate_run
from phm_agents.tools.rul_model import RULEstimator

def test_faulty_has_lower_rul_and_higher_risk():
    est = RULEstimator()
    faulty = est.predict(generate_run(seed=9, cycles=80, faulty=True))
    healthy = est.predict(generate_run(seed=9, cycles=80, faulty=False))
    assert faulty.risk_score > healthy.risk_score
    assert faulty.rul_cycles < healthy.rul_cycles
    assert 0.0 <= faulty.health_index <= 1.0

def test_contributors_sorted_by_loss():
    res = RULEstimator().predict(generate_run(seed=2, cycles=80, faulty=True))
    losses = [c["loss"] for c in res.contributing]
    assert losses == sorted(losses, reverse=True)
