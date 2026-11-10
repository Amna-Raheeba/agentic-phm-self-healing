# Dashboard

A Streamlit front-end for the agentic PHM pipeline — the same role the
dashboard plays in my FYP repo: a way to *look* at a run instead of
reading raw JSON.

It runs the actual pipeline (`phm_agents.graph.run_pipeline`) on every
scenario. Nothing on the page is a screenshot or a hardcoded result.

## What it shows

- **Scenario picker** (sidebar) — a faulty synthetic run, a healthy
  synthetic run, or your own uploaded CSV window (same columns as
  `phm_agents/data/sample_run.csv`).
- **Metric cards** — health index, RUL point estimate, the
  split-conformal prediction interval around it, and the risk level.
  If the interval's lower bound is inside the alert window, the
  escalation warning from the report shows here too.
- **Sensor window chart** and the monitor's anomaly table.
- **Contributing sensors** — the per-sensor health-loss ranking from
  the diagnosis (the explainability surface), as a bar chart + table.
- **Counterfactual repair options** joined with the failure-imagination
  outcome for each one: imagined failure cycle vs the no-action
  baseline, cycles bought, cost, downtime.
- **Approval gate** — the run's approval status and disposition, with
  an "Approve repair (demo)" toggle in the sidebar that re-runs the
  pipeline with a human approver so you can watch the disposition
  change from *AWAITING HUMAN APPROVAL* to *Repair authorised*.
- **Run trace, full Markdown report, and full JSON report** in
  expanders, plus the conformal coverage experiment table from
  `results/conformal_coverage.csv` when that file is present.

## Run it

From the repo root:

```bash
pip install streamlit
streamlit run dashboard/app.py
```

## Notes

- **Streamlit is dashboard-only.** The core pipeline has no
  third-party dependencies and does not import anything from this
  folder. It is also available as an optional extra:
  `pip install -e ".[dashboard]"`.
- `helpers.py` holds all the data shaping (CSV parsing, chart series,
  table joins) as plain Python with no Streamlit import, so it is
  covered by the normal test suite (`tests/test_dashboard_helpers.py`)
  without needing a browser.
- All data is synthetic, same as everywhere else in this repo.
