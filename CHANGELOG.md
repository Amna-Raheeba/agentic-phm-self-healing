# Changelog

All notable changes to this project, in my own words. Dates are when the
work was done, not when it was tidied up for the repo.

## v0.3.0 — 2026-11-10

### Added
- **Streamlit dashboard** (`dashboard/`), in the same role as the
  dashboard in my FYP repo. It runs the live pipeline — no screenshots,
  no hardcoded numbers — and shows the sensor window, health/RUL with
  the conformal interval, contributing sensors, the counterfactual
  table joined with failure-imagination outcomes, and the approval
  disposition. An "Approve repair (demo)" toggle re-runs with an
  approver so the human-in-the-loop gate is visible, not just
  described. Data shaping lives in `dashboard/helpers.py` (no
  Streamlit import) and is covered by
  `tests/test_dashboard_helpers.py`. Streamlit stays a
  dashboard-only optional extra; the core pipeline is still
  standard-library only.

## v0.2.0 — 2026-11-09

### Added
- **Split-conformal RUL intervals** (`phm_agents/tools/conformal.py`).
  Every diagnosis now reports a prediction interval next to the point
  RUL (default 90%, calibrated on 120 held-out synthetic assets). The
  report escalates when the interval's lower bound is inside the alert
  window even if the point estimate is not.
- **Failure imagination** (`phm_agents/agents/failure_imagination.py`).
  The counterfactual step now rolls the window forward under no action
  and under each repair, and the report compares imagined failure
  cycles (demo run: no action fails at +9 cycles; both repairs survive
  the 120-cycle horizon, load reduction only buys ~5).
- Experiment scripts in `notebooks/` and their outputs in `results/`,
  including the conformal coverage experiment
  (`results/conformal_coverage.csv`) and the interval plot.

### Fixed
- CI was red on GitHub Actions while tests passed locally: Actions runs
  the `pytest` binary, which does not put the repo root on `sys.path`
  the way `python -m pytest` does. Added `pythonpath` to the pytest
  config and a root `conftest.py`.

### Notes
- The conformal intervals are *wide* (90% half-width ≈ 73 cycles).
  Coverage is fine (0.94 empirical at 90% nominal) — the width is the
  heuristic estimator's optimistic bias, priced in. See
  `docs/experiment_log.md` before quoting the interval anywhere.

## v0.1.0 — 2026-11-02

### Added
- Initial agentic pipeline: monitor → diagnosis → counterfactual
  planner → human approval gate → report, as a pure-Python graph
  runner with an optional LangGraph adapter sharing the same nodes.
- Heuristic RUL estimator with per-sensor contributing-loss ranking
  (the explainability surface, in the spirit of the SHAP attributions
  from my FYP).
- Seeded synthetic sensor generator (C-MAPSS-style degradation shape —
  not NASA data) and the detection evaluation on labelled runs.
- CLI (`python -m phm_agents`) with `--healthy`, `--input`,
  `--approve` / `--auto-approve`, and 8 tests.
