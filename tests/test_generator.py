from phm_agents.data.generator import generate_run

def test_deterministic_for_same_seed():
    assert generate_run(seed=3, cycles=20) == generate_run(seed=3, cycles=20)

def test_shape_and_cycles():
    rows = generate_run(seed=1, cycles=30)
    assert len(rows) == 30 and rows[0]["cycle"] == 1 and rows[-1]["cycle"] == 30

def test_faulty_run_degrades_more_than_healthy():
    f = generate_run(seed=5, cycles=80, faulty=True)
    h = generate_run(seed=5, cycles=80, faulty=False)
    f_late = sum(r["vibration_mm_s"] for r in f[-10:]) / 10
    h_late = sum(r["vibration_mm_s"] for r in h[-10:]) / 10
    assert f_late > h_late + 1.0
